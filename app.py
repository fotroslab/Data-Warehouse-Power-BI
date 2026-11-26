#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — اپ پیش‌نمایش پروژهٔ ۵: «SQL Server + Data Warehouse + Power BI Report Server»
=======================================================================================
اجرا:
    streamlit run app.py --server.port 8506 --server.address 0.0.0.0

صداقت: این اپ فقط *طرح و اثبات منطق* را نشان می‌دهد. Report Server نصب نشده، schema.sql روی
SQL Server واقعی اجرا نشده و SQLite (model/dw_demo.sqlite) جایگزین محلی است. اعداد، دادهٔ
نمونهٔ seed=14030505 هستند و فروش واقعی هیچ سازمانی نیستند.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "model" / "dw_demo.sqlite"
ETL_SCRIPT = BASE_DIR / "model" / "etl_staging_to_dw.py"
DIAGRAM = BASE_DIR / "assets" / "model_diagram.svg"
FONT_DIR = BASE_DIR / "assets" / "fonts"

INK = "#232b36"
ACCENT = "#d64541"
MUTED = "#5b6674"
SURFACE = "#ffffff"
PAGE_BG = "#f6f7f8"
GRID = "#e9ecef"

PAGES = [
    "نمای کلی انبار داده",
    "پایپ‌لاین زندهٔ ETL",
    "تحلیل فروش نمونه",
    "استقرار و معماری",
    "دربارهٔ داده",
]

st.set_page_config(
    page_title="انبار دادهٔ سازمانی — پروژهٔ ۵",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --------------------------------------------------------------------------- کمکی‌ها
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_digits(text) -> str:
    """تبدیل ارقام لاتین به فارسی (برای متن‌های نمایشی)."""
    return str(text).translate(FA_DIGITS)


def fa_num(n, decimals: int = 0) -> str:
    """عدد با جداکنندهٔ هزارگان فارسی."""
    try:
        v = f"{n:,.{decimals}f}"
    except (TypeError, ValueError):
        return fa_digits(n)
    return fa_digits(v).replace(",", "٬").replace(".", "٫")


def fa_humt(rial_value: float) -> str:
    """نمایش خلاصهٔ مبلغ ریالی به «همت» (هزار میلیارد ریال)."""
    return f"{fa_num(rial_value / 1e12, 2)} همت"


def axis_hamt(fig: go.Figure) -> go.Figure:
    """محور مبلغ بر حسب همت (هزار میلیارد ریال) با برچسب فارسی."""
    fig.update_xaxes(tickformat=",.1f", ticksuffix=" همت", title=None)
    return fig


def axis_billion(fig: go.Figure) -> go.Figure:
    """محور مبلغ بر حسب میلیارد ریال."""
    fig.update_xaxes(tickformat=",.0f", ticksuffix=" م.ریال", title=None)
    fig.update_yaxes(tickformat=",.0f", ticksuffix=" م.ریال", title=None)
    return fig


def _font_face_css() -> str:
    """خواندن فونت‌های Vazirmatn و تزریق به‌صورت data-URI (بدون نیاز به CDN)."""
    css_parts = []
    weights = {"Vazirmatn-Regular.woff2": 400, "Vazirmatn-Medium.woff2": 500,
               "Vazirmatn-Bold.woff2": 700}
    for fname, weight in weights.items():
        f = FONT_DIR / fname
        if not f.exists():
            continue
        b64 = base64.b64encode(f.read_bytes()).decode("ascii")
        css_parts.append(
            "@font-face{font-family:'Vazirmatn FD';font-style:normal;font-weight:%d;"
            "font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2');}" % (weight, b64)
        )
    return "\n".join(css_parts)


def inject_css() -> None:
    st.markdown(
        f"""
<style>
{_font_face_css()}

html, body, .stApp, [class*="css"] {{
    font-family: 'Vazirmatn FD', Tahoma, sans-serif !important;
    direction: rtl;
}}
.stApp {{ background: {PAGE_BG}; }}
section[data-testid="stSidebar"] {{ direction: rtl; background: #ffffff; border-left: 1px solid #e3e6ea; }}
section[data-testid="stSidebar"] * {{ font-family: 'Vazirmatn FD', Tahoma, sans-serif !important; }}
.block-container {{ padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1400px; }}

/* عنوان‌ها */
h1, h2, h3, h4 {{ color: {INK}; font-weight: 700; }}
h1 {{ font-size: 1.85rem; }}
h2 {{ font-size: 1.35rem; margin-top: 1.1rem; }}
h3 {{ font-size: 1.1rem; }}

/* کارت‌ها */
.kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:14px; margin:10px 0 6px; }}
.kpi {{
  background:{SURFACE}; border:1px solid #e3e6ea; border-radius:10px; padding:14px 16px;
  box-shadow:0 1px 2px rgba(35,43,54,.04); border-top:3px solid {INK};
}}
.kpi.accent {{ border-top-color:{ACCENT}; }}
.kpi .label {{ color:{MUTED}; font-size:.8rem; margin-bottom:6px; }}
.kpi .value {{ color:{INK}; font-size:1.5rem; font-weight:700; line-height:1.25; }}
.kpi .hint {{ color:#8a94a3; font-size:.72rem; margin-top:4px; }}

/* بنر */
.banner {{
  background:#fff8f1; border:1px solid #e8c9a0; border-right:4px solid #c08b2e;
  border-radius:8px; padding:10px 14px; color:#6b4a1e; font-size:.85rem; margin:6px 0 16px;
}}
.banner-ok {{
  background:#f2f7f2; border:1px solid #c9ddc9; border-right:4px solid #4b7a4b;
  border-radius:8px; padding:10px 14px; color:#33512f; font-size:.85rem; margin:6px 0 16px;
}}
.banner-bad {{
  background:#fdf2f2; border:1px solid #eec6c4; border-right:4px solid {ACCENT};
  border-radius:8px; padding:10px 14px; color:#7d2b28; font-size:.85rem; margin:6px 0 16px;
}}

/* گام‌های پایپ‌لاین */
.flow {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:8px 0 14px; direction:rtl; }}
.flow .step {{
  background:#fff; border:1px solid #dfe3e8; border-radius:8px; padding:9px 12px;
  font-size:.8rem; color:{INK}; min-width:120px; text-align:center;
}}
.flow .step b {{ display:block; font-size:.72rem; color:{MUTED}; font-weight:500; margin-bottom:3px; }}
.flow .arrow {{ color:#a3abb6; font-size:1.1rem; }}
.flow .step.hot {{ border-color:{ACCENT}; background:#fdf2f2; }}

/* جدول‌ها و کد */
[data-testid="stDataFrame"] {{ direction:ltr; }}
code, pre {{ direction:ltr; text-align:left; font-family: ui-monospace, monospace !important; }}
.stCode pre code {{ font-size:.78rem; }}

/* نمودارها LTR می‌مانند تا برچسب فارسی نصفه نشود */
.js-plotly-plot, .js-plotly-plot .plot-container {{ direction: ltr !important; }}

/* دکمه */
.stButton > button {{
  background:{INK}; color:#fff; border:1px solid {INK}; border-radius:8px;
  padding:.45rem 1.1rem; font-family:'Vazirmatn FD',Tahoma,sans-serif; font-weight:500;
}}
.stButton > button:hover {{ background:{ACCENT}; border-color:{ACCENT}; color:#fff; }}
[data-testid="stMetricValue"] {{ color:{INK}; font-size:1.35rem; }}

.legend-note {{ color:{MUTED}; font-size:.76rem; margin-top:-6px; }}

/* دکمهٔ جمع‌شدن سایدبار: در RTL و بدون فونت آیکون، متن ligature نمایش داده می‌شد */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] *,
[data-testid="collapsedControl"],
[data-testid="collapsedControl"] * {{ display:none !important; }}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {{ display:none !important; }}

/* لایه‌های معماری (صفحهٔ استقرار) */
.arch {{ display:flex; flex-direction:column; gap:6px; margin:6px 0 10px; }}
.arch .layer {{
  background:#fff; border:1px solid #dfe3e8; border-right:4px solid {INK}; border-radius:8px;
  padding:9px 13px; display:flex; justify-content:space-between; align-items:center; gap:12px;
}}
.arch .layer.accent {{ border-right-color:{ACCENT}; background:#fdf7f7; }}
.arch .layer .t {{ font-size:.83rem; color:{INK}; font-weight:600; }}
.arch .layer .d {{ font-size:.73rem; color:{MUTED}; text-align:left; direction:ltr; white-space:nowrap; }}
.arch .gap {{ text-align:center; color:#a3abb6; font-size:.85rem; line-height:1; }}
hr {{ border-color:#e3e6ea; }}
</style>
""",
        unsafe_allow_html=True,
    )


def style_fig(fig: go.Figure, height: int = 340, margin=None, showlegend: bool = False) -> go.Figure:
    """استایل مشترک نمودارها؛ margin همیشه از این تابع می‌آید."""
    m = margin or dict(l=78, r=26, t=44, b=58)
    fig.update_layout(
        height=height,
        margin=m,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family="Vazirmatn FD, Tahoma, sans-serif", size=12, color=INK),
        showlegend=showlegend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        hoverlabel=dict(font=dict(family="Vazirmatn FD, Tahoma", size=12)),
        title=dict(font=dict(size=13, color=INK), x=1, xanchor="right"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont=dict(size=11, color=MUTED),
                     linecolor="#dfe3e8", automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False,
                     tickfont=dict(size=11, color=MUTED), automargin=True)
    return fig


# --------------------------------------------------------------------------- داده
@st.cache_data(show_spinner=False)
def load_csv(name: str, keep_default_na: bool = True) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"{name}.csv", encoding="utf-8-sig",
                       keep_default_na=keep_default_na)


@st.cache_data(show_spinner=False)
def load_db_summary(db_path: str, mtime: float) -> dict:
    """خلاصهٔ محتوای dw_demo.sqlite (mtime برای بی‌اعتبارسازی کش بعد از ETL)."""
    import sqlite3

    con = sqlite3.connect(db_path)
    out = {}
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for t in tables:
        try:
            out[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception:
            out[t] = None
    try:
        out["_sum_net"] = con.execute("SELECT COALESCE(SUM(net_amount_irr),0) FROM fact_sales").fetchone()[0]
        out["_sum_ret"] = con.execute(
            "SELECT COALESCE(SUM(return_amount_irr),0) FROM fact_returns").fetchone()[0]
        out["_regions"] = con.execute(
            "SELECT COUNT(DISTINCT region_id) FROM fact_sales").fetchone()[0]
        out["_rejects"] = con.execute("SELECT COUNT(*) FROM etl_reject").fetchone()[0]
    except Exception:
        pass
    con.close()
    return out


def db_fingerprint() -> float:
    return DB_PATH.stat().st_mtime if DB_PATH.exists() else 0.0


def banner(text: str, kind: str = "warn") -> None:
    st.markdown(f'<div class="banner{"" if kind == "warn" else "-" + kind}">{fa_digits(text)}</div>',
                unsafe_allow_html=True)


# --------------------------------------------------------------------------- سایدبار
def sidebar() -> str:
    with st.sidebar:
        st.markdown(
            f"""
<div style="direction:rtl;text-align:right;padding:2px 0 10px">
  <div style="font-size:1.02rem;font-weight:700;color:{INK}">🗄️ انبار دادهٔ سازمانی</div>
  <div style="font-size:.74rem;color:{MUTED};margin-top:3px">
    پروژهٔ ۵ · SQL Server + DW + Power BI Report Server
  </div>
  <div style="font-size:.72rem;color:#8a94a3;margin-top:2px">۱۴۰۵/۰۹/۰۵ · نسخهٔ ۱.۰</div>
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown('<hr style="margin:4px 0 12px">', unsafe_allow_html=True)
        page = st.radio("صفحه", PAGES, index=0, label_visibility="collapsed")
        st.markdown('<hr style="margin:14px 0 12px">', unsafe_allow_html=True)
        st.markdown(
            f"""
<div class="banner" style="font-size:.75rem;margin:0">
<b>وضعیت زیرساخت:</b> SQL Server، Report Server و SSL نصب/تست نشده‌اند.<br>
ETL واقعاً اجرا شده؛ خروجی آن یک <b>SQLite جایگزین محلی</b> است.
</div>
""",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-size:.7rem;color:#8a94a3;margin-top:10px;line-height:1.7">'
            'دادهٔ نمونه: seed=۱۴۰۳۰۵۰۵<br>واحد: ریال · تقویم: شمسی<br>'
            'هیچ داده یا ادعای سازمانی واقعی وجود ندارد.</div>',
            unsafe_allow_html=True,
        )
    return page


# --------------------------------------------------------------------------- صفحه ۱
def page_overview() -> None:
    st.markdown("## نمای کلی انبار داده")
    banner("این اپ «طرح + اثبات منطق» است: هیچ نصبی روی SQL Server/Report Server انجام نشده و "
           "اعداد نمایش‌داده‌شده از دادهٔ نمونهٔ seed=۱۴۰۳۰۵۰۵ می‌آیند.")

    summary = load_db_summary(str(DB_PATH), db_fingerprint()) if DB_PATH.exists() else {}
    sales = load_csv("fact_sales")
    net = summary.get("_sum_net") or int(sales["net_amount_irr"].sum())
    ret = summary.get("_sum_ret") or 0
    n_sales = summary.get("fact_sales") or len(sales)

    st.markdown(
        f"""
<div class="kpi-grid">
  <div class="kpi"><div class="label">فروش خالص سال ۱۴۰۳ (نمونه)</div>
    <div class="value">{fa_humt(net)}</div><div class="hint">Σ net_amount_irr · ریال</div></div>
  <div class="kpi accent"><div class="label">اسناد فروش</div>
    <div class="value">{fa_num(n_sales)}</div><div class="hint">fact_sales</div></div>
  <div class="kpi"><div class="label">مرجوعی</div>
    <div class="value">{fa_num(summary.get("fact_returns", 2000))}</div>
    <div class="hint">Σ مرجوعی {fa_humt(ret)}</div></div>
  <div class="kpi"><div class="label">مناطق / مشتری / کالا</div>
    <div class="value">{fa_num(12)} / {fa_num(500)} / {fa_num(80)}</div>
    <div class="hint">ابعاد هم‌شکل (Conformed)</div></div>
  <div class="kpi accent"><div class="label">ردیف‌های Reject در نمونه</div>
    <div class="value" style="font-size:1.15rem">هیچ ردیف مردودی ندارد</div>
    <div class="hint">مسیر Reject کد و جدول دارد؛ نمونه صفر است</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### معماری در یک نگاه")
    st.markdown(
        f"""
<div class="flow">
  <div class="step"><b>منبع</b>ERP / فروش / CRM</div>
  <div class="arrow">◀</div>
  <div class="step"><b>Staging</b>stg.sales_raw</div>
  <div class="arrow">◀</div>
  <div class="step hot"><b>پاک‌سازی</b>ETL اجراشده</div>
  <div class="arrow">◀</div>
  <div class="step"><b>انبار</b>dw.dim_* / dw.fact_*</div>
  <div class="arrow">◀</div>
  <div class="step"><b>ارائه</b>Power BI Report Server</div>
</div>
<div class="legend-note">جریان از راست (منبع) به چپ (گزارش) خوانده می‌شود؛ همهٔ مؤلفه‌ها درون شبکهٔ داخلی.</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("### نمودار مدل ستاره‌ای")
    if DIAGRAM.exists():
        st.image(str(DIAGRAM), width="stretch")
    else:
        st.info("فایل assets/model_diagram.svg موجود نیست.")

    c1, c2 = st.columns([1.25, 1])
    with c1:
        st.markdown("### جدول‌های مدل")
        rows = [
            ("dim_date", "۳۶۶", "تقویم شمسی + میلادی + فصل", "بُعد"),
            ("dim_region", "۱۲", "منطقه و پهنه", "بُعد"),
            ("dim_customer", "۵۰۰", "حقیقی/حقوقی + کانال", "بُعد"),
            ("dim_product", "۸۰", "کالا + دسته + قیمت", "بُعد"),
            ("fact_sales", "۳۰٬۰۰۰", "یک سطر = یک قلم فروش", "فکت"),
            ("fact_returns", "۲٬۰۰۰", "ارجاع به sale_id", "فکت"),
            ("etl_reject", "۰ (در نمونه)", "پایش کیفیت ورودی", "کنترل"),
            ("etl_load_log", "به‌ازای هر بار", "ثبت هر بار ETL", "کنترل"),
        ]
        st.dataframe(
            pd.DataFrame(rows, columns=["جدول", "ردیف نمونه", "نقش", "نوع"]),
            hide_index=True, width="stretch", height=326,
        )
        st.markdown(
            '<div class="legend-note">هر بعد به فکت با رابطهٔ یک‌به‌چند وصل است؛ '
            'کلید تاریخ = YYYYMMDD شمسی.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("### سه ادعا که این پروژه <span style='color:#d64541'>نمی‌کند</span>",
                unsafe_allow_html=True)
    a1, a2, a3 = st.columns(3)
    for col, icon, title, body in [
        (a1, "⛔", "«Report Server نصب شد»", "نصب، لایسنس و انتشار سازمانی انجام نشده؛ مرحلهٔ ۳ چک‌لیست است."),
        (a2, "⛔", "«این اعداد فروش واقعی است»", "داده نمونه و قابل بازتولید با seed است؛ کنترل توازن انجام شده ولی منبع سازمانی نیست."),
        (a3, "⛔", "«RLS تست شد»", "RLS منطقه‌ای فقط مستند است؛ نه Security Policy ساخته شده نه View-as تست شده."),
    ]:
        with col:
            st.markdown(
                f"""<div class="kpi" style="border-top-color:{ACCENT};min-height:132px">
                <div class="label" style="color:{ACCENT};font-weight:700">{icon} {title}</div>
                <div style="font-size:.8rem;color:{MUTED};line-height:1.8;margin-top:6px">{body}</div>
                </div>""",
                unsafe_allow_html=True,
            )


# --------------------------------------------------------------------------- صفحه ۲
def page_etl() -> None:
    st.markdown("## پایپ‌لاین زندهٔ ETL")
    banner("دکمهٔ زیر اسکریپت واقعی model/etl_staging_to_dw.py را با subprocess اجرا می‌کند و خروجی آن را "
           "همان‌طور که هست نشان می‌دهد. خروجی به SQLite محلی نوشته می‌شود — نه به SQL Server.")

    stg = load_csv("stg_sales_raw", keep_default_na=False)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("ردیف ورودی خام", fa_num(len(stg)))
    c2.metric("فرمت تاریخ مخلوط", "۴ نوع")
    c3.metric("کامای هزارگان", fa_num(int(stg["unit_price_raw"].astype(str).str.contains(",").sum())))
    c4.metric("تخفیف خالی", fa_num(int((stg["discount_raw"].astype(str).str.strip() == "").sum())))

    st.markdown("### نمونهٔ ردیف‌های «عمداً کثیف» ورودی")
    show = stg.head(8)[["row_id", "sale_date_raw", "customer_name_raw", "region_id_raw",
                        "quantity_raw", "unit_price_raw", "discount_raw"]].copy()
    show.columns = ["ردیف", "تاریخ خام", "نام مشتری (خام)", "منطقه", "تعداد", "مبلغ واحد", "تخفیف"]
    st.dataframe(show, hide_index=True, width="stretch", height=310)

    st.markdown("### اجرای واقعی ETL")
    b1, b2, b3 = st.columns([1.1, 1.1, 2.4])
    run = b1.button("▶ اجرای ETL روی staging", width="stretch")
    if b2.button("↺ بازخوانی وضعیت پایگاه‌داده", width="stretch"):
        st.cache_data.clear()
        st.rerun()
    b3.markdown('<div class="legend-note" style="padding-top:10px">معادل SQL Server: SSIS یا '
                'Stored Procedure؛ منطق پاک‌سازی یکسان است. اجرا حدوداً ۱ ثانیه طول می‌کشد.</div>',
                unsafe_allow_html=True)
    if True:
        if run:
            with st.spinner("در حال اجرا…"):
                try:
                    cp = subprocess.run(
                        [sys.executable, str(ETL_SCRIPT)],
                        cwd=str(BASE_DIR), capture_output=True, text=True, timeout=240,
                    )
                    out = (cp.stdout or "") + (("\n[stderr]\n" + cp.stderr) if cp.stderr.strip() else "")
                    st.session_state["etl_out"] = out
                    st.session_state["etl_rc"] = cp.returncode
                    st.cache_data.clear()
                except subprocess.TimeoutExpired:
                    st.session_state["etl_out"] = "⏱ اجرا بیش از ۲۴۰ ثانیه طول کشید و متوقف شد."
                    st.session_state["etl_rc"] = -1
        out = st.session_state.get("etl_out")
        rc = st.session_state.get("etl_rc")
        if out:
            kind = "ok" if rc == 0 else "bad"
            label = "اجرا موفق (کد خروج ۰)" if rc == 0 else f"اجرا با خطا (کد خروج {fa_digits(rc)})"
            st.markdown(f'<div class="banner-{kind}">✅ {label} — این خروجی متنیِ همان اجراست.</div>',
                        unsafe_allow_html=True)
            st.code(out, language="text")
        else:
            st.markdown(
                '<div class="banner">هنوز در این نشست اجرا نشده است. دکمهٔ «اجرای ETL» را بزنید؛ '
                'اجرای اصلی در ساخت پروژه انجام و لاگ آن در VALIDATION.md ثبت شده است.</div>',
                unsafe_allow_html=True)

    st.markdown("### محتوای dw_demo.sqlite (جایگزین محلی)")
    if DB_PATH.exists():
        summary = load_db_summary(str(DB_PATH), db_fingerprint())
        order = ["dim_date", "dim_region", "dim_customer", "dim_product",
                 "fact_sales", "fact_returns", "etl_reject", "etl_load_log", "stg_sales_cleaned"]
        rows = [(t, summary.get(t)) for t in order if t in summary]
        rows += [(t, v) for t, v in summary.items()
                 if not t.startswith("_") and t not in order]
        df = pd.DataFrame([{"جدول": t, "تعداد ردیف": fa_num(v) if v is not None else "—"}
                           for t, v in rows])
        c1, c2 = st.columns([1.45, 1])
        with c1:
            st.dataframe(df, hide_index=True, width="stretch", height=456)
        with c2:
            st.markdown(
                f"""
<div class="kpi-grid" style="grid-template-columns:1fr">
  <div class="kpi"><div class="label">Σ net_amount_irr</div>
    <div class="value">{fa_humt(summary.get("_sum_net", 0))}</div>
    <div class="hint">{fa_num(summary.get("_sum_net", 0))} ریال</div></div>
  <div class="kpi accent"><div class="label">مناطق متمایز در فکت</div>
    <div class="value">{fa_num(summary.get("_regions", 0))}</div><div class="hint">از ۱۲ منطقه</div></div>
  <div class="kpi"><div class="label">ردیف‌های Reject پس از این اجرا</div>
    <div class="value" style="font-size:1.1rem">بدون ردیف مردودی</div>
    <div class="hint">etl_reject خالی است</div></div>
</div>
""", unsafe_allow_html=True)
        st.markdown(
            f'<div class="legend-note">فایل: model/dw_demo.sqlite · '
            f'آخرین بازنویسی: {fa_digits(pd.Timestamp(DB_PATH.stat().st_mtime, unit="s", tz="UTC")
                                        .tz_convert("Asia/Tehran").strftime("%Y/%m/%d %H:%M"))}</div>',
            unsafe_allow_html=True)
    else:
        st.markdown('<div class="banner-bad">dw_demo.sqlite موجود نیست؛ ابتدا ETL را اجرا کنید.</div>',
                    unsafe_allow_html=True)

    st.markdown("### نمایش جریان Reject")
    st.markdown(
        """
<div class="banner">در نمونهٔ فعلی <b>۰ ردیف Reject</b> است، چون هر چهار فرمت تاریخ قابل تبدیل‌اند.
برای دیدن جریان Reject، ردیف‌هایی مثل تاریخ <code>1403/13/45</code>، مبلغ <code>abc</code> یا
منطقهٔ <code>R99</code> را به <code>data/stg_sales_raw.csv</code> تزریق کنید؛ کد مسیر
<code>dw.etl_reject</code> آماده است و تست جداگانه دارد.</div>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- صفحه ۳
def page_sales() -> None:
    st.markdown("## تحلیل فروش نمونه")
    banner("همهٔ نمودارها از دادهٔ نمونهٔ seed=۱۴۰۳۰۵۰۵ ساخته شده‌اند (نه فروش واقعی). "
           "تقویم شمسی، واحد ریال.")

    sales = load_csv("fact_sales")
    returns = load_csv("fact_returns")
    dim_date = load_csv("dim_date")
    dim_region = load_csv("dim_region")
    dim_product = load_csv("dim_product")

    regions = dim_region.set_index("region_id")["region_name_fa"].to_dict()
    picked = st.multiselect(
        "فیلتر منطقه", options=list(regions.keys()),
        format_func=lambda r: f"{regions[r]}",
        default=[],
        placeholder="همهٔ مناطق",
    )
    if picked:
        sales_f = sales[sales["region_id"].isin(picked)]
        returns_f = returns[returns["region_id"].isin(picked)]
    else:
        sales_f, returns_f = sales, returns

    net = int(sales_f["net_amount_irr"].sum())
    ret_amt = int(returns_f["return_amount_irr"].sum())
    qty = int(sales_f["quantity"].sum())
    margin = (net - int(sales_f["cost_amount_irr"].sum())) / net if net else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("فروش خالص", fa_humt(net))
    c2.metric("تعداد", fa_num(qty))
    c3.metric("حاشیهٔ سود", fa_digits(f"{margin * 100:.1f}") + "٪")
    c4.metric("نرخ مرجوعی", fa_digits(f"{ret_amt / net * 100:.2f}") + "٪" if net else "—")

    merged = sales_f.merge(dim_date[["date_key", "month", "month_name_fa"]], on="date_key")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### روند فروش ماهانه (شمسی)")
        m = (merged.groupby(["month", "month_name_fa"], as_index=False)["net_amount_irr"].sum()
             .sort_values("month"))
        fig = go.Figure(go.Scatter(
            x=m["month_name_fa"], y=m["net_amount_irr"] / 1e12, mode="lines+markers",
            line=dict(color=INK, width=2.4, shape="spline"),
            marker=dict(size=7, color=INK),
            customdata=m["net_amount_irr"],
            hovertemplate="%{x}<br>%{customdata:,.0f} ریال<extra></extra>",
            fill="tozeroy", fillcolor="rgba(35,43,54,0.06)", name="فروش",
        ))
        fig.update_yaxes(tickformat=",.1f", ticksuffix=" همت", rangemode="tozero")
        style_fig(fig, height=350, margin=dict(l=74, r=26, t=44, b=74))
        fig.update_xaxes(tickangle=-32, tickfont=dict(size=10.5, color=MUTED))
        st.plotly_chart(fig, width="stretch",
                        config={"displayModeBar": False, "locale": "fa"})

    with c2:
        st.markdown("### فروش به تفکیک منطقه")
        r = (sales_f.groupby("region_id", as_index=False)["net_amount_irr"].sum()
             .merge(dim_region[["region_id", "region_name_fa"]], on="region_id")
             .sort_values("net_amount_irr", ascending=True))
        fig = go.Figure(go.Bar(
            x=r["net_amount_irr"] / 1e12, y=r["region_name_fa"], orientation="h",
            marker=dict(color=[ACCENT if i >= len(r) - 3 else INK for i in range(len(r))],
                        line=dict(width=0)),
            text=[f"{v / 1e12:,.2f} همت" for v in r["net_amount_irr"]],
            textposition="outside", cliponaxis=False,
            customdata=r["net_amount_irr"],
            hovertemplate="%{y}<br>%{customdata:,.0f} ریال<extra></extra>",
        ))
        axis_hamt(fig)
        fig.update_yaxes(tickfont=dict(size=11, color=INK))
        style_fig(fig, height=350, margin=dict(l=84, r=88, t=44, b=52))
        st.plotly_chart(fig, width="stretch",
                        config={"displayModeBar": False, "locale": "fa"})

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("### ترکیب دستهٔ کالا")
        cat = (sales_f.merge(dim_product[["product_id", "category_name_fa"]], on="product_id")
               .groupby("category_name_fa", as_index=False)["net_amount_irr"].sum()
               .sort_values("net_amount_irr", ascending=False))
        fig = go.Figure(go.Bar(
            x=cat["category_name_fa"], y=cat["net_amount_irr"] / 1e12,
            marker=dict(color=[INK, "#3d4b5c", "#5b6b7d", "#8a94a3", "#b9c0c9", ACCENT][:len(cat)]),
            text=[f"{v / 1e12:,.1f} همت" for v in cat["net_amount_irr"]],
            textposition="outside", cliponaxis=False,
            customdata=cat["net_amount_irr"],
            hovertemplate="%{x}<br>%{customdata:,.0f} ریال<extra></extra>",
        ))
        fig.update_yaxes(tickformat=",.1f", ticksuffix=" همت")
        style_fig(fig, height=330, margin=dict(l=74, r=26, t=44, b=78))
        st.plotly_chart(fig, width="stretch",
                        config={"displayModeBar": False, "locale": "fa"})

    with c2:
        st.markdown("### نرخ مرجوعی به تفکیک علت")
        rr = (returns_f.groupby("reason_fa", as_index=False)["return_amount_irr"].sum()
              .sort_values("return_amount_irr", ascending=True))
        fig = go.Figure(go.Bar(
            x=rr["return_amount_irr"] / 1e9, y=rr["reason_fa"], orientation="h",
            marker=dict(color=ACCENT, opacity=.85, line=dict(width=0)),
            text=[f"{v / 1e9:,.0f} م.ریال" for v in rr["return_amount_irr"]],
            textposition="outside", cliponaxis=False,
            customdata=rr["return_amount_irr"],
            hovertemplate="%{y}<br>%{customdata:,.0f} ریال<extra></extra>",
        ))
        axis_billion(fig)
        style_fig(fig, height=330, margin=dict(l=110, r=82, t=44, b=52))
        st.plotly_chart(fig, width="stretch",
                        config={"displayModeBar": False, "locale": "fa"})

    st.markdown("### ۱۰ کالای پرفروش")
    top = (sales_f.groupby("product_id", as_index=False)
           .agg(فروش_ریال=("net_amount_irr", "sum"), تعداد=("quantity", "sum"),
                اسناد=("sale_id", "count"))
           .merge(dim_product[["product_id", "product_name_fa", "category_name_fa"]], on="product_id")
           .sort_values("فروش_ریال", ascending=False).head(10))
    top_out = pd.DataFrame({
        "کالا": top["product_name_fa"],
        "دسته": top["category_name_fa"],
        "تعداد": top["تعداد"].map(fa_num),
        "اسناد": top["اسناد"].map(fa_num),
        "فروش خالص (ریال)": top["فروش_ریال"].map(lambda v: fa_num(v)),
    })
    st.dataframe(top_out, hide_index=True, width="stretch", height=418)
    st.markdown('<div class="legend-note">جدول‌ها از fact_sales + dim_product ساخته شده‌اند؛ '
                'مرتب‌سازی بر پایهٔ فروش خالص.</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- صفحه ۴
def page_deploy() -> None:
    st.markdown("## استقرار و معماری")
    banner("این صفحه <b>راهنمای استقرار</b> است، نه گزارش انجام آن. هیچ‌یک از مراحل نصب در این "
           "پروژه اجرا نشده است.")

    c1, c2 = st.columns([1.25, 1])
    with c1:
        st.markdown("### معماری هدف — بدون ابر")
        layers = [
            ("منبع", "ERP / CRM / سیستم مرجوعی", "extraction: file or CDC", False),
            ("Staging", "stg.sales_raw — دادهٔ خام با load_batch_id", "no transformation", False),
            ("پاک‌سازی", "SSIS یا Python — همین منطق ETL", "normalize · reject · log", True),
            ("انبار داده", "dw.dim_* و dw.fact_* — استاراسکیما", "FK · index · CHECK", False),
            ("معنایی", "مدل Power BI (Import mode) و سنجه‌های DAX", "refresh scheduled", False),
            ("ارائه", "Power BI Report Server داخلی + HTTPS", "portal · AD auth", True),
        ]
        rows = []
        for k, (title, desc, en, hot) in enumerate(layers):
            if k:
                rows.append('<div class="gap">▼</div>')
            rows.append(
                f'<div class="layer{" accent" if hot else ""}">'
                f'<span class="t">{title} — {desc}</span>'
                f'<span class="d">{en}</span></div>')
        st.markdown('<div class="arch">' + "".join(rows) + "</div>", unsafe_allow_html=True)
        st.markdown('<div class="legend-note">همهٔ لایه‌ها درون شبکهٔ داخلی؛ هیچ مؤلفهٔ ابری لازم نیست. '
                    'از بالا به پایین: منبع ← گزارش.</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("### وضعیت واقعی اجزا")
        status = pd.DataFrame([
            ("DDL T-SQL (schema.sql)", "نوشته و بازبینی منطقی", "⚠️ روی سرور اجرا نشده"),
            ("ETL (Python)", "اجرا شد ✅", "✅ ۳۰۰/۳۰۰ تمیز"),
            ("انبار داده", "SQLite جایگزین محلی", "⚠️ نه SQL Server"),
            ("RSLS منطقه‌ای", "طراحی داکیومنت", "⚠️ پیاده/تست نشده"),
            ("Report Server", "فقط راهنما", "⛔ نصب/لایسنس نشده"),
            ("گزارش (.pbix)", "ساخت‌نشده", "⛔ وجود ندارد"),
            ("SSL / DNS داخلی", "فقط چک‌لیست", "⛔ تست نشده"),
            ("UAT / تست بار", "—", "⛔ انجام نشده"),
        ], columns=["مؤلفه", "وضعیت در پروژه", "پذیرش"])
        st.dataframe(status, hide_index=True, width="stretch", height=330)

    st.markdown("### مراحل استقرار (خلاصهٔ چک‌لیست)")
    steps = pd.DataFrame([
        ("۰", "تأیید شرح خدمات، لایسنس SQL Server و Report Server، گروه‌های AD", "کارفرما + IT"),
        ("۱", "ساخت VM، نصب SQL Server با کالیشن فارسی، بکاپ و بازگردانی", "DBA"),
        ("۲", "DBA Review روی schema.sql → اجرا در Test → ETL → کنترل کیفیت", "DBA + تیم داده"),
        ("۳", "نصب Report Server، ReportServer DB، HTTPS، DNS، .pbix، Publish", "زیرساخت + BI"),
        ("۴", "RLS + View-as، توازن با مبدأ، تست بار، UAT، آموزش، Run Book", "BI + مالی + کارفرما"),
    ], columns=["مرحله", "کارهای کلیدی", "مسئول"])
    st.dataframe(steps, hide_index=True, width="stretch", height=250)
    st.markdown('<div class="legend-note">جزئیات کامل با پیش‌نیاز و ریسک: '
                'report/DEPLOYMENT_CHECKLIST.md</div>', unsafe_allow_html=True)

    st.markdown("### تصمیم‌های فنی و هزینه‌شان")
    dec = pd.DataFrame([
        ("تقویم شمسی به‌عنوان کلید تاریخ", "الزام گزارش فارسی", "نیاز به ستون میلادی موازی — فراهم شد"),
        ("Import mode در Power BI", "کارایی و استقرار سادهٔ داخلی", "نیاز به Refresh زمان‌بندی‌شده"),
        ("Reject در DW نه در فایل", "قابل گزارش و پیگیری", "نگهداشت و آرشیو دوره‌ای لازم"),
        ("SQLite برای اثبات منطق", "اجرای واقعی و تکرارپذیر بدون زیرساخت", "بدون Columnstore/پارتیشن/آمار"),
        ("RLS فقط مستند", "نبود محیط AD و Report Server", "قبل از انتشار الزاماً پیاده و تست شود"),
    ], columns=["تصمیم", "دلیل", "هزینه/ریسک"])
    st.dataframe(dec, hide_index=True, width="stretch", height=230)

    st.markdown("### فایل‌های کلیدی")
    files = pd.DataFrame([
        ("model/schema.sql", "DDL کامل T-SQL (idempotent، CHECK، FK، ایندکس)"),
        ("model/etl_staging_to_dw.py", "ETL اجراشده: پاک‌سازی تاریخ/مبلغ/تخفیف + Reject"),
        ("model/dw_demo.sqlite", "خروجی ETL — جایگزین محلی SQL Server"),
        ("model/measures.dax", "سنجه‌های DAX (فروش، حاشیه، مرجوعی، YTD/MTD شمسی)"),
        ("report/POWER_BI_BUILD_GUIDE.md", "ساخت گزارش، RLS، View-as، Publish"),
        ("report/theme.json", "تم «Enterprise DW Fa» — #232b36 و #d64541 روی #f6f7f8"),
    ], columns=["فایل", "کاربرد"])
    st.dataframe(files, hide_index=True, width="stretch", height=240)


# --------------------------------------------------------------------------- صفحه ۵
def page_data() -> None:
    st.markdown("## دربارهٔ داده")
    banner("کل داده نمونه است: <b>seed=۱۴۰۳۰۵۰۵</b>، تولید‌شده با scripts/generate_all_data.py. "
           "هیچ دیتاست عمومی یا سازمانی استفاده نشده. واحد ریال، تقویم شمسی ۱۴۰۳.")

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("### مشخصات تولید داده")
        meta = pd.DataFrame([
            ("seed", "۱۴۰۳۰۵۰۵"),
            ("اسکریپت", "scripts/generate_all_data.py"),
            ("سال داده", "۱۴۰۳ شمسی (+ معادل میلادی)"),
            ("واحد پول", "ریال"),
            ("فروش خالص نمونه", fa_humt(int(load_csv("fact_sales")["net_amount_irr"].sum()))),
            ("مرجوعی", fa_num(len(load_csv("fact_returns"))) + " سند"),
            ("staging", fa_num(len(load_csv("stg_sales_raw", keep_default_na=False))) + " ردیف عمداً کثیف"),
            ("کتابخانه‌ها", "pandas · jdatetime · streamlit · plotly"),
        ], columns=["مورد", "مقدار"])
        st.dataframe(meta, hide_index=True, width="stretch", height=306)

    with c2:
        st.markdown("### کنترل‌های کیفیت اجراشده")
        q = pd.DataFrame([
            ("یکتایی sale_id", "۰ تکراری", "✅"),
            ("FK فکت → ۴ بعد", "۰ نقض", "✅"),
            ("FK مرجوعی → fact_sales", "۰ نقض", "✅"),
            ("بازمحاسبهٔ net = qty×price×(1−disc)", "۰ مغایرت", "✅"),
            ("هم‌خوانی منطقهٔ فکت/مشتری", "۰ ناهم‌خوانی", "✅"),
            ("تبدیل هر ۴ فرمت تاریخ staging", "۳۰۰/۳۰۰", "✅"),
            ("حذف کامای هزارگان", "۱۰۰٪ ردیف‌ها", "✅"),
            ("تخفیف خالی → ۰", "۱۰۰٪ ردیف‌ها", "✅"),
        ], columns=["کنترل", "نتیجه", "وضعیت"])
        st.dataframe(q, hide_index=True, width="stretch", height=306)

    st.markdown("### محدودیت‌ها (صادقانه)")
    lim = pd.DataFrame([
        ("زیرساخت واقعی", "SQL Server، Report Server، SSL، شبکه — هیچ‌کدام نصب/تست نشده"),
        ("schema.sql", "روی SQL Server اجرا نشده؛ نیازمند DBA Review (کالیشن، فایل‌گروپ، بکاپ)"),
        ("SQLite", "جایگزین محلی؛ Columnstore/پارتیشن/آمار فقط در سرور واقعی معنا دارد"),
        ("Reject", "در نمونه ۰ ردیف است؛ جریان واقعی خطا نمایش داده نشده"),
        ("RLS", "فقط مستند؛ بدون Security Policy و بدون View-as"),
        ("YTD/سال مالی", "وابسته به dim_date این پروژه و فرض مرز نوروز"),
        ("گزارش", "فایل .pbix ساخته نشده؛ Report Server منتشر نشده"),
        ("شرح خدمات", "پیوست کارفرما موجود نبود؛ Scope طراحی مستقل است"),
        ("ROI", "هیچ ادعای صرفه‌جویی/بهره‌وری نمی‌شود"),
        ("لایسنس", "لایسنس Power BI Report Server الزامی است و تأمین نشده"),
    ], columns=["موضوع", "توضیح"])
    st.dataframe(lim, hide_index=True, width="stretch", height=400)

    st.markdown("### منابع داده")
    st.markdown(
        """
<div class="banner-ok">
<b>منبع:</b> هیچ منبع بیرونی. کل داده با شبیه‌سازی کنترل‌شده (random با seed ثابت) در همین مخزن
تولید شده و با اجرای مجدد اسکریپت عیناً بازتولید می‌شود. اعداد برای «مقیاس واقع‌نمای سازمانی»
کالیبره شده‌اند (ضریب PRICE_SCALE) و <b>برآورد بازار یا فروش واقعی نیستند</b>.
</div>
""", unsafe_allow_html=True)
    st.markdown('<div class="legend-note">جزئیات: data/DATA_DICTIONARY.md · '
                'data/DATA_QUALITY_REPORT.md · LIMITATIONS.md · SOURCES.md</div>',
                unsafe_allow_html=True)


# --------------------------------------------------------------------------- اجرا
def main() -> None:
    inject_css()
    page = sidebar()
    try:
        if page == PAGES[0]:
            page_overview()
        elif page == PAGES[1]:
            page_etl()
        elif page == PAGES[2]:
            page_sales()
        elif page == PAGES[3]:
            page_deploy()
        else:
            page_data()
    except Exception as exc:  # نمایش خطای خوانا به‌جای صفحهٔ سفید
        st.markdown(f'<div class="banner-bad">خطا در نمایش این صفحه: {fa_digits(exc)}</div>',
                    unsafe_allow_html=True)
        with st.expander("جزئیات فنی"):
            st.exception(exc)

    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="text-align:center;color:#8a94a3;font-size:.72rem;line-height:1.9">'
        f'پروژهٔ ۵ — راهکار سازمانی SQL Server + DW + Power BI Report Server · '
        f'۱۴۰۵/۰۹/۰۵<br>دادهٔ نمونه (seed=۱۴۰۳۰۵۰۵) · SQLite جایگزین محلی · '
        f'بدون ادعای نصب یا انتشار سازمانی</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()

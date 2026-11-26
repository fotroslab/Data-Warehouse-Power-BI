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

طراحی: یک سیستم طراحی مینیمال و «طبیعی» — پالت خنثی، یک رنگ لهجه، مقیاس تایپوگرافی آرام،
حاشیه‌های زیاد و کادرهای کم. قواعد در همین فایل (بخش CSS) تعریف شده‌اند.
"""
from __future__ import annotations

import base64
import json
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

# ------------------------------------------------------------------ پالت طراحی
# خنثی‌های گرم‌مایل + یک لهجهٔ آجری. بدون مشکی مطلق و بدون قرمز فریادزن.
INK        = "#1f2630"   # متن اصلی
INK_SOFT   = "#3d4854"   # متن ثانویه
MUTED      = "#6f7a88"   # متن کم‌رنگ
FAINT      = "#98a2ae"   # راهنما
LINE       = "#e6e9ed"   # خط‌های جداکننده
HAIRLINE   = "#eef0f3"
SURFACE    = "#ffffff"
PAGE       = "#f7f8f9"
TINT       = "#f3f5f7"   # پس‌زمینهٔ ملایم بلوک‌ها
ACCENT     = "#9c4a3c"   # آجری (لهجه)
ACCENT_2   = "#3c6e80"   # فیروزه‌ای مات (دوم)
WARN_BG    = "#fbf6ee"
WARN_LINE  = "#e8d9bf"
WARN_INK   = "#7a6033"

PAGES = ["نمای کلی", "پایپ‌لاین ETL", "تحلیل فروش", "استقرار", "دربارهٔ داده"]

st.set_page_config(
    page_title="انبار دادهٔ فروش — پروژهٔ ۵",
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------ کمکی‌ها
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_digits(text) -> str:
    return str(text).translate(FA_DIGITS)


def fa_num(n, decimals: int = 0) -> str:
    try:
        v = f"{n:,.{decimals}f}"
    except (TypeError, ValueError):
        return fa_digits(n)
    return fa_digits(v).replace(",", "٬").replace(".", "٫")


def compact(n: float) -> str:
    """نمایش خلاصهٔ مبلغ: همت / میلیارد ریال."""
    n = float(n or 0)
    if abs(n) >= 1e12:
        return f"{fa_num(n / 1e12, 2)} همت"
    if abs(n) >= 1e9:
        return f"{fa_num(n / 1e9, 0)} میلیارد"
    return fa_num(n)


def _font_face_css() -> str:
    weights = {"Vazirmatn-Regular.woff2": 400, "Vazirmatn-Medium.woff2": 500,
               "Vazirmatn-Bold.woff2": 700}
    parts = []
    for fname, weight in weights.items():
        f = FONT_DIR / fname
        if not f.exists():
            continue
        b64 = base64.b64encode(f.read_bytes()).decode("ascii")
        parts.append(
            "@font-face{font-family:'Vazirmatn FD';font-style:normal;font-weight:%d;"
            "font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2');}"
            % (weight, b64))
    return "\n".join(parts)


def inject_css() -> None:
    st.markdown(
        f"""
<style>
{_font_face_css()}

/* ============================ پایهٔ تایپوگرافی ============================ */
html, body, .stApp, [class*="css"] {{
    font-family: 'Vazirmatn FD', Tahoma, sans-serif !important;
    direction: rtl;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}}
.stApp {{ background:{PAGE}; }}

/* راست‌چینی صریح: direction تنها کافی نیست، Streamlit خودش left می‌گذارد */
.stApp, .stApp p, .stApp span, .stApp div, .stApp li, .stApp label,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdown"],
[data-testid="stHeading"], [data-testid="stCaptionContainer"],
[data-testid="stMetricLabel"], [data-testid="stExpander"], [data-testid="stAlert"],
[data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"] {{
    direction: rtl !important; text-align: right;
}}
.stApp code, .stApp pre, .stApp pre *, .stApp kbd {{
    direction: ltr !important; text-align: left !important; unicode-bidi: embed;
}}

/* مقیاس آرام: اندازه‌ها کوچک‌تر و وزن‌ها سبک‌تر از پیش‌فرض */
[data-testid="stMarkdownContainer"] {{ font-size:.875rem; line-height:1.95; color:{INK_SOFT}; }}
[data-testid="stMarkdownContainer"] p {{ margin:0 0 .55rem; }}
h1, h2, h3, h4 {{ color:{INK}; font-weight:600 !important; letter-spacing:-.2px; }}
h1 {{ font-size:1.45rem !important; margin:.1rem 0 .2rem !important; }}
h2 {{ font-size:1.06rem !important; margin:1.5rem 0 .5rem !important; }}
h3 {{ font-size:.95rem !important; margin:1rem 0 .35rem !important; }}
h2::after {{
  content:""; display:block; width:28px; height:2px; background:{ACCENT};
  margin:.42rem 0 0; border-radius:2px; opacity:.75;
}}

.block-container {{ padding:2.1rem 2.4rem 3.5rem; max-width:1260px; }}
hr {{ border:none; border-top:1px solid {HAIRLINE}; margin:1.4rem 0; }}

/* ============================ سایدبار ============================ */
section[data-testid="stSidebar"] {{
  background:{SURFACE}; border-left:1px solid {LINE}; direction:rtl;
}}
section[data-testid="stSidebar"] * {{ font-family:'Vazirmatn FD',Tahoma,sans-serif !important; }}
section[data-testid="stSidebar"] .block-container {{ padding:.9rem 1rem 1.2rem; }}
[data-testid="stSidebarNav"] {{ display:none; }}
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapseButton"] *,
[data-testid="collapsedControl"], [data-testid="collapsedControl"] *,
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {{
  display:none !important;
}}

/* ناوبری سایدبار: رادیو به شکل فهرست آرام */
section[data-testid="stSidebar"] [role="radiogroup"] {{ gap:2px !important; }}
section[data-testid="stSidebar"] [role="radiogroup"] label {{
  padding:6px 10px !important; border-radius:6px; cursor:pointer; min-height:0 !important;
  margin:0 !important; font-size:.82rem !important; color:{INK_SOFT} !important;
  transition:background .15s;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label > div,
section[data-testid="stSidebar"] [role="radiogroup"] label > div > div {{
  min-height:0 !important; gap:0 !important; align-items:center !important; padding:0 !important;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] p {{
  margin:0 !important; font-size:.82rem !important; line-height:1.7 !important;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background:{TINT}; }}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
  background:#eef1f4; color:{INK} !important; font-weight:500;
  box-shadow:inset -2px 0 0 {ACCENT};
}}
section[data-testid="stSidebar"] [role="radiogroup"] label > div > div:first-child {{ display:none; }}

.brand {{ padding:0 2px 13px; border-bottom:1px solid {HAIRLINE}; margin-bottom:10px; }}
.brand .mark {{
  width:30px; height:30px; border-radius:8px; background:{INK}; color:#fff;
  display:flex; align-items:center; justify-content:center; font-size:.9rem; margin-bottom:9px;
}}
.brand .name {{ font-size:.9rem; font-weight:600; color:{INK}; }}
.brand .sub {{ font-size:.72rem; color:{MUTED}; margin-top:2px; line-height:1.7; }}

.side-note {{ margin-top:16px; padding-top:12px; border-top:1px solid {HAIRLINE};
  font-size:.71rem; color:{MUTED}; line-height:2; }}
.side-note b {{ color:{INK_SOFT}; font-weight:600; }}
.side-dot {{ display:inline-block; width:5px; height:5px; border-radius:50%;
  background:{WARN_INK}; margin-inline-end:5px; vertical-align:middle; }}

/* ============================ سربرگ صفحه ============================ */
.page-head {{ margin:0 0 1.5rem; }}
.page-head .eyebrow {{ font-size:.71rem; color:{FAINT}; letter-spacing:.2px; margin-bottom:5px;
  direction:rtl; text-align:right; }}
.page-head h1 {{ font-size:1.38rem !important; margin:0 0 5px !important; }}
.page-head .lede {{ font-size:.82rem; color:{MUTED}; line-height:1.85; max-width:74ch;
  direction:rtl; text-align:right; }}

/* ============================ KPI ============================ */
.kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr));
  align-items:start; gap:1px; background:{LINE}; border:1px solid {LINE}; border-radius:9px;
  overflow:hidden; margin:2px 0 6px; }}
.kpi {{ background:{SURFACE}; padding:11px 15px 12px; }}
.kpi .label {{ font-size:.7rem; color:{MUTED}; margin-bottom:6px; line-height:1.5; }}
.kpi .value {{ font-size:1.15rem; font-weight:600; color:{INK}; line-height:1.35;
  letter-spacing:-.2px; }}
.kpi .hint {{ font-size:.66rem; color:{FAINT}; margin-top:5px; line-height:1.6; }}
.kpi.warn .value {{ color:{WARN_INK}; font-size:.92rem; font-weight:500; }}

/* ============================ بلوک‌های محتوا ============================ */
.note {{
  border-right:2px solid {WARN_LINE}; background:{WARN_BG}; color:{WARN_INK};
  border-radius:0 6px 6px 0; padding:8px 12px; font-size:.76rem; line-height:1.85;
  margin:0 0 1.2rem;
}}
.quiet {{ font-size:.73rem; color:{FAINT}; line-height:1.9; margin:.35rem 0 0; }}

/* جدول راست‌چین */
.tbl-wrap {{ width:100%; overflow-x:auto; border:1px solid {LINE}; border-radius:8px;
  background:{SURFACE}; margin:2px 0 4px; }}
.tbl-scroll {{ max-height:var(--h,440px); overflow-y:auto; }}
table.rt {{ width:100%; min-width:100%; border-collapse:collapse; direction:rtl; }}
table.rt thead th {{
  background:{SURFACE}; color:{MUTED}; font-weight:500; font-size:.7rem; line-height:1.6;
  padding:8px 12px; text-align:right; white-space:nowrap;
  border-bottom:1px solid {LINE}; position:sticky; top:0; z-index:2;
}}
table.rt tbody td {{ padding:7px 12px; font-size:.78rem; color:{INK_SOFT}; line-height:1.65;
  text-align:right; border-bottom:1px solid {HAIRLINE}; vertical-align:middle; }}
table.rt tbody tr:last-child td {{ border-bottom:none; }}
table.rt tbody tr:hover td {{ background:#fbfbfc; }}
table.rt td.num {{ font-variant-numeric:tabular-nums; white-space:nowrap; color:{INK}; }}
table.rt td.mono {{ direction:ltr; text-align:left; font-family:ui-monospace,monospace;
  font-size:.73rem; color:{MUTED}; }}

/* نمودار */
.js-plotly-plot, .js-plotly-plot .plot-container {{ direction:ltr !important; }}

/* دکمه‌ها و کنترل‌ها */
.stButton > button, .stDownloadButton > button {{
  background:{SURFACE}; color:{INK}; border:1px solid #d9dee4; border-radius:6px;
  padding:.42rem 1rem; font-family:'Vazirmatn FD',Tahoma,sans-serif !important;
  font-size:.8rem; font-weight:500; transition:all .15s; box-shadow:none;
}}
.stButton > button:hover {{ background:{TINT}; border-color:#c9d0d8; color:{INK}; }}
.stButton > button:focus:not(:active) {{ border-color:{ACCENT}; color:{ACCENT}; }}
[data-baseweb="select"] > div {{ border-radius:6px; border-color:#dfe4ea; font-size:.8rem; }}
[data-baseweb="select"] div {{ direction:rtl !important; }}
[data-baseweb="tag"] {{ background:{TINT} !important; color:{INK_SOFT} !important;
  font-size:.73rem !important; border-radius:4px !important; }}
[data-testid="stMetricLabel"] div {{ font-size:.72rem !important; color:{MUTED} !important; }}
[data-testid="stMetricValue"] {{ font-size:1.05rem !important; color:{INK} !important; font-weight:600; }}
[data-testid="stExpander"] {{ border:1px solid {LINE} !important; border-radius:8px !important; }}
[data-testid="stExpander"] summary {{ font-size:.8rem !important; }}
.stAlert {{ border-radius:8px; font-size:.8rem; }}
</style>
""",
        unsafe_allow_html=True,
    )


def style_fig(fig: go.Figure, height: int = 300, margin=None, showlegend: bool = False) -> go.Figure:
    """استایل یکنواخت نمودارها؛ margin همیشه از این تابع می‌آید."""
    m = margin or dict(l=72, r=22, t=30, b=52)
    fig.update_layout(
        height=height, margin=m,
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
        font=dict(family="Vazirmatn FD, Tahoma, sans-serif", size=11, color=INK_SOFT),
        showlegend=showlegend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        hoverlabel=dict(font=dict(family="Vazirmatn FD, Tahoma", size=11),
                        bgcolor="#ffffff", bordercolor=LINE),
        title=None,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=LINE,
                     tickfont=dict(size=10, color=MUTED), automargin=True, ticks="")
    fig.update_yaxes(showgrid=True, gridcolor=HAIRLINE, zeroline=False,
                     tickfont=dict(size=10, color=MUTED), automargin=True, ticks="")
    return fig


def hbar_rtl(fig: go.Figure, labels_side_right: bool = True) -> go.Figure:
    """
    قرارداد راست‌به‌چپ برای میلهٔ افقی: محور مقادیر معکوس (میله از راست رشد می‌کند)
    و برچسب دسته‌ها در سمت راست. این‌طور برچسب فارسی نه بریده می‌شود و نه
    برای کاربر فارسی‌زبان غیرطبیعی است.
    """
    # میله از راست رشد می‌کند (قرارداد فارسی) و برچسب دسته‌ها در حاشیهٔ آزاد چپ می‌نشیند
    fig.update_xaxes(autorange="reversed")
    fig.update_yaxes(side="left", ticklabelposition="outside left",
                     tickfont=dict(size=10, color=INK_SOFT), ticks="")
    return fig


def axis_hamt(fig: go.Figure) -> go.Figure:
    fig.update_xaxes(tickformat=",.1f", ticksuffix=" همت")
    return fig


def axis_billion(fig: go.Figure) -> go.Figure:
    fig.update_xaxes(tickformat=",.0f", ticksuffix=" م‌ریال")
    fig.update_yaxes(tickformat=",.0f", ticksuffix=" م‌ریال")
    return fig


# ------------------------------------------------------------------ اجزای UI
def page_head(title: str, lede: str, eyebrow: str = "") -> None:
    eyebrow_html = f'<div class="eyebrow">{fa_digits(eyebrow)}</div>' if eyebrow else ""
    st.markdown(
        f'<div class="page-head">{eyebrow_html}<h1>{title}</h1>'
        f'<div class="lede">{lede}</div></div>',
        unsafe_allow_html=True,
    )


def kpis(items: list[tuple]) -> None:
    """items: [(label, value, hint, kind)] — kind: '' | 'warn'"""
    cells = []
    for label, value, hint, kind in items:
        hint_html = f'<div class="hint">{hint}</div>' if hint else ""
        cells.append(
            f'<div class="kpi {kind}"><div class="label">{label}</div>'
            f'<div class="value">{value}</div>{hint_html}</div>')
    st.markdown('<div class="kpis">' + "".join(cells) + "</div>", unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def quiet(text: str) -> None:
    st.markdown(f'<div class="quiet">{text}</div>', unsafe_allow_html=True)


def _cell_class(col: str, val) -> str:
    name = str(col)
    if any(k in name for k in ("فایل", "ستون", "مؤلفه", "جدول")) or str(val).startswith(("dw.", "stg.", "model/")):
        return "mono"
    try:
        float(str(val).replace("٬", "").replace(",", "").replace("٪", ""))
        return "num"
    except (TypeError, ValueError):
        return ""


def rtl_table(df: pd.DataFrame, max_height: int | None = 440,
              numeric_cols: list[str] | None = None,
              note_text: str | None = None) -> None:
    """جدول راست‌چین با HTML (st.dataframe همیشه LTR است)."""
    import html as _html

    numeric_cols = numeric_cols or []
    heads = "".join(f"<th>{_html.escape(str(c))}</th>" for c in df.columns)
    rows = []
    for _, row in df.iterrows():
        tds = []
        for col in df.columns:
            val = row[col]
            cls = "num" if str(col) in numeric_cols else _cell_class(col, val)
            tds.append(f'<td class="{cls}">{_html.escape(str(val))}</td>')
        rows.append("<tr>" + "".join(tds) + "</tr>")
    style = f' style="--h:{max_height}px"' if max_height else ""
    cls = "tbl-scroll" if max_height else ""
    st.markdown(
        f'<div class="tbl-wrap"{style}><div class="{cls}"{style}>'
        f'<table class="rt"><thead><tr>{heads}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div></div>',
        unsafe_allow_html=True)
    if note_text:
        quiet(_html.escape(note_text))


# ------------------------------------------------------------------ داده
@st.cache_data(show_spinner=False)
def load_csv(name: str, keep_default_na: bool = True) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"{name}.csv", encoding="utf-8-sig",
                       keep_default_na=keep_default_na)


@st.cache_data(show_spinner=False)
def load_db_summary(db_path: str, mtime: float) -> dict:
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
        out["_sum_net"] = con.execute(
            "SELECT COALESCE(SUM(net_amount_irr),0) FROM fact_sales").fetchone()[0]
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


# ------------------------------------------------------------------ سایدبار
def sidebar() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="brand">'
            '<div class="mark">▦</div>'
            '<div class="name">انبار دادهٔ فروش</div>'
            '<div class="sub">SQL Server · DW · Report Server<br>پروژهٔ ۵ — ۱۴۰۵/۰۹/۰۵</div>'
            '</div>',
            unsafe_allow_html=True)
        page = st.radio("صفحه", PAGES, index=0, label_visibility="collapsed")
        st.markdown(
            '<div class="side-note">'
            '<span class="side-dot"></span><b>زیرساخت:</b> نصب‌نشده<br>'
            'ETL: اجراشده · خروجی SQLite محلی<br>'
            'داده: نمونه (seed ۱۴۰۳۰۵۰۵)<br>'
            'واحد: ریال · تقویم: شمسی'
            '</div>',
            unsafe_allow_html=True)
    return page


# ------------------------------------------------------------------ ۱) نمای کلی
def page_overview() -> None:
    page_head(
        "نمای کلی",
        "طرح انبار دادهٔ استاراسکیما برای شبکهٔ داخلی سازمان، با اثبات اجراییِمسیر پاک‌سازی داده.",
        "پروژهٔ ۵ · راهکار سازمانی",
    )

    summary = load_db_summary(str(DB_PATH), db_fingerprint()) if DB_PATH.exists() else {}
    sales = load_csv("fact_sales")
    net = summary.get("_sum_net") or int(sales["net_amount_irr"].sum())
    ret = summary.get("_sum_ret") or 0
    n_sales = summary.get("fact_sales") or len(sales)

    kpis([
        ("فروش خالص ۱۴۰۳", compact(net), f"{fa_num(n_sales)} سند · نمونه", ""),
        ("مرجوعی", compact(ret), f"{fa_num(summary.get('fact_returns', 0))} سند", ""),
        ("ابعاد", f"{fa_num(12)} / {fa_num(500)} / {fa_num(80)}",
         "منطقه / مشتری / کالا", ""),
        ("ردیف Reject", "بدون ردیف", "مسیر آماده است", "warn"),
    ])

    st.markdown("## جریان داده")
    steps = [("منابع", "ERP · CRM · مرجوعی"), ("Staging", "stg.sales_raw"),
             ("پاک‌سازی", "ETL اجراشده"), ("انبار", "dw.dim_* · dw.fact_*"),
             ("ارائه", "Report Server")]
    chips = '<div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin:0 0 2px">'
    for i, (t, d) in enumerate(steps):
        if i:
            chips += f'<span style="color:#c3cad2;font-size:.8rem">‹</span>'
        bg = TINT if i != 2 else "#f7efed"
        col = INK_SOFT if i != 2 else ACCENT
        chips += (f'<span style="background:{bg};color:{col};border:1px solid {LINE};'
                  f'border-radius:18px;padding:5px 13px;font-size:.74rem;line-height:1.6">'
                  f'{t}<span style="color:{FAINT};margin-inline-start:6px">{d}</span></span>')
    chips += "</div>"
    st.markdown(chips, unsafe_allow_html=True)
    quiet("همهٔ لایه‌ها درون شبکهٔ داخلی؛ هیچ مؤلفهٔ ابری لازم نیست.")

    st.markdown("## مدل داده")
    if DIAGRAM.exists():
        st.image(str(DIAGRAM), width="stretch")

    st.markdown("## جدول‌ها")
    rows = [
        ("dim_date", "۳۶۶", "تقویم شمسی + میلادی", "بُعد"),
        ("dim_region", "۱۲", "منطقه و پهنه", "بُعد"),
        ("dim_customer", "۵۰۰", "حقیقی/حقوقی + کانال", "بُعد"),
        ("dim_product", "۸۰", "کالا، دسته، قیمت", "بُعد"),
        ("fact_sales", "۳۰٬۰۰۰", "یک سطر = یک قلم فروش", "فکت"),
        ("fact_returns", "۲٬۰۰۰", "ارجاع به sale_id", "فکت"),
        ("etl_reject", "۰", "پایش کیفیت ورودی", "کنترل"),
        ("etl_load_log", "هر بار", "ثبت هر اجرای ETL", "کنترل"),
    ]
    rtl_table(pd.DataFrame(rows, columns=["جدول", "ردیف", "محتوا", "نوع"]),
              max_height=330, numeric_cols=["ردیف"])

    st.markdown("## آنچه ادعا نمی‌شود")
    note("Report Server نصب و لایسنس نشده است · این اعداد فروش واقعی نیستند · "
         "RLS منطقه‌ای فقط مستند است و تست نشده.")


# ------------------------------------------------------------------ ۲) ETL
def page_etl() -> None:
    page_head("پایپ‌لاین ETL",
              "دکمهٔ زیر اسکریپت واقعی را اجرا می‌کند و خروجی آن را همان‌طور که هست نشان می‌دهد؛ "
              "نتیجه در SQLite محلی ذخیره می‌شود.",
              "اثبات اجرایی")

    stg = load_csv("stg_sales_raw", keep_default_na=False)
    kpis([
        ("ردیف ورودی", fa_num(len(stg)), "stg_sales_raw.csv", ""),
        ("فرمت تاریخ", "۴ نوع", "شمسی و میلادی", ""),
        ("کاما هزارگان", fa_num(int(stg["unit_price_raw"].astype(str).str.contains(",").sum())),
         "ردیف", ""),
        ("تخفیف خالی", fa_num(int((stg["discount_raw"].astype(str).str.strip() == "").sum())),
         "ردیف", ""),
    ])

    st.markdown("## ورودی خام")
    show = stg.head(6)[["row_id", "sale_date_raw", "customer_name_raw", "region_id_raw",
                        "quantity_raw", "unit_price_raw", "discount_raw"]].copy()
    show.columns = ["#", "تاریخ", "مشتری", "منطقه", "تعداد", "مبلغ واحد", "تخفیف"]
    rtl_table(show, max_height=None, numeric_cols=["#", "تعداد", "مبلغ واحد", "تخفیف"])

    st.markdown("## اجرا")
    c1, c2, _ = st.columns([1, 1, 2.2])
    run = c1.button("اجرای ETL", width="stretch")
    if c2.button("بازخوانی", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    if run:
        with st.spinner("در حال اجرا…"):
            try:
                cp = subprocess.run([sys.executable, str(ETL_SCRIPT)], cwd=str(BASE_DIR),
                                    capture_output=True, text=True, timeout=240)
                out = (cp.stdout or "")
                if cp.stderr.strip():
                    out += "\n[stderr]\n" + cp.stderr
                st.session_state["etl_out"] = out
                st.session_state["etl_rc"] = cp.returncode
                st.cache_data.clear()
            except subprocess.TimeoutExpired:
                st.session_state["etl_out"] = "اجرا بیش از ۲۴۰ ثانیه طول کشید و متوقف شد."
                st.session_state["etl_rc"] = -1

    out = st.session_state.get("etl_out")
    rc = st.session_state.get("etl_rc")
    if out:
        if rc == 0:
            note("اجرا با موفقیت تمام شد — این خروجی متنیِ همان اجراست.")
        else:
            note(f"اجرا با خطا تمام شد (کد {fa_digits(rc)}).")
        st.code(out, language="text")
    else:
        quiet("هنوز در این نشست اجرا نشده است. لاگ اجرای ساخت پروژه در VALIDATION.md ثبت شده.")

    st.markdown("## محتوای پایگاه‌داده")
    if DB_PATH.exists():
        summary = load_db_summary(str(DB_PATH), db_fingerprint())
        order = ["dim_date", "dim_region", "dim_customer", "dim_product", "fact_sales",
                 "fact_returns", "etl_reject", "etl_load_log", "stg_sales_cleaned"]
        rows = [(t, summary.get(t)) for t in order if t in summary]
        df = pd.DataFrame([{"جدول": t, "ردیف": fa_num(v) if v is not None else "—"}
                           for t, v in rows])
        c1, c2 = st.columns([1.35, 1])
        with c1:
            rtl_table(df, max_height=340, numeric_cols=["ردیف"])
        with c2:
            kpis([
                ("جمع فروش", compact(summary.get("_sum_net", 0)), "ریال", ""),
                ("مناطق", fa_num(summary.get("_regions", 0)), "از ۱۲", ""),
                ("Reject", "بدون ردیف", "etl_reject خالی", "warn"),
            ])
            stamp = pd.Timestamp(DB_PATH.stat().st_mtime, unit="s", tz="UTC")
            stamp_fa = fa_digits(stamp.tz_convert("Asia/Tehran").strftime("%Y/%m/%d %H:%M"))
            quiet(f"آخرین نوشتن فایل: {stamp_fa}")
    else:
        note("dw_demo.sqlite موجود نیست؛ ابتدا ETL را اجرا کنید.")

    st.markdown("## مسیر Reject")
    quiet("در این نمونه صفر ردیف مردود است، چون هر چهار فرمت تاریخ قابل تبدیل‌اند. "
          "برای دیدن مسیر، ردیفی با تاریخ ۱۴۰۳/۱۳/۴۵ یا مبلغ abc یا منطقهٔ R99 به فایل "
          "staging اضافه کنید.")


# ------------------------------------------------------------------ ۳) تحلیل فروش
def page_sales() -> None:
    page_head("تحلیل فروش",
              "نمودارها از دادهٔ نمونه ساخته شده‌اند؛ واحد ریال و تقویم شمسی است.",
              "دادهٔ نمونه")

    sales = load_csv("fact_sales")
    returns = load_csv("fact_returns")
    dim_date = load_csv("dim_date")
    dim_region = load_csv("dim_region")
    dim_product = load_csv("dim_product")

    regions = dim_region.set_index("region_id")["region_name_fa"].to_dict()
    filter_col, _ = st.columns([1, 2.4])
    with filter_col:
        picked = st.multiselect("منطقه", options=list(regions.keys()),
                                format_func=lambda r: regions[r], default=[],
                                placeholder="همهٔ مناطق")
    if picked:
        sales_f = sales[sales["region_id"].isin(picked)]
        returns_f = returns[returns["region_id"].isin(picked)]
    else:
        sales_f, returns_f = sales, returns

    net = int(sales_f["net_amount_irr"].sum())
    ret_amt = int(returns_f["return_amount_irr"].sum())
    margin = (net - int(sales_f["cost_amount_irr"].sum())) / net if net else 0

    kpis([
        ("فروش خالص", compact(net), "ریال", ""),
        ("تعداد", fa_num(int(sales_f["quantity"].sum())), "قلم", ""),
        ("حاشیهٔ سود", fa_digits(f"{margin * 100:.1f}") + "٪", "", ""),
        ("نرخ مرجوعی", fa_digits(f"{ret_amt / net * 100:.2f}") + "٪" if net else "—", "", ""),
    ])

    merged = sales_f.merge(dim_date[["date_key", "month", "month_name_fa"]], on="date_key")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("## روند ماهانه")
        m = (merged.groupby(["month", "month_name_fa"], as_index=False)["net_amount_irr"]
             .sum().sort_values("month"))
        fig = go.Figure(go.Scatter(
            x=m["month_name_fa"], y=m["net_amount_irr"] / 1e12, mode="lines",
            line=dict(color=ACCENT, width=2, shape="spline"),
            customdata=m["net_amount_irr"],
            hovertemplate="%{x}<br>%{customdata:,.0f} ریال<extra></extra>",
            fill="tozeroy", fillcolor="rgba(156,74,60,0.06)"))
        peak = float(m["net_amount_irr"].max()) / 1e12
        fig.update_yaxes(tickformat=",.1f", ticksuffix=" همت",
                         range=[0, peak * 1.14])
        style_fig(fig, height=290, margin=dict(l=64, r=18, t=18, b=52))
        fig.update_xaxes(tickmode="array", tickvals=list(m["month_name_fa"][::2]),
                         tickangle=0, tickfont=dict(size=9.5))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "locale": "fa"})

    with c2:
        st.markdown("## فروش منطقه‌ای")
        r = (sales_f.groupby("region_id", as_index=False)["net_amount_irr"].sum()
             .merge(dim_region[["region_id", "region_name_fa"]], on="region_id")
             .sort_values("net_amount_irr"))
        fig = go.Figure(go.Bar(
            x=r["net_amount_irr"] / 1e12, y=r["region_name_fa"], orientation="h",
            marker=dict(color=ACCENT_2, opacity=.82, line=dict(width=0)),
            text=[f"{v / 1e12:,.2f}" for v in r["net_amount_irr"]],
            textposition="inside", insidetextanchor="end",
            textfont=dict(size=9.5, color="#ffffff"),
            cliponaxis=False, customdata=r["net_amount_irr"],
            hovertemplate="%{y}<br>%{customdata:,.0f} ریال<extra></extra>"))
        axis_hamt(fig)
        style_fig(fig, height=290, margin=dict(l=88, r=16, t=18, b=42))
        hbar_rtl(fig)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "locale": "fa"})

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("## دستهٔ کالا")
        cat = (sales_f.merge(dim_product[["product_id", "category_name_fa"]], on="product_id")
               .groupby("category_name_fa", as_index=False)["net_amount_irr"].sum()
               .sort_values("net_amount_irr", ascending=False))
        fig = go.Figure(go.Bar(
            x=cat["category_name_fa"], y=cat["net_amount_irr"] / 1e12,
            marker=dict(color=[INK_SOFT] * len(cat), opacity=.78, line=dict(width=0)),
            text=[f"{v / 1e12:,.1f}" for v in cat["net_amount_irr"]],
            textposition="outside", textfont=dict(size=9.5, color=MUTED),
            cliponaxis=False, customdata=cat["net_amount_irr"],
            hovertemplate="%{x}<br>%{customdata:,.0f} ریال<extra></extra>"))
        fig.update_yaxes(tickformat=",.1f", ticksuffix=" همت")
        top_cat = float(cat["net_amount_irr"].max()) / 1e12
        fig.update_yaxes(range=[0, top_cat * 1.18])
        style_fig(fig, height=280, margin=dict(l=62, r=16, t=22, b=70))
        fig.update_xaxes(tickfont=dict(size=9.5))
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "locale": "fa"})

    with c2:
        st.markdown("## علت مرجوعی")
        rr = (returns_f.groupby("reason_fa", as_index=False)["return_amount_irr"].sum()
              .sort_values("return_amount_irr"))
        fig = go.Figure(go.Bar(
            x=rr["return_amount_irr"] / 1e9, y=rr["reason_fa"], orientation="h",
            marker=dict(color=ACCENT, opacity=.62, line=dict(width=0)),
            text=[f"{v / 1e9:,.0f}" for v in rr["return_amount_irr"]],
            textposition="inside", insidetextanchor="end",
            textfont=dict(size=9.5, color="#ffffff"),
            cliponaxis=False, customdata=rr["return_amount_irr"],
            hovertemplate="%{y}<br>%{customdata:,.0f} ریال<extra></extra>"))
        axis_billion(fig)
        style_fig(fig, height=280, margin=dict(l=118, r=16, t=18, b=42))
        hbar_rtl(fig)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "locale": "fa"})

    st.markdown("## ۱۰ کالای پرفروش")
    top = (sales_f.groupby("product_id", as_index=False)
           .agg(فروش=("net_amount_irr", "sum"), تعداد=("quantity", "sum"),
                اسناد=("sale_id", "count"))
           .merge(dim_product[["product_id", "product_name_fa", "category_name_fa"]], on="product_id")
           .sort_values("فروش", ascending=False).head(10))
    out = pd.DataFrame({
        "کالا": top["product_name_fa"],
        "دسته": top["category_name_fa"],
        "تعداد": top["تعداد"].map(fa_num),
        "اسناد": top["اسناد"].map(fa_num),
        "فروش (ریال)": top["فروش"].map(fa_num),
    })
    rtl_table(out, max_height=400, numeric_cols=["تعداد", "اسناد", "فروش (ریال)"])


# ------------------------------------------------------------------ ۴) استقرار
def page_deploy() -> None:
    page_head("استقرار",
              "راهنمای اجرا در محیط سازمان. هیچ‌یک از این مراحل در این پروژه انجام نشده است.",
              "طرح و چک‌لیست")

    st.markdown("## وضعیت اجزا")
    status = pd.DataFrame([
        ("DDL (schema.sql)", "نوشته و بازبینی منطقی", "روی سرور اجرا نشده"),
        ("ETL (Python)", "اجرا شد", "۳۰۰ / ۳۰۰ تمیز"),
        ("انبار داده", "SQLite محلی", "نه SQL Server"),
        ("RLS منطقه‌ای", "طراحی مستند", "پیاده/تست نشده"),
        ("Report Server", "راهنما", "نصب/لایسنس نشده"),
        ("گزارش .pbix", "—", "وجود ندارد"),
        ("SSL / DNS داخلی", "چک‌لیست", "تست نشده"),
    ], columns=["مؤلفه", "وضعیت در پروژه", "پذیرش"])
    rtl_table(status, max_height=None)

    st.markdown("## معماری هدف")
    layers = [
        ("منابع", "ERP، CRM و سیستم مرجوعی", "extract / CDC"),
        ("Staging", "جدول ورودی خام با شناسهٔ بستهٔ بار", "no transform"),
        ("پاک‌سازی", "SSIS یا Python با همین منطق", "reject · log"),
        ("انبار داده", "ابعاد و فکت‌های استاراسکیما", "FK · index · check"),
        ("ارائه", "Power BI Report Server داخلی", "HTTPS · AD auth"),
    ]
    rows = []
    for t, d, m in layers:
        rows.append(
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;'
            f'gap:16px;padding:9px 14px;background:{SURFACE};border:1px solid {LINE};'
            f'border-radius:7px;margin-bottom:5px">'
            f'<div style="min-width:0">'
            f'<div style="font-size:.8rem;color:{INK}">{t}</div>'
            f'<div style="font-size:.72rem;color:{FAINT};margin-top:2px">{d}</div></div>'
            f'<div style="font-size:.7rem;color:{MUTED};white-space:nowrap;'
            f'direction:ltr;text-align:left;padding-top:2px">{m}</div></div>')
    st.markdown("".join(rows), unsafe_allow_html=True)

    st.markdown("## مراحل")
    steps = pd.DataFrame([
        ("۰", "تأیید شرح خدمات، لایسنس SQL Server و Report Server، گروه‌های AD", "کارفرما · IT"),
        ("۱", "VM، نصب SQL Server با کالیشن فارسی، بکاپ و بازگردانی", "DBA"),
        ("۲", "بازبینی schema.sql، اجرا در Test، ETL، کنترل کیفیت", "DBA · داده"),
        ("۳", "نصب Report Server، HTTPS، DNS، ساخت .pbix، انتشار", "زیرساخت · BI"),
        ("۴", "RLS و View-as، توازن با مبدأ، تست بار، UAT، آموزش", "BI · مالی"),
    ], columns=["مرحله", "کارها", "مسئول"])
    rtl_table(steps, max_height=None, numeric_cols=["مرحله"])
    quiet("جزئیات کامل با پیش‌نیاز و ریسک در report/DEPLOYMENT_CHECKLIST.md")

    st.markdown("## تصمیم‌ها")
    dec = pd.DataFrame([
        ("تقویم شمسی به‌عنوان کلید تاریخ", "الزام گزارش فارسی", "ستون میلادی موازی"),
        ("Import mode", "استقرار ساده و کارایی", "Refresh زمان‌بندی‌شده"),
        ("Reject در DW", "قابل گزارش و پیگیری", "نگهداشت دوره‌ای"),
        ("SQLite برای اثبات منطق", "اجرای واقعی بدون زیرساخت", "بدون Columnstore"),
        ("RLS فقط مستند", "نبود AD و Report Server", "قبل از انتشار الزامی"),
    ], columns=["تصمیم", "دلیل", "هزینه"])
    rtl_table(dec, max_height=None)


# ------------------------------------------------------------------ ۵) دربارهٔ داده
def page_data() -> None:
    page_head("دربارهٔ داده",
              "کل داده نمونه و قابل بازتولید است. هیچ دیتاست عمومی یا سازمانی استفاده نشده.",
              "شفافیت")

    sales = load_csv("fact_sales")
    returns = load_csv("fact_returns")
    kpis([
        ("seed", fa_digits("۱۴۰۳۰۵۰۵"), "تولید با اسکریپت", ""),
        ("فروش خالص", compact(int(sales["net_amount_irr"].sum())), "ریال", ""),
        ("مرجوعی", fa_num(len(returns)), "سند", ""),
        ("staging", fa_num(len(load_csv("stg_sales_raw", keep_default_na=False))), "ردیف کثیف", ""),
    ])

    st.markdown("## کنترل‌های کیفیت")
    q = pd.DataFrame([
        ("یکتایی sale_id", "بدون تکرار", "گذشت"),
        ("FK فکت به چهار بُعد", "بدون نقض", "گذشت"),
        ("FK مرجوعی به fact_sales", "بدون نقض", "گذشت"),
        ("بازمحاسبهٔ net", "بدون مغایرت", "گذشت"),
        ("منطقهٔ فکت و مشتری", "هم‌خوان", "گذشت"),
        ("تبدیل چهار فرمت تاریخ", "۳۰۰ از ۳۰۰", "گذشت"),
        ("حذف کامای هزارگان", "۱۰۰٪", "گذشت"),
        ("تخفیف خالی به صفر", "۱۰۰٪", "گذشت"),
    ], columns=["کنترل", "نتیجه", "وضعیت"])
    rtl_table(q, max_height=None)

    st.markdown("## محدودیت‌ها")
    lim = pd.DataFrame([
        ("زیرساخت", "SQL Server، Report Server، SSL و شبکه نصب/تست نشده"),
        ("schema.sql", "اجرا نشده؛ نیازمند بازبینی DBA"),
        ("SQLite", "جایگزین محلی؛ بدون Columnstore و پارتیشن"),
        ("Reject", "در نمونه صفر ردیف"),
        ("RLS", "فقط مستند، بدون View-as"),
        ("YTD", "وابسته به dim_date و فرض مرز نوروز"),
        ("گزارش", "بدون .pbix و بدون انتشار"),
        ("شرح خدمات", "پیوست کارفرما موجود نبود"),
        ("ROI", "هیچ ادعای صرفه‌جویی نمی‌شود"),
        ("لایسنس", "تأمین نشده"),
    ], columns=["موضوع", "توضیح"])
    rtl_table(lim, max_height=430)

    st.markdown("## منبع")
    quiet("داده با scripts/generate_all_data.py و seed ثابت تولید می‌شود و با اجرای مجدد عیناً "
          "بازتولید می‌شود. اعداد برای مقیاس سازمانی کالیبره شده‌اند و برآورد بازار نیستند.")


# ------------------------------------------------------------------ اجرا
def main() -> None:
    inject_css()
    page = sidebar()
    try:
        {"نمای کلی": page_overview, "پایپ‌لاین ETL": page_etl, "تحلیل فروش": page_sales,
         "استقرار": page_deploy, "دربارهٔ داده": page_data}[page]()
    except Exception as exc:
        note(f"خطا در نمایش این صفحه: {fa_digits(exc)}")
        with st.expander("جزئیات فنی"):
            st.exception(exc)

    st.markdown('<hr>', unsafe_allow_html=True)
    quiet("پروژهٔ ۵ — دادهٔ نمونه (seed ۱۴۰۳۰۵۰۵) · SQLite جایگزین محلی · "
          "بدون ادعای نصب یا انتشار سازمانی")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — انبار دادهٔ فروش · پروژهٔ ۵
=====================================================================
SQL Server + Data Warehouse + Power BI Report Server — طرح و اثبات منطق.

اجرا:
    streamlit run app.py --server.port 8506 --server.address 0.0.0.0

صداقت: Report Server نصب/لایسنس نشده، schema.sql روی SQL Server واقعی اجرا نشده و
dw_demo.sqlite یک جایگزین محلی است. اعداد از دادهٔ نمونهٔ seed=14030505 می‌آیند و
فروش واقعی هیچ سازمانی نیستند.

طراحی: یک سیستم طراحی توکن‌محور (رنگ، تایپ، فاصله، شعاع) در بالای فایل؛ همهٔ صفحه‌ها
فقط از همین توکن‌ها استفاده می‌کنند تا اندازه‌ها و فونت‌ها یکدست بمانند.
"""
from __future__ import annotations

import base64
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
DB = BASE / "model" / "dw_demo.sqlite"
ETL = BASE / "model" / "etl_staging_to_dw.py"
DIAGRAM_SVG = BASE / "assets" / "model_diagram.svg"
FONTS = BASE / "assets" / "fonts"

# ════════════════════════════════════════════════════════════════════
#  توکن‌های طراحی — تنها منبع حقیقت برای رنگ، اندازه، فاصله
# ════════════════════════════════════════════════════════════════════
T = dict(
    # رنگ
    page="#f3f6fa", surface="#ffffff", tint="#eef5f8", sunken="#eaf0f5",
    line="#e4e8ec", hair="#eef1f4",
    ink="#18202b", ink2="#46525f", muted="#78838f", faint="#9aa4af",
    accent="#123b5a", accent_soft="#eaf3f7", accent_line="#c8dce7",
    good="#098b87", warn_bg="#fbf7ef", warn_line="#e9dcc4", warn_ink="#84673a",
    # تایپوگرافی (rem)
    fs_display="1.5rem", fs_h2="1.02rem", fs_h3=".9rem",
    fs_body=".875rem", fs_small=".79rem", fs_micro=".72rem",
    # فاصله
    gap_page="1.9rem", gap_block="1.15rem",
    radius="10px", radius_sm="7px",
)
FONT = "'Vazirmatn FD', Vazirmatn, Tahoma, sans-serif"

PAGES = ["نمای کلی", "پایپ‌لاین ETL", "تحلیل فروش", "استقرار", "دربارهٔ داده"]

st.set_page_config(page_title="انبار دادهٔ فروش · پروژهٔ ۵", page_icon="▦",
                   layout="wide", initial_sidebar_state="expanded")

# ------------------------------------------------------------------ کمکی
_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(x) -> str:
    return str(x).translate(_FA)


def num(n, d: int = 0) -> str:
    try:
        s = f"{n:,.{d}f}"
    except (TypeError, ValueError):
        return fa(n)
    return fa(s).replace(",", "٬").replace(".", "٫")


def money(v) -> str:
    v = float(v or 0)
    if abs(v) >= 1e12:
        return f"{num(v / 1e12, 2)} همت"
    if abs(v) >= 1e9:
        return f"{num(v / 1e9, 0)} میلیارد"
    return num(v)


def _faces() -> str:
    out = []
    for f, w in (("Vazirmatn-Regular.woff2", 400), ("Vazirmatn-Medium.woff2", 500),
                 ("Vazirmatn-Bold.woff2", 700)):
        p = FONTS / f
        if p.exists():
            b64 = base64.b64encode(p.read_bytes()).decode()
            out.append("@font-face{font-family:'Vazirmatn FD';font-weight:%d;font-style:normal;"
                       "font-display:swap;src:url(data:font/woff2;base64,%s) format('woff2')}"
                       % (w, b64))
    return "\n".join(out)


def css() -> str:
    return f"""
<style>
{_faces()}

/* ── پایه ───────────────────────────────────────────────────── */
html, body, .stApp, .stApp *, button, input, select, textarea, p, span, div, li, a,
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] *,
[data-testid="stMarkdown"], [data-testid="stMarkdown"] * {{
  font-family:{FONT} !important;
  -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
}}
html, body, .stApp {{ direction:rtl; }}
.stApp {{ background:{T['page']}; }}
.stApp, .stApp p, .stApp span, .stApp div, .stApp li, .stApp label,
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"], [data-testid="stHeading"],
[data-testid="stMetricLabel"], [data-testid="stExpander"] {{
  direction:rtl !important; text-align:right;
}}
.stApp code, .stApp pre, .stApp pre *, .stApp kbd {{
  direction:ltr !important; text-align:left !important; unicode-bidi:embed;
}}
[data-testid="stMarkdownContainer"] {{ font-size:{T['fs_body']}; line-height:1.9; color:{T['ink2']}; }}
[data-testid="stMarkdownContainer"] p {{ margin:0 0 .5rem; }}
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3, [data-testid="stMarkdownContainer"] h4 {{
  color:{T['ink']} !important; font-weight:600 !important; letter-spacing:-.15px;
  font-style:normal !important; padding:0 !important; margin-top:0 !important;
}}
.block-container {{ padding:1.9rem 2.2rem 3rem; max-width:1220px; }}
hr {{ border:none; border-top:1px solid {T['hair']}; margin:1.2rem 0; }}
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapseButton"] *,
[data-testid="collapsedControl"], [data-testid="collapsedControl"] * {{ display:none !important; }}

/* ── پرچم‌های بخش ─────────────────────────────────────────── */
.sec {{ margin:{T['gap_block']} 0 .55rem; }}
.sec + .sec {{ margin-top:{T['gap_page']}; }}
.sec .t {{ font-size:{T['fs_h2']} !important; font-weight:600 !important;
  color:{T['ink']} !important; letter-spacing:-.2px; line-height:1.6; }}
.sec .d {{ font-size:{T['fs_micro']} !important; color:{T['faint']} !important; margin-top:3px; }}
.sec .t::after {{
  content:""; display:block; width:26px; height:2px; background:{T['accent']};
  border-radius:2px; margin-top:7px; opacity:.8;
}}

/* ── سربرگ صفحه ────────────────────────────────────────────── */
.head {{ margin:0 0 {T['gap_page']}; padding-top:2px; padding-bottom:1.1rem; border-bottom:1px solid {T['line']}; }}
.head .eyebrow {{
  font-size:{T['fs_micro']} !important; color:{T['accent']} !important;
  font-weight:500 !important; font-style:normal !important; letter-spacing:.3px;
  margin-bottom:6px; line-height:1.9; display:block;
}}
.head h1 {{ font-size:{T['fs_display']} !important; margin:0 0 8px !important;
  letter-spacing:-.4px; color:{T['ink']} !important; line-height:1.5; }}
.head .lede {{ font-size:{T['fs_small']} !important; color:{T['muted']} !important;
  line-height:1.9; max-width:70ch; }}

/* ── سایدبار ───────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{ background:{T['surface']}; border-left:1px solid {T['line']}; }}
section[data-testid="stSidebar"] * {{ font-family:{FONT} !important; }}
section[data-testid="stSidebar"] .block-container {{ padding:1.1rem .95rem 1.4rem; }}
.brand {{ padding:0 2px .85rem; border-bottom:1px solid {T['hair']}; margin-bottom:.7rem; }}
.brand .mark {{
  width:28px; height:28px; border-radius:7px; background:{T['ink']}; color:#fff;
  display:flex; align-items:center; justify-content:center; font-size:.82rem; margin-bottom:9px;
}}
.brand .name {{ font-size:.86rem; font-weight:600; color:{T['ink']}; letter-spacing:-.1px; }}
.brand .sub {{ font-size:{T['fs_micro']}; color:{T['muted']}; margin-top:3px; line-height:1.75; }}
section[data-testid="stSidebar"] [role="radiogroup"] {{ gap:1px !important; }}
section[data-testid="stSidebar"] [role="radiogroup"] label {{
  padding:6px 9px !important; border-radius:{T['radius_sm']}; min-height:0 !important;
  margin:0 !important; cursor:pointer; transition:background .14s;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label > div,
section[data-testid="stSidebar"] [role="radiogroup"] label > div > div {{
  min-height:0 !important; gap:0 !important; padding:0 !important; align-items:center !important;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label > div > div:first-child {{ display:none; }}
section[data-testid="stSidebar"] [role="radiogroup"] label [data-testid="stMarkdownContainer"] p {{
  margin:0 !important; font-size:{T['fs_small']} !important; line-height:1.9 !important;
  color:{T['ink2']};
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover {{ background:{T['tint']}; }}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
  background:{T['sunken']};
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{
  color:{T['ink']} !important; font-weight:500;
}}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)::before {{
  content:""; position:absolute; inset-inline-start:0; top:7px; bottom:7px;
  width:2px; border-radius:2px; background:{T['accent']};
}}
section[data-testid="stSidebar"] [role="radiogroup"] label {{ position:relative; }}
.side-meta {{
  margin-top:1rem; padding-top:.85rem; border-top:1px solid {T['hair']};
  font-size:{T['fs_micro']}; color:{T['muted']}; line-height:2;
}}
.side-meta .row {{ display:flex; justify-content:space-between; gap:8px; }}
.side-meta .k {{ color:{T['faint']}; }}
.side-meta .v {{ color:{T['ink2']}; font-weight:500; }}

/* ── KPI ───────────────────────────────────────────────────── */
.kpis {{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(158px,1fr));
  background:{T['surface']}; border:1px solid {T['line']}; border-radius:{T['radius']};
  overflow:hidden; margin:0 0 {T['gap_block']};
}}
.kpi {{ padding:.85rem 1.05rem .9rem; border-inline-start:1px solid {T['hair']}; }}
.kpi:first-child {{ border-inline-start:none; }}
.kpi .lb {{ font-size:{T['fs_micro']} !important; color:{T['muted']} !important;
  margin-bottom:6px; white-space:nowrap; }}
.kpi .vl {{ font-size:1.12rem !important; font-weight:600 !important; color:{T['ink']} !important;
  letter-spacing:-.3px; line-height:1.5; font-variant-numeric:tabular-nums; }}
.kpi .hint {{ font-size:{T['fs_micro']}; color:{T['faint']}; margin-top:4px; }}
.kpi.accent .vl {{ color:{T['accent']}; }}
.kpi.quiet .vl {{ font-size:.88rem; font-weight:500; color:{T['warn_ink']}; }}

/* ── کارت ──────────────────────────────────────────────────── */
.card {{
  background:{T['surface']}; border:1px solid {T['line']}; border-radius:{T['radius']};
  padding:1rem 1.15rem 1.1rem;
}}
/* کارتِ ویجت‌دار: st.container(border=True) */
[data-testid="stVerticalBlockBorderWrapper"] {{
  background:{T['surface']} !important; border:1px solid {T['line']} !important;
  border-radius:{T['radius']} !important; box-shadow:0 1px 2px rgba(24,32,43,.035);
}}
[data-testid="stVerticalBlockBorderWrapper"] > div {{ padding:.15rem .2rem .1rem; }}
.ct {{ font-size:{T['fs_h3']} !important; font-weight:600 !important;
  color:{T['ink']} !important; letter-spacing:-.1px; line-height:1.7; }}
.cd {{ font-size:{T['fs_micro']} !important; color:{T['faint']} !important; margin:2px 0 0; }}

/* ── بنر/یادداشت ───────────────────────────────────────────── */
.note {{
  background:{T['warn_bg']}; border:1px solid {T['warn_line']}; border-radius:{T['radius_sm']};
  padding:.7rem .9rem; font-size:{T['fs_small']}; color:{T['warn_ink']}; line-height:1.85;
}}
.note.ok {{ background:#f3f7f4; border-color:#d5e3da; color:{T['good']}; }}
.hint {{ font-size:{T['fs_micro']}; color:{T['faint']}; line-height:1.85; margin-top:.35rem; }}

/* ── جدول ──────────────────────────────────────────────────── */
.tw {{ background:{T['surface']}; border:1px solid {T['line']}; border-radius:{T['radius']};
  overflow:auto; max-height:var(--h,None); }}
table.rt {{ width:100%; border-collapse:collapse; direction:rtl; }}
table.rt thead th {{
  position:sticky; top:0; z-index:2; background:{T['surface']};
  font-size:{T['fs_micro']} !important; font-weight:500 !important; color:{T['muted']} !important;
  padding:.5rem .8rem; text-align:right; white-space:nowrap;
  border-bottom:1px solid {T['line']};
}}
table.rt tbody td {{
  font-size:{T['fs_small']} !important; color:{T['ink2']} !important; padding:.46rem .8rem;
  border-bottom:1px solid {T['hair']}; text-align:right; line-height:1.7;
}}
table.rt tbody tr:last-child td {{ border-bottom:none; }}
table.rt tbody tr:hover td {{ background:{T['tint']}; }}
table.rt td.n {{ font-variant-numeric:tabular-nums; color:{T['ink']}; white-space:nowrap; }}
table.rt td.m {{
  direction:ltr; text-align:left; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
  font-size:{T['fs_micro']}; color:{T['muted']};
}}

/* ── نمودار ────────────────────────────────────────────────── */
.js-plotly-plot, .js-plotly-plot .plot-container {{ direction:ltr !important; }}
.js-plotly-plot .main-svg text {{ font-family:{FONT} !important; }}
.diagram svg {{ width:100%; height:auto; display:block; }}
.diagram svg text {{ font-family:{FONT} !important; }}

/* ── کنترل‌ها ──────────────────────────────────────────────── */
.stButton > button {{
  background:{T['surface']}; color:{T['accent']}; border:1px solid {T['accent_line']};
  border-radius:{T['radius_sm']}; padding:.4rem 1rem; font-size:{T['fs_small']};
  font-weight:500; box-shadow:none; transition:background .14s,border-color .14s;
}}
.stButton > button:hover {{ background:{T['accent_soft']}; border-color:{T['accent']}; color:{T['accent']}; }}
[data-baseweb="select"] > div {{ border-radius:{T['radius_sm']}; font-size:{T['fs_small']}; }}
[data-baseweb="select"] div {{ direction:rtl !important; }}
[data-baseweb="tag"] {{ background:{T['sunken']} !important; color:{T['ink2']} !important;
  font-size:{T['fs_micro']} !important; border-radius:4px !important; }}
[data-testid="stExpander"] {{ border:1px solid {T['line']} !important; border-radius:{T['radius_sm']} !important; }}

[data-testid="stVerticalBlockBorderWrapper"] {{background:#fff!important;}}
/* Dashboard v4: structural cards and consistent visual hierarchy */
.head {{background:#fff;border:1px solid #dfe7ee;border-right:5px solid #123b5a;border-radius:14px;padding:22px 26px!important;box-shadow:0 4px 18px #123b5a06;}}
.head .eyebrow {{color:#098b87!important;font-weight:700;}}
.kpis {{display:grid!important;grid-template-columns:repeat(4,minmax(0,1fr))!important;gap:16px!important;margin:18px 0 8px!important;}}
.kpi {{background:#fff!important;border:1px solid #dfe7ee!important;border-top:4px solid #123b5a!important;border-radius:12px!important;padding:20px!important;min-height:139px;box-shadow:0 3px 12px #123b5a05;}}
.kpi:nth-child(2) {{border-top-color:#098b87!important;}}
.kpi:nth-child(3) {{border-top-color:#d6a321!important;}}
.kpi:nth-child(4) {{border-top-color:#c45a54!important;}}
.kpi .lb {{font-size:.79rem!important;color:#526476!important;}}
.kpi .vl {{font-size:1.55rem!important;color:#123b5a!important;margin:13px 0 8px!important;font-weight:700!important;}}
.kpi .hint {{font-size:.72rem!important;}}
[data-testid="stVerticalBlockBorderWrapper"]>div,[data-testid="stLayoutWrapper"]>[data-testid="stVerticalBlockBorderWrapper"] {{border-radius:14px!important;}}
.ct {{color:#123b5a!important;font-size:1.02rem!important;font-weight:700!important;border-right:3px solid #098b87;padding-right:10px!important;}}
.cd {{margin:6px 0 12px!important;}}
section[data-testid="stSidebar"] {{background:#fff!important;border-left:1px solid #dfe7ee;}}
.brand {{background:#123b5a!important;border-radius:12px;padding:23px 18px!important;border-bottom:4px solid #d6a321!important;}}
.brand .name,.brand .sub,.brand .mark {{color:#fff!important;}}
section[data-testid="stSidebar"] [role="radiogroup"] label {{background:#f2f6f9;border:1px solid #e3ebf1;border-radius:8px;padding:9px 12px!important;margin:4px 0!important;}}
@media(max-width:760px){{.kpis{{grid-template-columns:repeat(2,minmax(0,1fr))!important;}}.block-container{{padding:1rem!important;}}}}

</style>
"""


# ------------------------------------------------------------------ اجزای UI
def head(title: str, lede: str, eyebrow: str = "") -> None:
    eyebrow_html = f'<div class="eyebrow">{eyebrow}</div>' if eyebrow else ""
    st.markdown(
        f'<div class="head">{eyebrow_html}'
        f'<h1>{title}</h1><div class="lede">{lede}</div></div>',
        unsafe_allow_html=True)


def sec(title: str, desc: str = "") -> None:
    d = f'<div class="d">{desc}</div>' if desc else ""
    st.markdown(f'<div class="sec"><div class="t">{title}</div>{d}</div>', unsafe_allow_html=True)


def kpis(items: list[tuple]) -> None:
    """[(label, value, hint, kind)] kind: '' | 'accent' | 'quiet'"""
    cells = []
    for item in items:
        lb, vl = item[0], item[1]
        hnt = item[2] if len(item) > 2 else ""
        kind = item[3] if len(item) > 3 else ""
        h = f'<div class="hint">{hnt}</div>' if hnt else ""
        cells.append(f'<div class="kpi {kind}"><div class="lb">{lb}</div>'
                     f'<div class="vl">{vl}</div>{h}</div>')
    st.markdown('<div class="kpis">' + "".join(cells) + "</div>", unsafe_allow_html=True)


def card_open(title: str = "", desc: str = "", lift: bool = False) -> None:
    t = f'<div class="ct">{title}</div>' if title else ""
    d = f'<div class="cd">{desc}</div>' if desc else ""
    st.markdown(f'<div class="card{" lift" if lift else ""}">{t}{d}', unsafe_allow_html=True)


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def note(text: str, kind: str = "") -> None:
    st.markdown(f'<div class="note {kind}">{text}</div>', unsafe_allow_html=True)


def hint(text: str) -> None:
    st.markdown(f'<div class="hint">{text}</div>', unsafe_allow_html=True)


def _cls(col: str, val) -> str:
    s = str(col)
    if s in ("فایل", "ستون", "جدول", "مؤلفه") or str(val).startswith(("dw.", "stg.", "model/", "scripts/")):
        return "m"
    try:
        float(str(val).replace("٬", "").replace(",", "").replace("٪", ""))
        return "n"
    except (TypeError, ValueError):
        return ""


def table(df: pd.DataFrame, height: int | None = None, numeric: list[str] | None = None) -> None:
    """جدول راست‌چین (st.dataframe همیشه LTR است و اینجا استفاده نمی‌شود)."""
    import html as h

    numeric = numeric or []
    ths = "".join(f"<th>{h.escape(str(c))}</th>" for c in df.columns)
    rows = []
    for _, r in df.iterrows():
        tds = "".join(
            f'<td class="{"n" if str(c) in numeric else _cls(c, r[c])}">{h.escape(str(r[c]))}</td>'
            for c in df.columns)
        rows.append(f"<tr>{tds}</tr>")
    style = f' style="--h:{height}px"' if height else ""
    st.markdown(f'<div class="tw"{style}><table class="rt"><thead><tr>{ths}</tr></thead>'
                f'<tbody>{"".join(rows)}</tbody></table></div>', unsafe_allow_html=True)


def figure(fig: go.Figure, height: int, margin: dict) -> None:
    fig.update_layout(
        height=height, margin=margin,
        paper_bgcolor=T["surface"], plot_bgcolor=T["surface"],
        font=dict(family="Vazirmatn FD, Vazirmatn, Tahoma, sans-serif", size=10.5, color=T["ink2"]),
        showlegend=False, title=None,
        hoverlabel=dict(font=dict(family="Vazirmatn FD, Vazirmatn, Tahoma", size=10.5),
                        bgcolor=T["surface"], bordercolor=T["line"]),
        separators="٫,",
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=T["line"], ticks="",
                     tickfont=dict(size=10, color=T["muted"]), automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor=T["hair"], zeroline=False, ticks="",
                     tickfont=dict(size=10, color=T["muted"]), automargin=True)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "locale": "fa"})


def fa_axis(fig: go.Figure, axis: str, ticks: list, suffix: str = "", d: int = 1) -> None:
    """تیک‌های محور با ارقام فارسی (Plotly خودش فارسی نمی‌نویسد)."""
    labels = [f"{num(v, d)}{(' ' + suffix) if suffix else ''}" for v in ticks]
    kw = dict(tickmode="array", tickvals=list(ticks), ticktext=labels)
    (fig.update_xaxes if axis == "x" else fig.update_yaxes)(**kw)


def nice_ticks(vmax: float, n: int = 5) -> list:
    import math
    if vmax <= 0:
        return [0]
    raw = vmax / max(1, n - 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = min((1, 2, 2.5, 5, 10), key=lambda m: abs(m * mag - raw)) * mag
    return [round(i * step, 6) for i in range(int(vmax / step) + 2)]


def chart_card(title: str, desc: str) -> None:
    """عنوان کوچک داخل کارتِ ویجت‌دار."""
    st.markdown(f'<div class="ct">{title}</div><div class="cd">{desc}</div>',
                unsafe_allow_html=True)


def hbar(fig: go.Figure) -> go.Figure:
    """قرارداد RTL: میله از راست رشد می‌کند، برچسب دسته در حاشیهٔ آزاد چپ."""
    fig.update_xaxes(autorange="reversed")
    fig.update_yaxes(side="left", ticklabelposition="outside left", ticks="",
                     tickfont=dict(size=10, color=T["ink2"]))
    return fig


# ------------------------------------------------------------------ داده
@st.cache_data(show_spinner=False)
def csv(name: str, keep_na: bool = True) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv", encoding="utf-8-sig", keep_default_na=keep_na)


@st.cache_data(show_spinner=False)
def db_summary(path: str, mtime: float) -> dict:
    import sqlite3
    con = sqlite3.connect(path)
    out = {}
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        try:
            out[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        except Exception:
            out[t] = None
    for key, q in (("_net", "SELECT COALESCE(SUM(net_amount_irr),0) FROM fact_sales"),
                   ("_ret", "SELECT COALESCE(SUM(return_amount_irr),0) FROM fact_returns"),
                   ("_reg", "SELECT COUNT(DISTINCT region_id) FROM fact_sales"),
                   ("_rej", "SELECT COUNT(*) FROM etl_reject")):
        try:
            out[key] = con.execute(q).fetchone()[0]
        except Exception:
            pass
    con.close()
    return out


def db_stamp() -> float:
    return DB.stat().st_mtime if DB.exists() else 0.0


# ------------------------------------------------------------------ سایدبار
def sidebar() -> str:
    with st.sidebar:
        st.markdown(
            '<div class="brand"><div class="mark">▦</div>'
            '<div class="name">انبار دادهٔ فروش</div>'
            '<div class="sub">SQL Server · DW · Report Server<br>پروژهٔ ۵ — ۱۴۰۵/۰۹/۰۵</div></div>',
            unsafe_allow_html=True)
        page = st.radio("صفحه", PAGES, label_visibility="collapsed")
        st.markdown(
            '<div class="side-meta">'
            '<div class="row"><span class="k">زیرساخت</span><span class="v">نصب‌نشده</span></div>'
            '<div class="row"><span class="k">ETL</span><span class="v">اجراشده</span></div>'
            '<div class="row"><span class="k">داده</span><span class="v">نمونه</span></div>'
            '<div class="row"><span class="k">واحد</span><span class="v">ریال</span></div>'
            '</div>', unsafe_allow_html=True)
    return page


# ══════════════════════════════════════════════════════════════════ ۱) نمای کلی
def page_overview() -> None:
    head("نمای مدیریتی فروش و انبار داده", "عملکرد فروش، پراکندگی بازار و مرجوعی‌ها · سال ۱۴۰۳ · واحد مبالغ: ریال", "انبار دادهٔ فروش / نمای کلی")
    sales, returns = csv("fact_sales"), csv("fact_returns")
    dates, regions, products = csv("dim_date"), csv("dim_region"), csv("dim_product")
    with st.sidebar:
        sec("فیلترهای تحلیلی", "محدودهٔ نمای کلی")
        choices = regions.set_index("region_id")["region_name_fa"].to_dict()
        selected = st.multiselect("منطقهٔ فروش", list(choices), format_func=lambda k: choices[k], placeholder="همهٔ مناطق", key="overview_region")
        cats = st.multiselect("گروه محصول", products["category_name_fa"].unique().tolist(), placeholder="همهٔ گروه‌ها", key="overview_category")
    sf, rf = sales.copy(), returns.copy()
    if selected:
        sf = sf[sf.region_id.isin(selected)]
        rf = rf[rf.region_id.isin(selected)]
    if cats:
        ids = products.loc[products.category_name_fa.isin(cats), "product_id"]
        sf = sf[sf.product_id.isin(ids)]
        rf = rf[rf.product_id.isin(ids)]
    net, ret = float(sf.net_amount_irr.sum()), float(rf.return_amount_irr.sum())
    kpis([("فروش خالص", money(net), "ریال · پس از تخفیف"),
          ("ردیف‌های فروش", num(len(sf)), "هر ردیف یک قلم فروش؛ نه تعداد فاکتور"),
          ("مبلغ برگشتی", money(ret), "ریال · ثبت‌شده در دوره"),
          ("نسبت مبلغ برگشتی", num(100*ret/net, 2)+"٪" if net else "—", "مبلغ برگشتی ÷ فروش خالص")])
    hint("دادهٔ نمونه است؛ فروش واقعی سازمان نیست. فیلترها بر تمام شاخص‌ها و نمودارهای این صفحه اعمال می‌شوند.")
    m = (sf.merge(dates[["date_key", "month", "month_name_fa"]], on="date_key")
         .groupby(["month", "month_name_fa"], as_index=False).net_amount_irr.sum().sort_values("month"))
    rm = (rf.merge(dates[["date_key", "month"]], on="date_key").groupby("month").return_amount_irr.sum())
    c1,c2 = st.columns(2)
    with c1, st.container(border=True):
        chart_card("روند ماهانهٔ فروش", "فروش خالص · میلیارد ریال")
        f = go.Figure(go.Scatter(x=m.month_name_fa,y=m.net_amount_irr/1e9,mode="lines+markers",line=dict(color="#098b87",width=3),marker=dict(size=7,color="#123b5a"),fill="tozeroy",fillcolor="rgba(9,139,135,.10)",hovertemplate="%{x}<br>%{y:,.1f} میلیارد ریال<extra></extra>"))
        fa_axis(f,"y",nice_ticks(float(m.net_amount_irr.max()/1e9) if len(m) else 0),d=0)
        figure(f,285,dict(l=55,r=15,t=15,b=45))
    with c2, st.container(border=True):
        chart_card("سهم مناطق از فروش", "رتبه‌بندی مناطق · میلیارد ریال")
        r = sf.groupby("region_id",as_index=False).net_amount_irr.sum().merge(regions,on="region_id").sort_values("net_amount_irr")
        colors=["#098b87"]*len(r)
        if colors: colors[-1]="#d6a321"
        f=go.Figure(go.Bar(x=r.net_amount_irr/1e9,y=r.region_name_fa,orientation="h",marker_color=colors,text=[num(v/1e9,0) for v in r.net_amount_irr],textposition="inside",textangle=0,textfont_color="white"))
        fa_axis(f,"x",nice_ticks(float(r.net_amount_irr.max()/1e9) if len(r) else 0),d=0)
        hbar(f)
        figure(f,285,dict(l=75,r=10,t=10,b=35))
    c3,c4=st.columns(2)
    with c3, st.container(border=True):
        chart_card("ترکیب فروش گروه‌های محصول", "سهم هر گروه از مبلغ فروش خالص")
        g=sf.merge(products,on="product_id").groupby("category_name_fa",as_index=False).net_amount_irr.sum()
        f=go.Figure(go.Pie(labels=g.category_name_fa,values=g.net_amount_irr,hole=.66,sort=False,marker=dict(colors=["#123b5a","#098b87","#d6a321","#6b94ab","#91c5bd","#d4dfe8"]),textinfo="label",textposition="outside",hovertemplate="%{label}<br>%{value:,.0f} ریال<extra></extra>"))
        figure(f,285,dict(l=45,r=45,t=25,b=25))
    with c4, st.container(border=True):
        chart_card("برگشتی‌های ماهانه", "مبلغ برگشتی بر اساس تاریخ ثبت برگشت · میلیارد ریال")
        vals=[float(rm.get(v,0))/1e9 for v in m.month]
        f=go.Figure(go.Bar(x=m.month_name_fa,y=vals,marker_color="#d6a321",text=[num(v,1) for v in vals],textposition="outside",cliponaxis=False))
        fa_axis(f,"y",nice_ticks(max(vals) if vals else 0),d=0)
        figure(f,285,dict(l=45,r=15,t=20,b=45))
    sec("محصولات پیشتاز", "ده محصول با بیشترین فروش خالص در محدودهٔ انتخاب‌شده")
    top=sf.groupby("product_id",as_index=False).agg(net_amount_irr=("net_amount_irr","sum"),quantity=("quantity","sum")).merge(products[["product_id","product_name_fa","category_name_fa"]],on="product_id").nlargest(10,"net_amount_irr")
    top=top[["product_name_fa","category_name_fa","quantity","net_amount_irr"]]
    top.columns=["محصول","گروه","تعداد","فروش خالص (ریال)"]
    table(top,height=360,numeric=["تعداد","فروش خالص (ریال)"])
    with st.expander("معماری و حدود اجرای این نمونه"):
        note("SQLite جایگزین محلی است؛ SQL Server واقعی و نصب Report Server آزموده نشده‌اند. RLS فقط مستند است.")
        if DIAGRAM_SVG.exists():
            st.markdown(DIAGRAM_SVG.read_text(encoding="utf-8"),unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════ ۲) ETL
def page_etl() -> None:
    head("پایپ‌لاین ETL",
         "اسکریپت واقعی با یک کلیک اجرا می‌شود و خروجی‌اش همان‌طور که هست نمایش داده می‌شود.",
         "اثبات اجرایی")

    stg = csv("stg_sales_raw", keep_na=False)
    kpis([
        ("ردیف ورودی", num(len(stg)), "stg_sales_raw"),
        ("فرمت تاریخ", "۴ نوع", "شمسی و میلادی"),
        ("کاما هزارگان", num(int(stg["unit_price_raw"].astype(str).str.contains(",").sum())), "ردیف"),
        ("تخفیف خالی", num(int((stg["discount_raw"].astype(str).str.strip() == "").sum())), "ردیف"),
    ])

    sec("ورودی خام", "همان چیزی که ETL دریافت می‌کند: تاریخ مخلوط، فاصلهٔ اضافه، کاما")
    show = stg.head(6)[["row_id", "sale_date_raw", "customer_name_raw", "region_id_raw",
                        "quantity_raw", "unit_price_raw", "discount_raw"]].copy()
    show.columns = ["#", "تاریخ", "مشتری", "منطقه", "تعداد", "مبلغ واحد", "تخفیف"]
    table(show, numeric=["#", "تعداد", "مبلغ واحد", "تخفیف"])

    sec("اجرا")
    c1, c2, _ = st.columns([1, 1, 2.6])
    run = c1.button("اجرای ETL", width="stretch")
    if c2.button("بازخوانی", width="stretch"):
        st.cache_data.clear()
        st.rerun()

    if run:
        with st.spinner("در حال اجرا…"):
            try:
                cp = subprocess.run([sys.executable, str(ETL)], cwd=str(BASE),
                                    capture_output=True, text=True, timeout=240)
                out = cp.stdout or ""
                if cp.stderr.strip():
                    out += "\n[stderr]\n" + cp.stderr
                st.session_state["etl_out"], st.session_state["etl_rc"] = out, cp.returncode
                st.cache_data.clear()
            except subprocess.TimeoutExpired:
                st.session_state["etl_out"] = "اجرا بیش از ۲۴۰ ثانیه طول کشید."
                st.session_state["etl_rc"] = -1

    out, rc = st.session_state.get("etl_out"), st.session_state.get("etl_rc")
    if out:
        note("اجرا با موفقیت تمام شد — خروجی متنیِ همان اجراست." if rc == 0
             else f"اجرا با خطا تمام شد (کد {fa(rc)}).", "ok" if rc == 0 else "")
        st.code(out, language="text")
    else:
        hint("هنوز در این نشست اجرا نشده است؛ لاگ اجرای ساخت پروژه در VALIDATION.md ثبت شده.")

    sec("محتوای پایگاه‌داده")
    if DB.exists():
        db = db_summary(str(DB), db_stamp())
        order = ["dim_date", "dim_region", "dim_customer", "dim_product", "fact_sales",
                 "fact_returns", "etl_reject", "etl_load_log"]
        df = pd.DataFrame([{"جدول": t, "ردیف": num(db.get(t) if db.get(t) is not None else "—")}
                           for t in order if t in db])
        c1, c2 = st.columns([1.3, 1])
        with c1:
            table(df, height=310, numeric=["ردیف"])
        with c2:
            kpis([("جمع فروش", money(db.get("_net", 0)), "ریال"),
                  ("مناطق", num(db.get("_reg", 0)), "از ۱۲"),
                  ("Reject", "بدون ردیف", "etl_reject خالی", "quiet")])
            ts = pd.Timestamp(DB.stat().st_mtime, unit="s", tz="UTC")
            hint("آخرین نوشتن: " + fa(ts.tz_convert("Asia/Tehran").strftime("%Y/%m/%d · %H:%M")))
    else:
        note("dw_demo.sqlite موجود نیست؛ ابتدا ETL را اجرا کنید.")

    sec("مسیر Reject", "کد و جدول آماده است؛ در این نمونه خطایی رخ نداد")
    hint("برای دیدن مسیر، ردیفی با تاریخ ۱۴۰۳/۱۳/۴۵ یا مبلغ abc یا منطقهٔ R99 به فایل staging "
         "اضافه کنید.")


# ══════════════════════════════════════════════════════════════════ ۳) تحلیل فروش
def page_sales() -> None:
    head("تحلیل فروش",
         "نمای نمونه از گزارش‌هایی که روی Report Server منتشر می‌شوند؛ واحد ریال و تقویم شمسی.",
         "دادهٔ نمونه")

    sales, returns = csv("fact_sales"), csv("fact_returns")
    ddate, dregion, dproduct = csv("dim_date"), csv("dim_region"), csv("dim_product")

    names = dregion.set_index("region_id")["region_name_fa"].to_dict()
    fcol, _ = st.columns([1, 2.6])
    with fcol:
        picked = st.multiselect("منطقه", options=list(names.keys()),
                                format_func=lambda r: names[r], default=[],
                                placeholder="همهٔ مناطق")
    sf = sales[sales["region_id"].isin(picked)] if picked else sales
    rf = returns[returns["region_id"].isin(picked)] if picked else returns

    net = int(sf["net_amount_irr"].sum())
    ret = int(rf["return_amount_irr"].sum())
    margin = (net - int(sf["cost_amount_irr"].sum())) / net if net else 0
    kpis([
        ("فروش خالص", money(net), "ریال"),
        ("تعداد", num(int(sf["quantity"].sum())), "قلم"),
        ("حاشیهٔ سود", fa(f"{margin * 100:.1f}") + "٪", "", "accent"),
        ("نرخ مرجوعی", fa(f"{ret / net * 100:.2f}") + "٪" if net else "—", ""),
    ])

    merged = sf.merge(ddate[["date_key", "month", "month_name_fa"]], on="date_key")

    sec("روند و پراکندگی", "نمودارها از دادهٔ همین فیلتر ساخته می‌شوند")

    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        chart_card("فروش ماهانه", "مجموع فروش خالص در هر ماه شمسی")
        m = (merged.groupby(["month", "month_name_fa"], as_index=False)["net_amount_irr"]
             .sum().sort_values("month"))
        vmax = float(m["net_amount_irr"].max()) / 1e12
        ticks = nice_ticks(vmax * 1.16, 5)
        fig = go.Figure(go.Scatter(
            x=m["month_name_fa"], y=m["net_amount_irr"] / 1e12, mode="lines",
            line=dict(color=T["accent"], width=2, shape="spline"),
            customdata=m["net_amount_irr"],
            hovertemplate="%{x}<br>%{customdata:,.0f} ریال<extra></extra>",
            fill="tozeroy", fillcolor="rgba(156,74,60,0.05)"))
        fig.update_yaxes(range=[0, ticks[-1]])
        fa_axis(fig, "y", ticks, "همت", 1)
        fig.update_xaxes(tickmode="array", tickvals=list(m["month_name_fa"][::2]), tickangle=0)
        figure(fig, 246, dict(l=64, r=16, t=10, b=32))

    with c2, st.container(border=True):
        chart_card("فروش منطقه‌ای", "خالص به تفکیک منطقه")
        r = (sf.groupby("region_id", as_index=False)["net_amount_irr"].sum()
             .merge(dregion[["region_id", "region_name_fa"]], on="region_id")
             .sort_values("net_amount_irr"))
        vmax = float(r["net_amount_irr"].max()) / 1e12
        ticks = nice_ticks(vmax * 1.02, 4)
        fig = go.Figure(go.Bar(
            x=r["net_amount_irr"] / 1e12, y=r["region_name_fa"], orientation="h",
            marker=dict(color=T["accent"], opacity=.55, line=dict(width=0)),
            text=[num(v / 1e12, 2) for v in r["net_amount_irr"]],
            textposition="inside", insidetextanchor="start",
            textfont=dict(size=9.5, color="#ffffff"), cliponaxis=False,
            customdata=r["net_amount_irr"],
            hovertemplate="%{y}<br>%{customdata:,.0f} ریال<extra></extra>"))
        fig.update_xaxes(range=[ticks[-1], 0])
        fa_axis(fig, "x", ticks, "همت", 1)
        hbar(fig)
        figure(fig, 246, dict(l=68, r=16, t=10, b=32))

    c3, c4 = st.columns(2)
    with c3, st.container(border=True):
        chart_card("دستهٔ کالا", "سهم هر دسته از فروش خالص")
        cat = (sf.merge(dproduct[["product_id", "category_name_fa"]], on="product_id")
               .groupby("category_name_fa", as_index=False)["net_amount_irr"].sum()
               .sort_values("net_amount_irr", ascending=False))
        vmax = float(cat["net_amount_irr"].max()) / 1e12
        ticks = nice_ticks(vmax * 1.28, 4)
        fig = go.Figure(go.Bar(
            x=cat["category_name_fa"], y=cat["net_amount_irr"] / 1e12,
            marker=dict(color="#8b95a1", opacity=.55, line=dict(width=0)),
            text=[num(v / 1e12, 1) for v in cat["net_amount_irr"]],
            textposition="outside", textfont=dict(size=9.5, color=T["muted"]),
            cliponaxis=False, customdata=cat["net_amount_irr"],
            hovertemplate="%{x}<br>%{customdata:,.0f} ریال<extra></extra>"))
        fig.update_yaxes(range=[0, ticks[-1]])
        fa_axis(fig, "y", ticks, "همت", 1)
        figure(fig, 244, dict(l=58, r=16, t=10, b=52))

    with c4, st.container(border=True):
        chart_card("علت مرجوعی", "مبلغ برگشتی به تفکیک علت")
        rr = (rf.groupby("reason_fa", as_index=False)["return_amount_irr"].sum()
              .sort_values("return_amount_irr"))
        vmax = float(rr["return_amount_irr"].max()) / 1e9
        ticks = nice_ticks(vmax * 1.02, 3)
        fig = go.Figure(go.Bar(
            x=rr["return_amount_irr"] / 1e9, y=rr["reason_fa"], orientation="h",
            marker=dict(color=T["accent"], opacity=.4, line=dict(width=0)),
            text=[num(v / 1e9, 0) for v in rr["return_amount_irr"]],
            textposition="inside", insidetextanchor="start",
            textfont=dict(size=9.5, color="#ffffff"), cliponaxis=False,
            customdata=rr["return_amount_irr"],
            hovertemplate="%{y}<br>%{customdata:,.0f} ریال<extra></extra>"))
        fig.update_xaxes(range=[ticks[-1], 0])
        fa_axis(fig, "x", ticks, "م‌ریال", 0)
        hbar(fig)
        figure(fig, 244, dict(l=100, r=16, t=10, b=32))

    sec("کالاها", "ده کالای پرفروش بر پایهٔ فروش خالص")
    top = (sf.groupby("product_id", as_index=False)
           .agg(فروش=("net_amount_irr", "sum"), تعداد=("quantity", "sum"),
                اسناد=("sale_id", "count"))
           .merge(dproduct[["product_id", "product_name_fa", "category_name_fa"]], on="product_id")
           .sort_values("فروش", ascending=False).head(10))
    table(pd.DataFrame({
        "کالا": top["product_name_fa"], "دسته": top["category_name_fa"],
        "تعداد": top["تعداد"].map(num), "اسناد": top["اسناد"].map(num),
        "فروش (ریال)": top["فروش"].map(num),
    }), height=400, numeric=["تعداد", "اسناد", "فروش (ریال)"])


# ══════════════════════════════════════════════════════════════════ ۴) استقرار
def page_deploy() -> None:
    head("استقرار",
         "راهنمای اجرا در شبکهٔ داخلی سازمان. هیچ‌یک از این مراحل در این پروژه انجام نشده است.",
         "طرح و چک‌لیست")

    sec("وضعیت اجزا", "چه چیزی ساخته، اجرا یا فقط مستند شده است")
    table(pd.DataFrame([
        ("DDL (schema.sql)", "نوشته و بازبینی منطقی", "روی سرور اجرا نشده"),
        ("ETL (Python)", "اجرا شد", "۳۰۰ از ۳۰۰ تمیز"),
        ("انبار داده", "SQLite محلی", "نه SQL Server"),
        ("RLS منطقه‌ای", "طراحی مستند", "پیاده و تست نشده"),
        ("Report Server", "راهنما", "نصب و لایسنس نشده"),
        ("گزارش .pbix", "—", "وجود ندارد"),
        ("SSL / DNS داخلی", "چک‌لیست", "تست نشده"),
    ], columns=["مؤلفه", "وضعیت در پروژه", "پذیرش"]))

    sec("معماری هدف", "پنج لایه، بدون هیچ مؤلفهٔ ابری")
    layers = [
        ("منابع", "ERP، CRM و سیستم مرجوعی", "extract / CDC"),
        ("Staging", "جدول ورودی خام با شناسهٔ بستهٔ بار", "no transform"),
        ("پاک‌سازی", "SSIS یا Python با همین منطق", "reject · log"),
        ("انبار داده", "ابعاد و فکت‌های استاراسکیما", "FK · index · check"),
        ("ارائه", "Report Server داخلی", "HTTPS · AD auth"),
    ]
    for i, (t, d, m) in enumerate(layers):
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:14px;background:{T["surface"]};'
            f'border:1px solid {T["line"]};border-radius:{T["radius_sm"]};padding:.62rem .9rem;'
            f'margin-bottom:6px">'
            f'<span style="width:20px;height:20px;border-radius:5px;flex:0 0 auto;'
            f'background:{T["sunken"]};color:{T["muted"]};font-size:.68rem;display:flex;'
            f'align-items:center;justify-content:center">{fa(i + 1)}</span>'
            f'<span style="flex:1;min-width:0"><span style="font-size:.83rem;color:{T["ink"]};'
            f'font-weight:500">{t}</span>'
            f'<span style="font-size:.74rem;color:{T["faint"]};margin-inline-start:9px">{d}</span>'
            f'</span>'
            f'<span style="font-size:.7rem;color:{T["muted"]};direction:ltr;white-space:nowrap">'
            f'{m}</span></div>', unsafe_allow_html=True)

    sec("مراحل", "با مسئول هر مرحله")
    table(pd.DataFrame([
        ("۰", "تأیید شرح خدمات، لایسنس SQL Server و Report Server، گروه‌های AD", "کارفرما · IT"),
        ("۱", "ماشین مجازی، نصب SQL Server با کالیشن فارسی، بکاپ", "DBA"),
        ("۲", "بازبینی schema.sql، اجرا در Test، ETL، کنترل کیفیت", "DBA · تیم داده"),
        ("۳", "نصب Report Server، HTTPS، DNS، ساخت .pbix، انتشار", "زیرساخت · BI"),
        ("۴", "RLS و View-as، توازن با مبدأ، تست بار، UAT، آموزش", "BI · مالی"),
    ], columns=["مرحله", "کارها", "مسئول"]), numeric=["مرحله"])
    hint("جزئیات با پیش‌نیاز و ریسک در report/DEPLOYMENT_CHECKLIST.md")

    sec("تصمیم‌ها و هزینه‌شان")
    table(pd.DataFrame([
        ("تقویم شمسی به‌عنوان کلید تاریخ", "الزام گزارش فارسی", "ستون میلادی موازی"),
        ("Import mode", "استقرار ساده و کارایی", "Refresh زمان‌بندی‌شده"),
        ("Reject در DW", "قابل گزارش و پیگیری", "نگهداشت دوره‌ای"),
        ("SQLite برای اثبات منطق", "اجرای واقعی بدون زیرساخت", "بدون Columnstore"),
        ("RLS فقط مستند", "نبود AD و Report Server", "قبل از انتشار الزامی"),
    ], columns=["تصمیم", "دلیل", "هزینه"]))


# ══════════════════════════════════════════════════════════════════ ۵) داده
def page_data() -> None:
    head("دربارهٔ داده",
         "داده نمونه و قابل بازتولید است؛ هیچ دیتاست عمومی یا سازمانی استفاده نشده.",
         "شفافیت")

    sales, returns = csv("fact_sales"), csv("fact_returns")
    stg = csv("stg_sales_raw", keep_na=False)
    kpis([
        ("seed", fa("۱۴۰۳۰۵۰۵"), "بازتولیدپذیر"),
        ("فروش خالص", money(sales["net_amount_irr"].sum()), "ریال"),
        ("مرجوعی", num(len(returns)), "سند"),
        ("staging", num(len(stg)), "ردیف کثیف"),
    ])

    sec("کنترل‌های کیفیت", "همه پس از بار اجرا و بررسی شده‌اند")
    table(pd.DataFrame([
        ("یکتایی sale_id", "بدون تکرار", "گذشت"),
        ("FK فکت به چهار بُعد", "بدون نقض", "گذشت"),
        ("FK مرجوعی به fact_sales", "بدون نقض", "گذشت"),
        ("بازمحاسبهٔ مبلغ خالص", "بدون مغایرت", "گذشت"),
        ("منطقهٔ فکت و مشتری", "هم‌خوان", "گذشت"),
        ("تبدیل چهار فرمت تاریخ", "۳۰۰ از ۳۰۰", "گذشت"),
        ("حذف کامای هزارگان", "۱۰۰٪", "گذشت"),
        ("تخفیف خالی به صفر", "۱۰۰٪", "گذشت"),
    ], columns=["کنترل", "نتیجه", "وضعیت"]))

    sec("محدودیت‌ها", "صادقانه، بدون استثنا")
    table(pd.DataFrame([
        ("زیرساخت", "SQL Server، Report Server، SSL و شبکه نصب و تست نشده"),
        ("schema.sql", "اجرا نشده؛ نیازمند بازبینی DBA"),
        ("SQLite", "جایگزین محلی؛ بدون Columnstore و پارتیشن"),
        ("Reject", "در نمونه صفر ردیف"),
        ("RLS", "فقط مستند، بدون View-as"),
        ("YTD", "وابسته به dim_date و فرض مرز نوروز"),
        ("گزارش", "بدون .pbix و بدون انتشار"),
        ("شرح خدمات", "پیوست کارفرما موجود نبود"),
        ("ROI", "هیچ ادعای صرفه‌جویی نمی‌شود"),
        ("لایسنس", "تأمین نشده"),
    ], columns=["موضوع", "توضیح"]), height=430)

    sec("منبع")
    hint("داده با scripts/generate_all_data.py و seed ثابت تولید می‌شود و با اجرای مجدد عیناً "
         "بازتولید می‌شود. اعداد برای مقیاس سازمانی کالیبره شده‌اند و برآورد بازار نیستند.")


# ------------------------------------------------------------------ اجرا
def main() -> None:
    st.markdown(css(), unsafe_allow_html=True)
    page = sidebar()
    try:
        {"نمای کلی": page_overview, "پایپ‌لاین ETL": page_etl, "تحلیل فروش": page_sales,
         "استقرار": page_deploy, "دربارهٔ داده": page_data}[page]()
    except Exception as exc:
        note(f"خطا در نمایش این صفحه: {fa(exc)}")
        with st.expander("جزئیات فنی"):
            st.exception(exc)

    st.markdown(f'<hr>', unsafe_allow_html=True)
    hint("پروژهٔ ۵ — دادهٔ نمونه (seed ۱۴۰۳۰۵۰۵) · SQLite جایگزین محلی · "
         "بدون ادعای نصب یا انتشار سازمانی")


if __name__ == "__main__":
    main()

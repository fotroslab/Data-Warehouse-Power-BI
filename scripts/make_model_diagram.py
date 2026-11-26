#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_model_diagram.py — تولید assets/model_diagram.svg + model_diagram.html
===========================================================================
دو خروجی، با همان ابعاد و همان توکن‌های طراحی اپ:

  * model_diagram.html  → **درون‌خطی** در اپ استفاده می‌شود؛ چون درون DOM است،
    فونت Vazirmatn و اندازه‌ها دقیقاً مثل بقیهٔ صفحه است (SVG به‌صورت <img>
    فونت صفحه را ارث نمی‌برد و همین باعث «فونت متفاوت» می‌شد).
  * model_diagram.svg   → برای README و استفادهٔ مستقل.

قواعد فنی (آزموده‌شده):
  * هرگز direction="rtl" روی ریشه نگذارید (با text-anchor="end" متن از کادر بیرون می‌زند).
  * ستون‌های فنی: direction:ltr + text-anchor:start از لبهٔ چپ.
  * ستون‌های فارسی: direction:rtl + text-anchor:start از لبهٔ راست.

    python3 scripts/make_model_diagram.py
"""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS = BASE_DIR / "assets"

W, H = 1000, 470

# ---------------------------------------------- توکن‌های طراحی (هم‌نام با app.py)
C = dict(
    ink="#18202b", ink2="#46525f", muted="#78838f", faint="#9aa4af",
    line="#e3e7ec", hair="#eef1f4", surface="#ffffff",
    tint="#f8f9fb", accent="#9c4a3c", accent_line="#dfc6c0",
    edge="#c8d0d9",
)

BOX = [
    dict(id="dim_date", x=372, y=18, w=256, h=162, kind="dim",
         title="dim_date", fa="تقویم شمسی", rows=[
             ("date_key (PK)", "YYYYMMDD", "pk"),
             ("jalali_date_key", "شمسی", ""),
             ("gregorian_date", "DATE", ""),
             ("year · month · day", "", ""),
             ("quarter · season_fa", "", ""),
             ("day_of_week · weekday_fa", "", ""),
             ("is_weekend · fiscal_period", "", ""),
         ]),
    dict(id="dim_region", x=24, y=18, w=232, h=116, kind="dim",
         title="dim_region", fa="منطقه", rows=[
             ("region_id (PK)", "R01..R12", "pk"),
             ("region_name_fa", "", ""),
             ("region_code_fa · zone_fa", "", ""),
             ("", "", ""),
         ]),
    dict(id="dim_customer", x=24, y=170, w=232, h=140, kind="dim",
         title="dim_customer", fa="مشتری", rows=[
             ("customer_id (PK)", "", "pk"),
             ("customer_name_fa", "", ""),
             ("segment_fa · channel_fa", "", ""),
             ("region_id (FK)", "→ dim_region", "fk"),
             ("created_date · is_active", "", ""),
         ]),
    dict(id="dim_product", x=744, y=170, w=232, h=124, kind="dim",
         title="dim_product", fa="کالا", rows=[
             ("product_id (PK)", "", "pk"),
             ("product_name_fa", "", ""),
             ("category_id · category_name_fa", "", ""),
             ("unit_price_irr · unit_cost_irr", "", ""),
         ]),
    dict(id="fact_sales", x=356, y=196, w=288, h=172, kind="fact",
         title="fact_sales", fa="فروش · ۳۰ هزار", rows=[
             ("sale_id (PK)", "", "pk"),
             ("date_key · customer_id", "FK", "fk"),
             ("product_id · region_id", "FK", "fk"),
             ("channel_fa · quantity", "", ""),
             ("unit_price_irr · unit_cost_irr", "", ""),
             ("discount_pct · gross_amount_irr", "", ""),
             ("net_amount_irr · cost_amount_irr", "", ""),
         ]),
    dict(id="fact_returns", x=744, y=314, w=232, h=140, kind="fact",
         title="fact_returns", fa="مرجوعی · ۲ هزار", rows=[
             ("return_id (PK)", "", "pk"),
             ("sale_id (FK)", "→ fact_sales", "fk"),
             ("date_key · customer_id", "FK", "fk"),
             ("quantity_returned", "", ""),
             ("return_amount_irr · reason_fa", "", ""),
         ]),
    dict(id="etl_reject", x=24, y=326, w=232, h=128, kind="reject",
         title="etl_reject", fa="پایش کیفیت", rows=[
             ("reject_stage · reject_reason", "", ""),
             ("source_row_id · raw_payload", "", ""),
             ("load_batch_id · rejected_at", "", ""),
             ("در نمونه: صفر ردیف", "", "warn"),
         ]),
]

EDGES = [
    (500, 168, 500, 196, "1 : N", 508, 186),
    (140, 122, 140, 170, "1 : N", 148, 148),
    (256, 234, 356, 262, "1 : N", 262, 252),
    (744, 226, 644, 262, "N : 1", 656, 252),
    (644, 320, 744, 352, "1 : N", 656, 342),
]

ROW_H = 17.5
PAD = 12


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg() -> str:
    """SVG مستقل (برای README) — فونت به Vazirmatn ارجاع می‌دهد."""
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        'font-family="Vazirmatn FD, Vazirmatn, Tahoma, sans-serif">',
        "<defs>",
        '  <marker id="a" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" '
        'orient="auto-start-reverse"><path d="M0,1 L7,4 L0,7 z" fill="' + C["edge"] + '"/></marker>',
        "</defs>",
        f'<rect width="{W}" height="{H}" fill="{C["surface"]}"/>',
    ]
    for b in BOX:
        x, y, w = b["x"], b["y"], b["w"]
        h = 38 + 14 + len(b["rows"]) * ROW_H + 9   # ارتفاع = سربرگ دوخطی + سطرها + پدینگ
        fill = C["tint"] if b["kind"] == "fact" else (C["surface"] if b["kind"] == "dim" else "#fdfbf8")
        stroke = C["accent_line"] if b["kind"] == "fact" else (C["line"] if b["kind"] == "dim" else "#e8ddc9")
        tcol = C["accent"] if b["kind"] == "fact" else C["ink"]
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="1"/>')
        o.append(f'<text x="{x + w - PAD}" y="{y + 17}" text-anchor="start" direction="rtl" '
                 f'font-size="11.5" font-weight="600" fill="{tcol}">{_esc(b["title"])}</text>')
        # زیرنویس فارسی: راست‌چین در خط دوم، از لبهٔ راست به داخل (بدون سرریز)
        o.append(f'<text x="{x + w - PAD}" y="{y + 31}" text-anchor="start" direction="rtl" '
                 f'font-size="9.5" fill="{C["faint"]}">{_esc(b["fa"])}</text>')
        o.append(f'<line x1="{x + 1}" y1="{y + 38}" x2="{x + w - 1}" y2="{y + 38}" '
                 f'stroke="{C["hair"]}" stroke-width="1"/>')
        ty = y + 38 + 14
        for name, val, kind in b["rows"]:
            if name:
                col = C["accent"] if kind == "fk" else (C["ink"] if kind == "pk" else
                                                        ("#8a6a3a" if kind == "warn" else C["ink2"]))
                wt = "600" if kind in ("pk", "fk") else "400"
                o.append(f'<text x="{x + w - PAD}" y="{ty}" text-anchor="start" direction="rtl" '
                         f'font-size="10" font-weight="{wt}" fill="{col}">{_esc(name)}</text>')
            if val:
                o.append(f'<text x="{x + PAD}" y="{ty}" text-anchor="start" '
                         f'font-size="9" fill="{C["faint"]}">{_esc(val)}</text>')
            ty += ROW_H
    for x1, y1, x2, y2, lab, lx, ly in EDGES:
        o.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{C["edge"]}" '
                 f'stroke-width="1.1" marker-end="url(#a)"/>')
        o.append(f'<text x="{lx}" y="{ly}" font-size="8.5" fill="{C["faint"]}" '
                 f'letter-spacing=".3">{lab}</text>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


def build_html() -> str:
    """نسخهٔ درون‌خطی: همان SVG بدون تگ <svg> بیرونی، برای درج در HTML اپ."""
    body = build_svg()
    body = body.replace('<rect width="1000" height="470" fill="#ffffff"/>', "")
    return body


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "model_diagram.svg").write_text(build_svg(), encoding="utf-8")
    (ASSETS / "model_diagram.html").write_text(build_html(), encoding="utf-8")
    print("✔ assets/model_diagram.svg")
    print("✔ assets/model_diagram.html")


if __name__ == "__main__":
    main()

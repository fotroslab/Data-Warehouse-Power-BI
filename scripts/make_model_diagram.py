#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_model_diagram.py — تولید assets/model_diagram.svg (نمودار مدل ستاره‌ای)
==============================================================================
نکتهٔ فنی مهم (آزموده‌شده): هرگز direction="rtl" را روی ریشهٔ <svg> نگذارید؛ با
text-anchor="end" باعث سرریز متن به بیرون کادر می‌شود. راه‌حل: روی هر <text> جداگانه
direction="rtl" + text-anchor="start" با x = لبهٔ راست کادر.

    python3 scripts/make_model_diagram.py
"""
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "assets" / "model_diagram.svg"

INK = "#232b36"
ACCENT = "#d64541"
MUTED = "#5b6674"
BORDER = "#c9d1db"
BG = "#f6f7f8"
HDR_H = 34
PAD = 14
LH = 21          # فاصلهٔ خطوط
FONT = "Vazirmatn, Vazirmatn FD, Tahoma, sans-serif"

BOXES = [
    # key, x, y, w, h, kind, title, lines[(text, cls)]
    dict(key="dim_date", x=450, y=76, w=300, h=236, kind="dim",
         title="dim_date — تقویم شمسی", lines=[
             ("date_key  (PK)  YYYYMMDD شمسی", "pk"),
             ("jalali_date · jalali_date_key", "col"),
             ("gregorian_date  (DATE)", "col"),
             ("year · month · month_name_fa · day", "col"),
             ("quarter · season_fa", "col"),
             ("day_of_week · weekday_fa", "col"),
             ("is_weekend · is_month_start", "col"),
             ("fiscal_year · fiscal_period", "col"),
         ]),
    dict(key="dim_region", x=56, y=76, w=268, h=170, kind="dim",
         title="dim_region — منطقه", lines=[
             ("region_id  (PK)  R01..R12", "pk"),
             ("region_name_fa", "col"),
             ("region_code_fa", "col"),
             ("zone_fa", "col"),
         ]),
    dict(key="dim_customer", x=56, y=320, w=268, h=194, kind="dim",
         title="dim_customer — مشتری", lines=[
             ("customer_id  (PK)", "pk"),
             ("customer_name_fa", "col"),
             ("segment_fa  (حقیقی/حقوقی)", "col"),
             ("channel_fa", "col"),
             ("region_id  (FK → dim_region)", "fk"),
             ("created_date · is_active", "col"),
         ]),
    dict(key="dim_product", x=876, y=320, w=268, h=172, kind="dim",
         title="dim_product — کالا", lines=[
             ("product_id  (PK)", "pk"),
             ("product_name_fa", "col"),
             ("category_id · category_name_fa", "col"),
             ("unit_price_irr", "col"),
             ("unit_cost_irr · is_active", "col"),
         ]),
    dict(key="fact_sales", x=426, y=392, w=348, h=236, kind="fact",
         title="fact_sales — فروش (۳۰ هزار سند)", lines=[
             ("sale_id  (PK)", "pk"),
             ("date_key (FK) · customer_id (FK)", "fk"),
             ("product_id (FK) · region_id (FK)", "fk"),
             ("channel_fa · quantity", "col"),
             ("unit_price_irr · unit_cost_irr", "col"),
             ("discount_pct", "col"),
             ("gross_amount_irr", "col"),
             ("net_amount_irr · cost_amount_irr", "col"),
         ]),
    dict(key="fact_returns", x="same", y=576, w=268, h=172, kind="fact",
         title="fact_returns — مرجوعی (۲ هزار سند)", lines=[
             ("return_id  (PK)", "pk"),
             ("sale_id  (FK → fact_sales)", "fk"),
             ("date_key · customer_id", "fk"),
             ("product_id · region_id", "fk"),
             ("quantity_returned", "col"),
             ("return_amount_irr · reason_fa", "col"),
         ]),
    dict(key="etl_reject", x=56, y=576, w=268, h=172, kind="reject",
         title="etl_reject — پایش کیفیت", lines=[
             ("reject_id (PK) · source_row_id", "col"),
             ("reject_stage · reject_reason", "col"),
             ("raw_payload  (JSON)", "col"),
             ("load_batch_id · rejected_at", "col"),
             ("در نمونهٔ فعلی: بدون ردیف", "note"),
         ]),
]

EDGES = [
    # x1,y1 → x2,y2 , label , label_x , label_y
    (600, 312, 600, 392, "1 : N", 612, 358),
    (190, 246, 190, 320, "1 : N", 202, 288),
    (324, 402, 426, 452, "1 : N", 330, 416),
    (876, 402, 774, 452, "N : 1", 792, 416),
    (774, 582, 876, 618, "1 : N", 792, 590),
]

STYLE = f"""
  .box {{ fill:#ffffff; stroke:{BORDER}; stroke-width:1.5; }}
  .box-fact {{ fill:#fdf3f3; stroke:{ACCENT}; stroke-width:2; }}
  .box-reject {{ fill:#fff8f1; stroke:#d9a86a; stroke-width:1.5; }}
  .hdr {{ fill:{INK}; }}
  .hdr-fact {{ fill:{ACCENT}; }}
  .hdr-reject {{ fill:#8a5a24; }}
  .t {{ font-family:{FONT}; font-size:15px; font-weight:700; fill:#f6f7f8; direction:rtl; }}
  .t-fact {{ font-family:{FONT}; font-size:15px; font-weight:700; fill:#ffffff; direction:rtl; }}
  .pk {{ font-family:{FONT}; font-size:12.5px; font-weight:700; fill:{INK}; direction:rtl; }}
  .col {{ font-family:{FONT}; font-size:12.5px; fill:#3a4553; direction:rtl; }}
  .fk {{ font-family:{FONT}; font-size:12.5px; fill:#a3352f; direction:rtl; }}
  .note {{ font-family:{FONT}; font-size:12px; fill:#8a5a24; direction:rtl; }}
  .edge {{ stroke:#8a94a3; stroke-width:1.6; fill:none; marker-end:url(#arrow); }}
  .elabel {{ font-family:{FONT}; font-size:12px; fill:{MUTED}; direction:ltr; }}
  .title {{ font-family:{FONT}; font-size:23px; font-weight:800; fill:{INK}; direction:rtl; }}
  .sub {{ font-family:{FONT}; font-size:12.5px; fill:#6b7480; direction:rtl; }}
  .foot {{ font-family:{FONT}; font-size:11.5px; fill:#7b8490; direction:rtl; }}
"""


def build() -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 790" width="1200" height="790">',
        "<defs>",
        '  <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">',
        '    <path d="M0,0 L10,5 L0,10 z" fill="#8a94a3"/>',
        "  </marker>",
        f"  <style>{STYLE}</style>",
        "</defs>",
        f'<rect width="1200" height="790" fill="{BG}"/>',
        '<text class="title" x="1150" y="42" text-anchor="start">مدل استاراسکیما — انبار دادهٔ پروژهٔ ۵</text>',
        '<text class="sub" x="1150" y="66" text-anchor="start">SQL Server · تقویم شمسی · واحد ریال · '
        'دادهٔ نمونه (seed=۱۴۰۳۰۵۰۵ · نمونه)</text>',
    ]

    for b in BOXES:
        x = b["x"]
        if x == "same":
            x = 876
        y, w, h = b["y"], b["w"], b["h"]
        kind = b["kind"]
        rect_cls = {"dim": "box", "fact": "box-fact", "reject": "box-reject"}[kind]
        hdr_cls = {"dim": "hdr", "fact": "hdr-fact", "reject": "hdr-reject"}[kind]
        t_cls = "t-fact" if kind == "fact" else "t"
        parts.append(f'<g id="{b["key"]}">')
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" class="{rect_cls}"/>')
        # هدر با گوشه‌های بالایی گرد
        parts.append(
            f'<path d="M{x},{y + 8} a8,8 0 0 1 8,-8 h{w - 16} a8,8 0 0 1 8,8 v{HDR_H - 8} h{-w} z" '
            f'class="{hdr_cls}"/>')
        parts.append(f'<text class="{t_cls}" x="{x + w - 14}" y="{y + 23}" text-anchor="start">'
                     f'{b["title"]}</text>')
        ty = y + HDR_H + LH
        for text, cls in b["lines"]:
            parts.append(f'<text class="{cls}" x="{x + w - PAD}" y="{ty}" text-anchor="start">'
                         f'{text}</text>')
            ty += LH
        parts.append("</g>")

    for x1, y1, x2, y2, label, lx, ly in EDGES:
        parts.append(f'<path d="M{x1},{y1} L{x2},{y2}" class="edge"/>')
        parts.append(f'<text class="elabel" x="{lx}" y="{ly}" text-anchor="start">{label}</text>')

    parts.append('<text class="foot" x="1150" y="762" text-anchor="start">staging → پاک‌سازی → ابعاد و '
                 'فکت‌ها · جریان Reject مستند و کدِ آماده دارد (در نمونه ۰ ردیف) · '
                 'RLS منطقه‌ای فقط مستند است</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"✔ {OUT.relative_to(BASE_DIR)} نوشته شد")


if __name__ == "__main__":
    main()

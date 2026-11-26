#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
etl_staging_to_dw.py — ETL نمونه: stg_sales_raw.csv → انبار دادهٔ دمو
=====================================================================
این اسکریپت **واقعاً اجرا می‌شود** و خروجی می‌سازد. اما دقت شود:

    ⚠️  خروجی SQLite (model/dw_demo.sqlite) جایگزین محلی برای اثبات منطق ETL است،
        نه SQL Server. منطق پاک‌سازی همان است که در model/schema.sql و در
        (SSIS/Stored Procedure روی SQL Server) پیاده می‌شود. هیچ ادعایی دربارهٔ اجرا
        روی SQL Server واقعی وجود ندارد.

مسیر کار:
    1) خواندن stg_sales_raw.csv  (۳۰۰ ردیف عمداً کثیف)
    2) نرمال‌سازی: تاریخ‌های مختلط (شمسی 1403/.. | میلادی YYYY/MM/DD | DD-MM-YYYY |
       YYYY-MM-DD) → date_key شمسی ؛ حذف کامای هزارگان ؛ TRIM ؛ تخفیف خالی → ۰
    3) هر ردیف نامعتبر → dw.etl_reject (در نمونه: ۰ ردیف)
    4) بار ابعاد از data/dim_*.csv و فکت‌ها از data/fact_*.csv
    5) کنترل جمع: Σ net_amount_irr و شمارش هر جدول

اجرا (از ریشهٔ مخزن):
    python3 model/etl_staging_to_dw.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import uuid
from pathlib import Path

import jdatetime
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "model" / "dw_demo.sqlite"
JALALI_YEAR = 1403

# ------------------------------------------------------------------ کمکی‌ها
THOUSANDS_RE = re.compile(r"[,\u066c\u060c\s]")


def fa_num(n) -> str:
    """قالب فارسی اعداد برای لاگ."""
    try:
        return f"{int(n):,}".replace(",", "٬")
    except (TypeError, ValueError):
        return str(n)


def parse_sale_date(raw: str) -> tuple[int, str]:
    """
    تبدیل هر یک از فرمت‌های ورودی به (date_key شمسی YYYYMMDD, jalali_date متنی).
    فرمت‌های پشتیبانی‌شده:
        1403/12/12   → شمسی
        2024/07/17   → میلادی
        28-07-2024   → میلادی
        2024-07-28   → میلادی
    در صورت عدم امکان تبدیل → ValueError (ردیف به Reject می‌رود)
    """
    s = str(raw).strip()
    if not s:
        raise ValueError("تاریخ خالی")
    s = s.replace("\\", "/").replace(".", "/")

    jd: jdatetime.date | None = None
    # 1) DD-MM-YYYY  یا  DD/MM/YYYY با سال میلادی چهاررقمی در انتها
    m = re.fullmatch(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        jd = jdatetime.date.fromgregorian(date=__import__("datetime").date(y, mo, d))
    else:
        # 2) YYYY/MM/DD — سال شمسی (13xx/14xx) یا میلادی (19xx/20xx)
        m = re.fullmatch(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
        if m:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1300 <= y <= 1500:                     # شمسی
                jd = jdatetime.date(y, mo, d)
            elif 1900 <= y <= 2100:                   # میلادی
                jd = jdatetime.date.fromgregorian(date=__import__("datetime").date(y, mo, d))
            else:
                raise ValueError(f"سال خارج از محدوده: {y}")
        else:
            # 3) YYYYMMDD خالص
            m = re.fullmatch(r"(\d{8})", s)
            if m:
                v = m.group(1)
                y, mo, d = int(v[:4]), int(v[4:6]), int(v[6:])
                if 1300 <= y <= 1500:
                    jd = jdatetime.date(y, mo, d)
                else:
                    jd = jdatetime.date.fromgregorian(date=__import__("datetime").date(y, mo, d))
    if jd is None:
        raise ValueError(f"فرمت تاریخ ناشناخته: {raw!r}")
    return int(jd.strftime("%Y%m%d")), jd.strftime("%Y/%m/%d")


def parse_amount(raw, default=None):
    """حذف کامای هزارگان/فاصله و تبدیل به عدد؛ خالی → default."""
    if raw is None:
        return default
    s = str(raw).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return default
    s = THOUSANDS_RE.sub("", s)
    try:
        return int(round(float(s)))
    except ValueError as exc:
        raise ValueError(f"مبلغ نامعتبر: {raw!r}") from exc


def parse_discount(raw) -> float:
    """تخفیف: خالی → ۰ ؛ پشتیبانی از «۵٪»/«5%» و 0.05 و 5 (درصد)."""
    if raw is None:
        return 0.0
    s = str(raw).strip().replace("٪", "").replace("%", "")
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return 0.0
    try:
        v = float(s)
    except ValueError as exc:
        raise ValueError(f"تخفیف نامعتبر: {raw!r}") from exc
    if v > 1:            # اگر درصد (%) وارد شده باشد
        v = v / 100.0
    if not (0 <= v <= 1):
        raise ValueError(f"تخفیف خارج از بازه: {raw!r}")
    return round(v, 2)


# ------------------------------------------------------------------ DDL معادل
SQLITE_DDL = """
CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY, jalali_date TEXT UNIQUE NOT NULL,
    jalali_date_key INTEGER NOT NULL, gregorian_date TEXT UNIQUE NOT NULL,
    year INTEGER, month INTEGER, month_name_fa TEXT, day INTEGER,
    quarter INTEGER, season_fa TEXT, day_of_week INTEGER, weekday_fa TEXT,
    is_weekend INTEGER, is_month_start INTEGER, fiscal_year INTEGER, fiscal_period TEXT
);
CREATE TABLE IF NOT EXISTS dim_region (
    region_id TEXT PRIMARY KEY, region_name_fa TEXT UNIQUE NOT NULL,
    region_code_fa TEXT, zone_fa TEXT
);
CREATE TABLE IF NOT EXISTS dim_customer (
    customer_id TEXT PRIMARY KEY, customer_name_fa TEXT NOT NULL,
    segment_fa TEXT, channel_fa TEXT, region_id TEXT REFERENCES dim_region(region_id),
    created_date TEXT, is_active INTEGER
);
CREATE TABLE IF NOT EXISTS dim_product (
    product_id TEXT PRIMARY KEY, product_name_fa TEXT NOT NULL,
    category_id TEXT, category_name_fa TEXT,
    unit_price_irr INTEGER, unit_cost_irr INTEGER, is_active INTEGER
);
CREATE TABLE IF NOT EXISTS fact_sales (
    sale_id TEXT PRIMARY KEY, date_key INTEGER REFERENCES dim_date(date_key),
    customer_id TEXT REFERENCES dim_customer(customer_id),
    product_id TEXT REFERENCES dim_product(product_id),
    region_id TEXT REFERENCES dim_region(region_id),
    channel_fa TEXT, quantity INTEGER, unit_price_irr INTEGER, unit_cost_irr INTEGER,
    discount_pct REAL, gross_amount_irr INTEGER, net_amount_irr INTEGER, cost_amount_irr INTEGER
);
CREATE TABLE IF NOT EXISTS fact_returns (
    return_id TEXT PRIMARY KEY, sale_id TEXT REFERENCES fact_sales(sale_id),
    date_key INTEGER REFERENCES dim_date(date_key),
    customer_id TEXT REFERENCES dim_customer(customer_id),
    product_id TEXT REFERENCES dim_product(product_id),
    region_id TEXT REFERENCES dim_region(region_id),
    quantity_returned INTEGER, return_amount_irr INTEGER, reason_fa TEXT
);
CREATE TABLE IF NOT EXISTS etl_reject (
    reject_id INTEGER PRIMARY KEY AUTOINCREMENT, source_table TEXT, source_row_id INTEGER,
    reject_stage TEXT, reject_reason TEXT, raw_payload TEXT,
    load_batch_id TEXT, rejected_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS etl_load_log (
    load_id INTEGER PRIMARY KEY AUTOINCREMENT, load_batch_id TEXT, stage_name TEXT,
    rows_read INTEGER, rows_clean INTEGER, rows_reject INTEGER,
    started_at TEXT, finished_at TEXT, status TEXT, message TEXT
);
CREATE TABLE IF NOT EXISTS stg_sales_cleaned (
    row_id INTEGER PRIMARY KEY, sale_ref TEXT, date_key INTEGER, jalali_date TEXT,
    customer_name_fa TEXT, product_name_fa TEXT, region_id TEXT,
    quantity INTEGER, unit_price_irr INTEGER, discount_pct REAL, source_date_raw TEXT
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON;")
    con.executescript(SQLITE_DDL)
    return con


def log(con, batch, stage, read, clean, reject, status, message, started):
    con.execute(
        """INSERT INTO etl_load_log (load_batch_id, stage_name, rows_read, rows_clean,
                                     rows_reject, started_at, finished_at, status, message)
           VALUES (?,?,?,?,?,?,datetime('now'),?,?)""",
        (batch, stage, read, clean, reject, started, status, message),
    )


# ------------------------------------------------------------------ مراحل
def load_dimensions(con: sqlite3.Connection) -> dict[str, int]:
    dims = {}
    for name in ["dim_date", "dim_region", "dim_product", "dim_customer"]:
        df = pd.read_csv(DATA_DIR / f"{name}.csv", encoding="utf-8-sig")
        df.to_sql(name, con, if_exists="replace", index=False)
        dims[name] = len(df)
    return dims


def load_facts(con: sqlite3.Connection) -> dict[str, int]:
    facts = {}
    for name in ["fact_sales", "fact_returns"]:
        df = pd.read_csv(DATA_DIR / f"{name}.csv", encoding="utf-8-sig")
        df.to_sql(name, con, if_exists="replace", index=False)
        facts[name] = len(df)
    return facts


def transform_staging(con: sqlite3.Connection, batch: str) -> tuple[int, int, list[dict]]:
    """پاک‌سازی ۳۰۰ ردیف خام؛ برمی‌گرداند (خوانده، تمیز، لیست Reject)."""
    stg = pd.read_csv(DATA_DIR / "stg_sales_raw.csv", encoding="utf-8-sig", dtype=str).fillna("")
    rows_read = len(stg)
    clean, rejects = [], []

    valid_regions = {r[0] for r in con.execute("SELECT region_id FROM dim_region")}
    valid_dates = {r[0] for r in con.execute("SELECT date_key FROM dim_date")}

    for _, r in stg.iterrows():
        row_id = int(r["row_id"])
        payload = json.dumps(r.to_dict(), ensure_ascii=False)
        stage, reason = None, None
        try:
            date_key, jalali = parse_sale_date(r["sale_date_raw"])
            stage = "DATE_PARSE"
            if date_key not in valid_dates:
                raise ValueError(f"تاریخ {jalali} خارج از بازهٔ تقویم DW")

            stage = "NUMERIC_PARSE"
            qty = parse_amount(r["quantity_raw"])
            if qty is None or qty <= 0:
                raise ValueError("تعداد نامعتبر یا صفر")
            price = parse_amount(r["unit_price_raw"])
            if price is None or price <= 0:
                raise ValueError("مبلغ نامعتبر یا صفر")
            disc = parse_discount(r["discount_raw"])

            stage = "DIM_LOOKUP"
            region = str(r["region_id_raw"]).strip()
            if region not in valid_regions:
                raise ValueError(f"منطقهٔ ناشناخته: {region!r}")

            clean.append({
                "row_id": row_id,
                "sale_ref": str(r["sale_ref"]).strip(),
                "date_key": date_key,
                "jalali_date": jalali,
                "customer_name_fa": str(r["customer_name_raw"]).strip(),
                "product_name_fa": str(r["product_name_raw"]).strip(),
                "region_id": region,
                "quantity": qty,
                "unit_price_irr": price,
                "discount_pct": disc,
                "source_date_raw": str(r["sale_date_raw"]),
            })
        except ValueError as exc:
            rejects.append({
                "source_row_id": row_id,
                "reject_stage": stage or "READ",
                "reject_reason": str(exc),
                "raw_payload": payload,
            })

    con.execute("DELETE FROM stg_sales_cleaned")
    if clean:
        pd.DataFrame(clean).to_sql("stg_sales_cleaned", con, if_exists="append", index=False)
    if rejects:
        pd.DataFrame(rejects).to_sql("etl_reject", con, if_exists="append", index=False)
    return rows_read, len(clean), rejects


def quality_controls(con: sqlite3.Connection) -> dict:
    """کنترل‌های کیفیت پس از بار."""
    q = lambda sql: con.execute(sql).fetchone()[0]
    return {
        "fact_sales_rows": q("SELECT COUNT(*) FROM fact_sales"),
        "fact_returns_rows": q("SELECT COUNT(*) FROM fact_returns"),
        "sum_net_amount_irr": q("SELECT COALESCE(SUM(net_amount_irr),0) FROM fact_sales"),
        "sum_return_amount_irr": q("SELECT COALESCE(SUM(return_amount_irr),0) FROM fact_returns"),
        "distinct_regions": q("SELECT COUNT(DISTINCT region_id) FROM fact_sales"),
        "orphan_sales_customer": q("""SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_customer c ON c.customer_id=f.customer_id WHERE c.customer_id IS NULL"""),
        "orphan_sales_product": q("""SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_product p ON p.product_id=f.product_id WHERE p.product_id IS NULL"""),
        "orphan_sales_date": q("""SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_date d ON d.date_key=f.date_key WHERE d.date_key IS NULL"""),
        "orphan_returns_sale": q("""SELECT COUNT(*) FROM fact_returns r
            LEFT JOIN fact_sales s ON s.sale_id=r.sale_id WHERE s.sale_id IS NULL"""),
        "net_mismatch": q("""SELECT COUNT(*) FROM fact_sales
            WHERE net_amount_irr <> CAST(ROUND(gross_amount_irr * (1 - discount_pct)) AS INTEGER)"""),
        "reject_rows": q("SELECT COUNT(*) FROM etl_reject"),
    }


def main() -> int:
    from datetime import datetime, timezone
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    batch = str(uuid.uuid4())
    print("=" * 68)
    print("ETL: stg_sales_raw.csv  →  dw_demo.sqlite   (جایگزین محلیِ SQL Server)")
    print("batch:", batch)
    print("=" * 68)

    con = connect()
    con.execute("DELETE FROM etl_reject")

    dims = load_dimensions(con)
    print(f"[1/4] ابعاد بارگذاری شد → " + " | ".join(f"{k}={fa_num(v)}" for k, v in dims.items()))
    con.commit()

    facts = load_facts(con)
    print(f"[2/4] فکت‌ها بارگذاری شد → " + " | ".join(f"{k}={fa_num(v)}" for k, v in facts.items()))
    con.commit()

    n_read, n_clean, rejects = transform_staging(con, batch)
    con.commit()
    print(f"[3/4] پاک‌سازی staging → خوانده: {fa_num(n_read)} | تمیز: {fa_num(n_clean)} | "
          f"Reject: {fa_num(len(rejects))}")
    if rejects:
        for r in rejects[:5]:
            print(f"      - ردیف {r['source_row_id']} [{r['reject_stage']}] {r['reject_reason']}")

    ctl = quality_controls(con)
    print("[4/4] کنترل‌های کیفیت:")
    for k, v in ctl.items():
        print(f"      {k:26s} = {fa_num(v)}")
    print(f"      sum(net_amount_irr)        = {fa_num(ctl['sum_net_amount_irr'])} ریال")

    ok = all(ctl[k] == 0 for k in
             ["orphan_sales_customer", "orphan_sales_product", "orphan_sales_date",
              "orphan_returns_sale", "net_mismatch"])
    status = "SUCCESS" if ok else "PARTIAL"
    log(con, batch, "stg.sales_raw → dw", n_read, n_clean, len(rejects), status,
        f"dims={dims} facts={facts} controls_ok={ok}", started)
    con.commit()

    print("-" * 68)
    print(f"وضعیت: {status}  |  DB: {DB_PATH.relative_to(BASE_DIR)}")
    print("توجه: SQLite فقط جایگزین محلی برای اثبات منطق است؛ SQL Server واقعی اجرا نشده.")
    print("=" * 68)

    con.close()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

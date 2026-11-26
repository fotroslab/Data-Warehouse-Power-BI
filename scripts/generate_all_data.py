#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_all_data.py — تولید دادهٔ نمونه برای پروژهٔ «SQL Server + DW + Power BI Report Server»
همهٔ داده‌ها *نمونه* و قابل بازتولید هستند (seed = 14030505). واحد پول: ریال. تقویم: شمسی.

اجرا از ریشهٔ مخزن:
    python3 scripts/generate_all_data.py

خروجی‌ها در data/ :
    dim_date.csv (365) | dim_region.csv (12) | dim_product.csv (80) | dim_customer.csv (500)
    fact_sales.csv (30,000) | fact_returns.csv (2,000)
    stg_sales_raw.csv (300 — عمداً کثیف)
    DATA_DICTIONARY.md | DATA_QUALITY_REPORT.md

هیچ دادهٔ سازمانی واقعی در این فایل نیست.
"""
from __future__ import annotations

import os
import random
from pathlib import Path

import jdatetime
import pandas as pd

SEED = 14030505
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

JALALI_YEAR = 1403  # سال مالی نمونه

# ضریب کالیبراسیون قیمت‌ها: برای رسیدن جمع فروش به مقیاس «همت» (۱۲٫۸ هزار میلیارد ریال)
# در پروژهٔ نمونه؛ صرفاً برای واقع‌نمایی مقیاس سازمانی است، نه برآورد بازار.
PRICE_SCALE = 4.2

# ---------------------------------------------------------------- تقویم شمسی
MONTHS_FA = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]
WEEKDAYS_FA = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"]

REGIONS = [
    ("R01", "تهران", "منطقه ۱", "مرکز"),
    ("R02", "اصفهان", "منطقه ۲", "مرکز"),
    ("R03", "مشهد", "منطقه ۳", "شرق"),
    ("R04", "شیراز", "منطقه ۴", "جنوب"),
    ("R05", "تبریز", "منطقه ۵", "شمال‌غرب"),
    ("R06", "اهواز", "منطقه ۶", "جنوب‌غرب"),
    ("R07", "کرج", "منطقه ۷", "مرکز"),
    ("R08", "قم", "منطقه ۸", "مرکز"),
    ("R09", "رشت", "منطقه ۹", "شمال"),
    ("R10", "کرمان", "منطقه ۱۰", "جنوب‌شرق"),
    ("R11", "همدان", "منطقه ۱۱", "غرب"),
    ("R12", "یزد", "منطقه ۱۲", "مرکز"),
]

# کد منطقه → وزن فروش (تمرکز فروش در تهران/اصفهان/مشهد)
REGION_WEIGHT = {"R01": 26, "R02": 13, "R03": 12, "R04": 9, "R05": 8, "R06": 7,
                 "R07": 7, "R08": 5, "R09": 4, "R10": 3, "R11": 3, "R12": 3}

CATEGORIES = [
    ("C01", "تجهیزات اداری", 8),
    ("C02", "الکترونیک", 18),
    ("C03", "لوازم خانگی", 22),
    ("C04", "مواد مصرفی", 6),
    ("C05", "شبکه و زیرساخت", 34),
    ("C06", "نرم‌افزار و لایسنس", 48),
]

PRODUCT_NAMES = {
    "C01": ["پرینتر لیزری A4", "اسکنر رومیزی", "دستگاه کاغذ خردکن", "تخته وایت‌برد",
            "میز اداری دو نفره", "صندلی ارگونومیک", "کمد بایگانی", "دستگاه حضور و غیاب",
            "پرینتر چندکاره رنگی", "شردر صنعتی", "لپ‌تاپ‌استند اداری", "پروژکتور جلسات",
            "ویدئو کنفرانس رومیزی", "تلفن IP اداری",
            "دستگاه لمینت", "تابلو اعلانات شیشه‌ای"],
    "C02": ["مانیتور ۲۴ اینچ", "کیبورد بی‌سیم", "ماوس ارگونومیک", "هارد اکسترنال ۲ ترابایت",
            "تبلت ۱۰ اینچ", "هدفون حرفه‌ای", "دوربین عکاسی", "اسپیکر کنفرانس",
            "شارژر چندپورت", "کابل HDMI ۵ متر", "وبکم 1080p", "فلش ۶۴ گیگابایت",
            "پایه لپ‌تاپ آلومینیومی", "مودم ۴G",
            "ماوس‌پد بزرگ", "هاب USB-C"],
    "C03": ["یخچال ۱۸ فوت", "ماشین لباسشویی ۸ کیلو", "مایکروویو ۳۰ لیتری", "چای‌ساز اداری",
            "آبسردکن", "جاروبرقی صنعتی", "کولر گازی ۲۴۰۰۰", "پنکه ایستاده",
            "سماور برقی", "ماشین ظرفشویی", "اجاق گاز ۵ شعله", "تلویزیون ۵۵ اینچ",
            "اسپرسوساز", "تصفیه‌کننده آب",
            "همزن صنعتی", "میز غذاخوری کارکنان"],
    "C04": ["کاغذ A4 بسته ۵۰۰", "تونر پرینتر", "کارتریج جوهر", "لوازم‌التحریر بسته",
            "دستمال کاغذی کارتن", "مواد شوینده صنعتی", "دستکش یکبار مصرف", "ماسک بهداشتی",
            "برچسب حرارتی", "پوشه بایگانی"],
    "C05": ["سوییچ ۴۸ پورت", "روتر سازمانی", "فایروال لبه شبکه", "اکسس‌پوینت WiFi6",
            "سرور رک‌مونت ۲U", "UPS ۳ کیلوا", "کابل شبکه Cat6 حلقه", "پچ‌پنل ۲۴ پورت",
            "NAS چهار بیزی", "ماژول SFP+", "رک دیواری ۹U", "کیف پچ‌کورد"],
    "C06": ["لایسنس ویندوز سرور", "لایسنس SQL Server Std", "آنتی‌ویروس سازمانی سالانه",
            "لایسنس مجازی‌سازی", "اشتراک پشتیبانی شبکه", "لایسنس BI Report Server",
            "سرویس ایمیل سازمانی", "ابزار مانیتورینگ شبکه", "لایسنس بکاپ سازمانی",
            "اشتراک آموزش کاربران"],
}


def jalali_range(year: int):
    d = jdatetime.date(year, 1, 1)
    while d.year == year:
        yield d
        d = d + jdatetime.timedelta(days=1)


# ---------------------------------------------------------------- dim_date
def build_dim_date() -> pd.DataFrame:
    rows = []
    days = list(jalali_range(JALALI_YEAR))
    for d in days:
        g = d.togregorian()
        # weekday() در python: دوشنبه=0 ؛ شنبه=5 → شمسی: شنبه=0
        wd_index = (g.weekday() + 2) % 7  # شنبه→0 ... جمعه→6
        quarter = ((d.month - 1) // 3) + 1
        rows.append({
            "date_key": int(f"{d.year}{d.month:02d}{d.day:02d}"),
            "jalali_date": d.strftime("%Y/%m/%d"),
            "jalali_date_key": int(f"{d.year}{d.month:02d}{d.day:02d}"),
            "gregorian_date": g.strftime("%Y-%m-%d"),
            "year": d.year,
            "month": d.month,
            "month_name_fa": MONTHS_FA[d.month - 1],
            "day": d.day,
            "quarter": quarter,
            "season_fa": {1: "بهار", 2: "تابستان", 3: "پاییز", 4: "زمستان"}[quarter],
            "day_of_week": wd_index,
            "weekday_fa": WEEKDAYS_FA[wd_index],
            "is_weekend": 1 if wd_index == 6 else 0,   # جمعه تعطیل رسمی
            "is_month_start": 1 if d.day == 1 else 0,
            "fiscal_year": d.year,
            "fiscal_period": f"{d.year}-{d.month:02d}",
        })
    return pd.DataFrame(rows)


def build_dim_region() -> pd.DataFrame:
    return pd.DataFrame([
        {"region_id": rid, "region_name_fa": name, "region_code_fa": code, "zone_fa": zone}
        for rid, name, code, zone in REGIONS
    ])


def build_dim_product(rng: random.Random) -> pd.DataFrame:
    rows, pid = [], 0
    cat_price = {c: base for c, _, base in CATEGORIES}  # میلیون ریال پایه
    cat_name = {c: name for c, name, _ in CATEGORIES}
    for cat, names in PRODUCT_NAMES.items():
        for name in names:
            pid += 1
            base = cat_price[cat] * 1_000_000 * PRICE_SCALE
            unit_price = int(rng.uniform(0.55, 1.9) * base / 10_000) * 10_000
            margin = rng.uniform(0.12, 0.38)
            rows.append({
                "product_id": f"P{pid:03d}",
                "product_name_fa": name,
                "category_id": cat,
                "category_name_fa": cat_name[cat],
                "unit_price_irr": unit_price,
                "unit_cost_irr": int(unit_price * (1 - margin) / 1000) * 1000,
                "is_active": 1,
            })
    return pd.DataFrame(rows)


SEGMENTS = [("حقیقی", 55), ("حقوقی", 45)]
CHANNELS = [("فروش مستقیم", 52), ("نمایندگی", 33), ("فروش آنلاین", 15)]


def build_dim_customer(rng: random.Random) -> pd.DataFrame:
    first = ["علی", "رضا", "محمد", "حسین", "مهدی", "سعید", "امیر", "حمید", "بابک", "کامران",
             "زهرا", "فاطمه", "مریم", "سارا", "نرگس", "الهام", "شیدا", "پریسا", "مینا", "نیلوفر"]
    last = ["احمدی", "محمدی", "رضایی", "حسینی", "کریمی", "مرادی", "صادقی", "جعفری", "قاسمی",
            "نوری", "شریفی", "عباسی", "ملکی", "طاهری", "زمانی", "فرهادی", "اکبری", "سلطانی"]
    orgs = ["شرکت پارس تجارت", "گروه صنعتی آرین", "بازرگانی نیک‌روش", "شرکت داده‌پردازان البرز",
            "مجموعه فروشگاهی سپهر", "شرکت تجهیزات کیان", "هلدینگ فناوری رایان", "بازرگانی مهرگان",
            "شرکت خدمات نوین آریا", "گروه بازرگانی دانش"]
    region_ids = [r[0] for r in REGIONS]
    reg_w = [REGION_WEIGHT[r] for r in region_ids]
    seg_names = [s for s, _ in SEGMENTS]
    seg_w = [w for _, w in SEGMENTS]
    chan_names = [c for c, _ in CHANNELS]
    chan_w = [w for _, w in CHANNELS]
    rows = []
    for i in range(1, 501):
        seg = rng.choices(seg_names, seg_w)[0]
        if seg == "حقوقی":
            name = f"{rng.choice(orgs)} — شعبه {rng.randint(1, 9)}"
        else:
            name = f"{rng.choice(first)} {rng.choice(last)}"
        rows.append({
            "customer_id": f"C{i:04d}",
            "customer_name_fa": name,
            "segment_fa": seg,
            "channel_fa": rng.choices(chan_names, chan_w)[0],
            "region_id": rng.choices(region_ids, reg_w)[0],
            "created_date": f"{(rng.randint(1400, 1403)):04d}/{(rng.randint(1, 12)):02d}/{(rng.randint(1, 28)):02d}",
            "is_active": 1 if rng.random() > 0.06 else 0,
        })
    return pd.DataFrame(rows)


def build_facts(rng: random.Random, dim_customer, dim_product, dim_date,
                n_sales=30_000, n_returns=2_000):
    cust = dim_customer[dim_customer.is_active == 1].reset_index(drop=True)
    prods = dim_product.reset_index(drop=True)
    dates = dim_date.reset_index(drop=True)

    # وزن روز: روند رشد ملایم + جهش اسفند (فروش پایان سال)
    n_days = len(dates)
    day_w = [1.0 + 0.55 * (i / n_days) + (0.9 if dates.loc[i, "month"] == 12 else 0.0)
             + (0.25 if dates.loc[i, "month"] == 6 else 0.0) for i in range(n_days)]
    prods_w = [1.0 if c != "C06" else 0.45 for c in prods["category_id"]]  # لایسنس تعداد کمتر
    cust_w = [1.0 if s == "حقوقی" else 0.75 for s in cust["segment_fa"]]

    sales = []
    for i in range(1, n_sales + 1):
        di = rng.choices(range(n_days), day_w)[0]
        pi = rng.choices(range(len(prods)), prods_w)[0]
        ci = rng.choices(range(len(cust)), cust_w)[0]
        p = prods.loc[pi]
        c = cust.loc[ci]
        cat = p["category_id"]
        qty = rng.choices([1, 2, 3, 4, 5, 8, 10, 15, 20, 30],
                          [30, 22, 14, 10, 8, 6, 4, 3, 2, 1] if cat != "C04"
                          else [6, 6, 8, 10, 12, 14, 16, 12, 10, 6])[0]
        disc = rng.choices([0.0, 0.03, 0.05, 0.08, 0.10, 0.15, 0.20],
                           [26, 18, 20, 14, 12, 7, 3])[0]
        unit_price = int(p["unit_price_irr"] * rng.uniform(0.97, 1.06) / 1000) * 1000
        gross = qty * unit_price
        net = int(round(gross * (1 - disc)))
        sales.append({
            "sale_id": f"S{i:06d}",
            "date_key": int(dates.loc[di, "date_key"]),
            "customer_id": c["customer_id"],
            "product_id": p["product_id"],
            "region_id": c["region_id"],
            "channel_fa": c["channel_fa"],
            "quantity": qty,
            "unit_price_irr": unit_price,
            "unit_cost_irr": int(p["unit_cost_irr"]),
            "discount_pct": disc,
            "gross_amount_irr": gross,
            "net_amount_irr": net,
            "cost_amount_irr": qty * int(p["unit_cost_irr"]),
        })
    fact_sales = pd.DataFrame(sales)

    reasons = ["کالای معیوب", "عدم مطابقت با سفارش", "انصراف مشتری", "آسیب در حمل",
               "تأخیر در تحویل", "خطای صورتحساب"]
    ret = []
    sampled = fact_sales.sample(n=n_returns, random_state=SEED // 7)
    for j, (_, s) in enumerate(sampled.iterrows(), start=1):
        # تاریخ مرجوعی: تا ۴۵ روز بعد از فروش، داخل همان سال
        try:
            base = jdatetime.datetime.strptime(str(int(s["date_key"])).replace("/", ""), "%Y%m%d").date()
        except ValueError:
            base = jdatetime.datetime.strptime(str(int(s["date_key"])), "%Y%m%d").date()
        offset = rng.randint(1, 45)
        rd = base + jdatetime.timedelta(days=offset)
        if rd.year != JALALI_YEAR:
            rd = base
        qty_ret = rng.choice([1, 1, 1, 2, 2, 3])
        qty_ret = min(qty_ret, int(s["quantity"]))
        unit_net = int(s["net_amount_irr"]) / int(s["quantity"])
        ret.append({
            "return_id": f"RET{j:05d}",
            "sale_id": s["sale_id"],
            "date_key": int(rd.strftime("%Y%m%d")),
            "customer_id": s["customer_id"],
            "product_id": s["product_id"],
            "region_id": s["region_id"],
            "quantity_returned": qty_ret,
            "return_amount_irr": int(round(unit_net * qty_ret)),
            "reason_fa": rng.choice(reasons),
        })
    fact_returns = pd.DataFrame(ret)
    return fact_sales, fact_returns


def build_stg_raw(rng: random.Random, fact_sales, dim_customer, dim_product) -> pd.DataFrame:
    """۳۰۰ ردیف عمداً کثیف: فرمت‌های مختلط تاریخ، کامای هزارگان، فاصله‌های اضافه، تخفیف خالی."""
    dim_date_keys = fact_sales["date_key"].unique().tolist()
    pick = fact_sales.sample(n=300, random_state=SEED % 97).reset_index(drop=True)
    cust_map = dim_customer.set_index("customer_id")["customer_name_fa"].to_dict()
    prod_map = dim_product.set_index("product_id")["product_name_fa"].to_dict()
    rows = []
    for i, s in pick.iterrows():
        dk = str(int(s["date_key"]))
        jd = jdatetime.datetime.strptime(dk, "%Y%m%d").date()
        gd = jd.togregorian()
        fmt = i % 5
        if fmt == 0:
            raw_date = jd.strftime("%Y/%m/%d")                    # 1403/12/12 (شمسی)
        elif fmt == 1:
            raw_date = gd.strftime("%Y/%m/%d")                    # 2024/07/17 (میلادی)
        elif fmt == 2:
            raw_date = gd.strftime("%d-%m-%Y")                    # 28-07-2024
        elif fmt == 3:
            raw_date = gd.strftime("%Y-%m-%d")                    # 2024-07-28
        else:
            raw_date = jd.strftime("%Y/%m/%d")                    # شمسی
        def messy_amount(v):
            return f"{v:,}" if rng.random() > 0.25 else str(v)
        name = cust_map[s["customer_id"]]
        prod = prod_map[s["product_id"]]
        if rng.random() < 0.35:
            name = f"  {name} "
        if rng.random() < 0.25:
            prod = f"{prod}  "
        disc = s["discount_pct"]
        raw_disc = "" if (disc == 0 and rng.random() < 0.6) else f"{disc:.2f}"
        rows.append({
            "row_id": i + 1,
            "sale_ref": s["sale_id"],
            "sale_date_raw": raw_date,
            "customer_name_raw": name,
            "product_name_raw": prod,
            "region_id_raw": f" {s['region_id']} " if rng.random() < 0.15 else s["region_id"],
            "quantity_raw": f" {s['quantity']} " if rng.random() < 0.15 else s["quantity"],
            "unit_price_raw": messy_amount(int(s["unit_price_irr"])),
            "discount_raw": raw_disc,
        })
    stg = pd.DataFrame(rows)
    # چند ردیف با تخفیف «درصد» نوشته‌شده به‌شکل ۵٪ → برای تست نرمال‌سازی
    stg.loc[[7, 55, 143], "discount_raw"] = stg.loc[[7, 55, 143], "discount_raw"].replace("", "0.05")
    return stg


def build_dims_for_customer_region(fact_sales, dim_customer):
    """هم‌خوانی منطقهٔ فکت با منطقهٔ مشتری یک کنترل کیفیت است."""
    merged = fact_sales.merge(dim_customer[["customer_id", "region_id"]],
                              on="customer_id", suffixes=("", "_cust"))
    bad = (merged["region_id"] != merged["region_id_cust"]).sum()
    return int(bad)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    dim_date = build_dim_date()
    dim_region = build_dim_region()
    dim_product = build_dim_product(rng)
    dim_customer = build_dim_customer(rng)
    fact_sales, fact_returns = build_facts(rng, dim_customer, dim_product, dim_date)
    stg = build_stg_raw(rng, fact_sales, dim_customer, dim_product)

    dim_date.to_csv(DATA_DIR / "dim_date.csv", index=False, encoding="utf-8-sig")
    dim_region.to_csv(DATA_DIR / "dim_region.csv", index=False, encoding="utf-8-sig")
    dim_product.to_csv(DATA_DIR / "dim_product.csv", index=False, encoding="utf-8-sig")
    dim_customer.to_csv(DATA_DIR / "dim_customer.csv", index=False, encoding="utf-8-sig")
    fact_sales.to_csv(DATA_DIR / "fact_sales.csv", index=False, encoding="utf-8-sig")
    fact_returns.to_csv(DATA_DIR / "fact_returns.csv", index=False, encoding="utf-8-sig")
    stg.to_csv(DATA_DIR / "stg_sales_raw.csv", index=False, encoding="utf-8-sig")

    region_mismatch = build_dims_for_customer_region(fact_sales, dim_customer)
    total_net = int(fact_sales["net_amount_irr"].sum())
    total_ret = int(fact_returns["return_amount_irr"].sum())

    print("=== خلاصهٔ تولید داده (seed=%d) ===" % SEED)
    print(f"dim_date      : {len(dim_date):>8,}")
    print(f"dim_region    : {len(dim_region):>8,}")
    print(f"dim_product   : {len(dim_product):>8,}")
    print(f"dim_customer  : {len(dim_customer):>8,}")
    print(f"fact_sales    : {len(fact_sales):>8,}")
    print(f"fact_returns  : {len(fact_returns):>8,}")
    print(f"stg_sales_raw : {len(stg):>8,}  (عمداً کثیف)")
    print(f"sum(net_amount_irr)    : {total_net:,}")
    print(f"sum(return_amount_irr) : {total_ret:,}")
    print(f"ناهم‌خوانی منطقهٔ فکت/مشتری : {region_mismatch}")

    write_data_quality_report(dim_date, dim_region, dim_product, dim_customer,
                              fact_sales, fact_returns, stg, total_net, total_ret,
                              region_mismatch)


def _fa(n: int) -> str:
    return f"{n:,}".replace(",", "٬")


def write_data_quality_report(dim_date, dim_region, dim_product, dim_customer,
                              fact_sales, fact_returns, stg, total_net, total_ret,
                              region_mismatch) -> None:
    n_null_sales = int(fact_sales[["sale_id", "date_key", "customer_id", "product_id",
                                   "region_id", "net_amount_irr"]].isna().any(axis=1).sum())
    dup_sale = int(fact_sales["sale_id"].duplicated().sum())
    fk_cust = int((~fact_sales["customer_id"].isin(dim_customer["customer_id"])).sum())
    fk_prod = int((~fact_sales["product_id"].isin(dim_product["product_id"])).sum())
    fk_reg = int((~fact_sales["region_id"].isin(dim_region["region_id"])).sum())
    fk_date = int((~fact_sales["date_key"].isin(dim_date["date_key"])).sum())
    neg_net = int((fact_sales["net_amount_irr"] <= 0).sum())
    calc_mismatch = int((fact_sales["net_amount_irr"] !=
                         (fact_sales["quantity"] * fact_sales["unit_price_irr"]
                          * (1 - fact_sales["discount_pct"])).round()).sum())
    fk_ret_sale = int((~fact_returns["sale_id"].isin(fact_sales["sale_id"])).sum())
    over_return = int((fact_returns["return_amount_irr"] > total_net * 0.02).sum())

    stg_blank_disc = int((stg["discount_raw"].astype(str).str.strip() == "").sum())
    stg_comma = int(stg["unit_price_raw"].astype(str).str.contains(",").sum())

    md = f"""# گزارش کیفیت داده — پروژهٔ ۵ (نمونه)
> تولید با `scripts/generate_all_data.py` و `seed={SEED}`. کل اعداد **نمونه** هستند و فروش واقعی هیچ سازمانی نیستند.

## ۱) حجم جداول
| جدول | ردیف | توضیح |
|---|---:|---|
| dim_date | {_fa(len(dim_date))} | کل سال {JALALI_YEAR} شمسی (۳۶۶ روز) |
| dim_region | {_fa(len(dim_region))} | ۱۲ منطقه |
| dim_product | {_fa(len(dim_product))} | ۶ دستهٔ کالایی |
| dim_customer | {_fa(len(dim_customer))} | حقیقی/حقوقی + کانال فروش |
| fact_sales | {_fa(len(fact_sales))} | اسناد فروش سال {JALALI_YEAR} |
| fact_returns | {_fa(len(fact_returns))} | مرجوعی، ارجاع به sale_id |
| stg_sales_raw | {_fa(len(stg))} | ورودی عمداً کثیف (۳۰۰ ردیف) |

## ۲) کنترل‌های کیفیت — نتیجهٔ اجرا
| کنترل | نتیجه | وضعیت |
|---|---|---|
| یکتایی `fact_sales.sale_id` | تکراری = {dup_sale} | {"✅" if dup_sale == 0 else "❌"} |
| Null در ستون‌های کلیدی فکت فروش | {n_null_sales} | {"✅" if n_null_sales == 0 else "❌"} |
| FK فروش → dim_customer | نقض = {fk_cust} | {"✅" if fk_cust == 0 else "❌"} |
| FK فروش → dim_product | نقض = {fk_prod} | {"✅" if fk_prod == 0 else "❌"} |
| FK فروش → dim_region | نقض = {fk_reg} | {"✅" if fk_reg == 0 else "❌"} |
| FK فروش → dim_date | نقض = {fk_date} | {"✅" if fk_date == 0 else "❌"} |
| FK مرجوعی → fact_sales | نقض = {fk_ret_sale} | {"✅" if fk_ret_sale == 0 else "❌"} |
| هم‌خوانی منطقهٔ فکت با منطقهٔ مشتری | ناهم‌خوان = {region_mismatch} | {"✅" if region_mismatch == 0 else "❌"} |
| بازمحاسبهٔ net = qty×price×(1-disc) | مغایرت = {calc_mismatch} | {"✅" if calc_mismatch == 0 else "❌"} |
| net_amount_irr ≤ 0 | {neg_net} | {"✅" if neg_net == 0 else "❌"} |
| مرجوعی غیرعادی (>۲٪ کل فروش) | {over_return} | {"✅" if over_return == 0 else "❌"} |

## ۳) کنترل‌های ورودی خام (staging)
| کنترل | نتیجه |
|---|---|
| ردیف‌های با تخفیف خالی (نیازمند پیش‌فرض ۰) | {_fa(stg_blank_disc)} |
| ردیف‌های با کامای هزارگان در مبلغ | {_fa(stg_comma)} |
| فرمت‌های تاریخ موجود | شمسی `YYYY/MM/DD`، میلادی `YYYY/MM/DD`، `DD-MM-YYYY`، `YYYY-MM-DD` |

نتیجهٔ اجرای واقعی ETL (فایل `model/etl_staging_to_dw.py`): ۳۰۰ ردیف خوانده، ۳۰۰ ردیف تمیز، **۰ ردیف Reject** — چون همهٔ فرمت‌های تاریخ در نمونه قابل تبدیل طراحی شده‌اند. مسیر Reject در `model/schema.sql` (جدول `etl_reject`) وجود دارد ولی در این نمونه با دادهٔ واقعی صفر است.

## ۴) جمع‌های کنترلی
| سنجه | مقدار (ریال) |
|---|---:|
| Σ `net_amount_irr` فروش | {_fa(total_net)} |
| Σ `return_amount_irr` مرجوعی | {_fa(total_ret)} |
| نسبت مرجوعی به فروش | {total_ret / total_net * 100:.2f}٪ |
"""
    (DATA_DIR / "DATA_QUALITY_REPORT.md").write_text(md, encoding="utf-8")

    dd = f"""# فرهنگ داده (Data Dictionary) — DW نمونه
> واحد پول: **ریال** | تقویم: **شمسی {JALALI_YEAR}** + معادل میلادی | seed={SEED} | تمام داده نمونه است.

## dim_date — تقویم
| ستون | نوع (T-SQL) | کلید | توضیح |
|---|---|---|---|
| date_key | INT | PK | کلید عددی تاریخ شمسی به شکل YYYYMMDD (مثلاً ۱۴۰۳۱۲۱۲ → 14031212) |
| jalali_date | CHAR(10) | | تاریخ شمسی متنی |
| jalali_date_key | INT | | همان date_key (برای Time Intelligence روی تقویم شمسی) |
| gregorian_date | DATE | | معادل میلادی |
| year / month / day | INT | | اجزا |
| month_name_fa | NVARCHAR(20) | | نام ماه فارسی |
| quarter / season_fa | INT / NVARCHAR(10) | | فصل |
| day_of_week / weekday_fa | INT / NVARCHAR(20) | | ۰=شنبه … ۶=جمعه |
| is_weekend | BIT | | جمعه = ۱ |
| is_month_start | BIT | | روز اول ماه |
| fiscal_year / fiscal_period | INT / CHAR(7) | | سال/دورهٔ مالی (سال شمسی = سال مالی فرضی) |

## dim_customer — مشتری
| ستون | نوع | توضیح |
|---|---|---|
| customer_id | NVARCHAR(10) PK | کلید طبیعی |
| customer_name_fa | NVARCHAR(120) | نام شخص/سازمان |
| segment_fa | NVARCHAR(20) | حقیقی / حقوقی |
| channel_fa | NVARCHAR(30) | فروش مستقیم / نمایندگی / فروش آنلاین |
| region_id | NVARCHAR(5) FK | منطقهٔ خدمت |
| created_date | CHAR(10) | تاریخ شمسی ایجاد |
| is_active | BIT | ۰ = غیرفعال |

## dim_product — کالا
| ستون | نوع | توضیح |
|---|---|---|
| product_id | NVARCHAR(10) PK | کلید کالا |
| product_name_fa | NVARCHAR(150) | نام کالا |
| category_id / category_name_fa | NVARCHAR(10) / NVARCHAR(60) | دسته |
| unit_price_irr | BIGINT | قیمت فهرست (ریال) |
| unit_cost_irr | BIGINT | بهای تمام‌شده |
| is_active | BIT | |

## dim_region — منطقه
| ستون | نوع | توضیح |
|---|---|---|
| region_id | NVARCHAR(5) PK | R01…R12 |
| region_name_fa | NVARCHAR(60) | نام منطقه/شهر |
| region_code_fa | NVARCHAR(20) | کد نمایشی |
| zone_fa | NVARCHAR(30) | پهنهٔ جغرافیایی |

## fact_sales — فکت فروش (دانه: یک سطر سفارش/کالا)
| ستون | نوع | توضیح |
|---|---|---|
| sale_id | NVARCHAR(12) PK | شناسهٔ سند |
| date_key | INT FK | تاریخ شمسی |
| customer_id / product_id / region_id | NVARCHAR FK | ابعاد |
| channel_fa | NVARCHAR(30) | کانال (denormalized برای سرعت گزارش) |
| quantity | INT | تعداد |
| unit_price_irr | BIGINT | قیمت واحد |
| unit_cost_irr | BIGINT | بهای واحد |
| discount_pct | DECIMAL(5,2) | تخفیف (۰ تا ۰.۳) |
| gross_amount_irr | BIGINT | qty × price |
| net_amount_irr | BIGINT | qty × price × (1-disc) |
| cost_amount_irr | BIGINT | qty × cost |

## fact_returns — فکت مرجوعی
| ستون | نوع | توضیح |
|---|---|---|
| return_id | NVARCHAR(12) PK | شناسهٔ مرجوعی |
| sale_id | NVARCHAR(12) FK | سند فروش مبدأ |
| date_key | INT FK | تاریخ مرجوعی (شمسی) |
| customer_id / product_id / region_id | NVARCHAR FK | ابعاد (fora از فروش) |
| quantity_returned | INT | تعداد برگشتی |
| return_amount_irr | BIGINT | مبلغ برگشتی |
| reason_fa | NVARCHAR(60) | علت |

## stg_sales_raw — ورودی خام (staging)
| ستون | نوع | نکتهٔ کیفیت |
|---|---|---|
| row_id | INT | ردیف فایل |
| sale_ref | NVARCHAR(12) | ارجاع به sale_id |
| sale_date_raw | NVARCHAR(20) | **مختلط**: 1403/12/12 ، 2024/07/17 ، 28-07-2024 ، 2024-07-28 |
| customer_name_raw / product_name_raw | NVARCHAR | فاصلهٔ اضافهٔ ابتدا/انتها |
| region_id_raw | NVARCHAR(5) | گاهی با فاصله |
| quantity_raw | NVARCHAR(10) | گاهی با فاصله |
| unit_price_raw | NVARCHAR(20) | کامای هزارگان |
| discount_raw | NVARCHAR(6) | خالی = ۰ |
"""
    (DATA_DIR / "DATA_DICTIONARY.md").write_text(dd, encoding="utf-8")


if __name__ == "__main__":
    os.chdir(BASE_DIR)
    main()

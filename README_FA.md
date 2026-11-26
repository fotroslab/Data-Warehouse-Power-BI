# پروژهٔ ۵ — راهکار سازمانی: SQL Server + Data Warehouse + Power BI Report Server

**«طرح انبار داده + اثبات منطق ETL»** برای سازمانی با شبکهٔ داخلی و بدون ابر.

| | |
|---|---|
| تاریخ | ۱۴۰۵/۰۹/۰۵ |
| پوشه | `project_05_sqlserver_reportserver/` |
| وضعیت | اسناد، مدل، ETL اجراشده و اپ پیش‌نمایش کامل — **بدون نصب SQL Server/Report Server** |
| اپ پیش‌نمایش | `streamlit run app.py --server.port 8506` (۵ صفحه، فارسی/RTL) |
| داده | نمونهٔ قابل بازتولید با `seed=14030505` — **فروش واقعی هیچ سازمانی نیست** |

---

## ۱) این پروژه چه چیزی را ثابت می‌کند و چه چیزی را نه

**ثابت می‌کند (اجراشده و قابل بازتولید):**

* طراحی استاراسکیما با تقویم شمسی و DDL کامل T-SQL (`model/schema.sql`).
* ETL واقعی روی ۳۰۰ ردیف عمداً کثیف: چهار فرمت تاریخ، کامای هزارگان، فاصله‌های اضافه،
  تخفیف خالی → **۳۰۰/۳۰۰ تمیز، ۰ Reject** (`model/etl_staging_to_dw.py`).
* بارگذاری ۳۰٬۰۰۰ سند فروش و ۲٬۰۰۰ مرجوعی با کنترل توازن، یکتایی و FK
  (خروجی: `model/dw_demo.sqlite`, `Σ net = 12,491,123,417,390 ریال`).
* ۳۷ تست سبز + اجرای بدون خطای هر ۵ صفحهٔ اپ (AppTest).

**ثابت نمی‌کند (صادقانه):**

* SQL Server نصب نشده؛ `schema.sql` روی سرور واقعی اجرا نشده و **نیازمند DBA Review** است.
* Power BI Report Server نصب/لایسنس نشده؛ فایل `.pbix` وجود ندارد؛ گزارشی منتشر نشده.
* RLS منطقه‌ای فقط **مستند** است (بدون Security Policy و بدون View-as).
* SSL، DNS داخلی، تست بار، UAT و انطباق با «شرح خدمات» انجام نشده (پیوست در دسترس نبود).
* هیچ ادعای ROI، صرفه‌جویی یا بهره‌وری وجود ندارد.

---

## ۲) اجرای سریع

```bash
# ۱) تولید دادهٔ نمونه (اختیاری — خروجی‌ها در مخزن هستند)
python3 scripts/generate_all_data.py

# ۲) اجرای واقعی ETL  → model/dw_demo.sqlite
python3 model/etl_staging_to_dw.py

# ۳) تست‌ها
python3 -m unittest discover -s tests -v

# ۴) اپ پیش‌نمایش
streamlit run app.py --server.port 8506 --server.address 0.0.0.0
```

پیش‌نیاز: `python3.11+`، `pandas`، `streamlit`، `plotly`، `jdatetime`
(برای اسکرین‌شات: `playwright` + `chromium`).

---

## ۳) ساختار پوشه

```text
project_05_sqlserver_reportserver/
├── app.py                       # اپ Streamlit — ۵ صفحه، فارسی/RTL/Vazirmatn/ریال/شمسی
├── README_FA.md                 # همین فایل
├── HANDOFF_FA.md                # هندآف فنی برای ایجنت/تیم بعدی
├── PORTFOLIO_CASE_STUDY_EN.md    # «DW Blueprint + ETL Proof» (انگلیسی)
├── VALIDATION.md                # اجراهای واقعی + موارد تست‌نشده
├── LIMITATIONS.md               # همهٔ محدودیت‌ها، بی‌پرده
├── SOURCES.md                   # منبع داده و seed
├── model/
│   ├── schema.sql               # DDL کامل T-SQL: stg → reject → ابعاد/فکت (idempotent)
│   ├── etl_staging_to_dw.py     # ETL اجراشده (پاک‌سازی + Reject + کنترل کیفیت)
│   ├── dw_demo.sqlite           # خروجی ETL — جایگزین محلی SQL Server
│   ├── MODEL.md                 # توضیح استاراسکیما و تصمیم‌ها
│   └── measures.dax             # KPIها: فروش، حاشیه، مرجوعی، YTD/MTD شمسی
├── report/
│   ├── ARCHITECTURE.md          # معماری هدف، جریان داده، امنیت/RLS، کارایی
│   ├── DEPLOYMENT_CHECKLIST.md  # مراحل نصب با مسئول/پیش‌نیاز/ریسک
│   ├── POWER_BI_BUILD_GUIDE.md  # ساخت گزارش، RLS، View-as، Publish
│   └── theme.json               # تم «Enterprise DW Fa» (#232b36 + #d64541 روی #f6f7f8)
├── data/                        # ۷ فایل CSV + DATA_DICTIONARY + DATA_QUALITY_REPORT
├── scripts/
│   ├── generate_all_data.py     # تولید داده با seed=14030505
│   ├── make_model_diagram.py    # تولید SVG مدل
│   └── make_preview.py          # اسکرین‌شات واقعی با Playwright
├── tests/test_data_quality.py   # ۳۷ تست
├── requirements.txt             # وابستگی‌ها
├── .streamlit/config.toml       # تم پایه و پورت ۸۵۰۶
└── assets/
    ├── preview.png              # اسکرین‌شات صفحهٔ نمای کلی
    ├── preview_etl.png          # اسکرین‌شات پس از اجرای واقعی ETL
    ├── preview_sales.png        # اسکرین‌شات تحلیل فروش
    ├── model_diagram.svg        # نمودار مدل ستاره‌ای
    └── fonts/                   # Vazirmatn (woff2)
```

---

## ۴) مدل داده در یک نگاه

| جدول | ردیف | نقش |
|---|---:|---|
| `dw.dim_date` | ۳۶۶ | تقویم شمسی ۱۴۰۳ + معادل میلادی + فصل + تعطیلی جمعه |
| `dw.dim_region` | ۱۲ | منطقه و پهنه |
| `dw.dim_customer` | ۵۰۰ | حقیقی/حقوقی + کانال + منطقهٔ خدمت |
| `dw.dim_product` | ۸۰ | کالا، دسته، قیمت فهرست و بهای تمام‌شده |
| `dw.fact_sales` | ۳۰٬۰۰۰ | یک سطر = یک قلم فروش (net = qty×price×(1−disc)) |
| `dw.fact_returns` | ۲٬۰۰۰ | مرجوعی با ارجاع به `sale_id` |
| `dw.etl_reject` | ۰ در نمونه | پایش کیفیت ورودی (stage/reason/raw_payload) |
| `dw.etl_load_log` | هر بار ETL | لاگ خوانده/تمیز/مردود و وضعیت |

کلید تاریخ (`date_key`) عددی `YYYYMMDD` **شمسی** است و `jalali_date_key` عیناً همان مقدار.

---

## ۵) پایپ‌لاین واقعی (خروجی اجرا)

```text
stg_sales_raw.csv (۳۰۰ ردیف: 1403/12/12 ، 2024/07/17 ، 28-07-2024 ، 2024-07-28 ،
                              کامای هزارگان، فاصلهٔ اضافه، تخفیف خالی)
  → [1/4] ابعاد بارگذاری شد → dim_date=366 | dim_region=12 | dim_product=80 | dim_customer=500
  → [2/4] فکت‌ها بارگذاری شد → fact_sales=30,000 | fact_returns=2,000
  → [3/4] خوانده: 300 | تمیز: 300 | Reject: 0
  → [4/4] orphan_sales_*=0 · net_mismatch=0 · distinct_regions=12
  → Σ net_amount_irr = 12,491,123,417,390 ریال   (≈ ۱۲٫۴۹ همت)
  → وضعیت: SUCCESS   DB: model/dw_demo.sqlite
```

لاگ کامل در [VALIDATION.md](VALIDATION.md).

---

## ۶) اپ پیش‌نمایش

| صفحه | محتوا |
|---|---|
| **نمای کلی انبار داده** | KPIها، معماری در یک نگاه، نمودار مدل، سه ادعایی که پروژه نمی‌کند |
| **پایپ‌لاین زندهٔ ETL** | جدول ردیف‌های کثیف + دکمه‌ای که واقعاً اسکریپت را با `subprocess` اجرا می‌کند و لاگ را نشان می‌دهد + محتوای sqlite |
| **تحلیل فروش نمونه** | فیلتر منطقه، روند ماهانه شمسی، فروش منطقه‌ای، دستهٔ کالا، علت مرجوعی، ۱۰ کالای پرفروش |
| **استقرار و معماری** | معماری هدف، وضعیت واقعی اجزا، مراحل استقرار، تصمیم‌های فنی و هزینه‌شان |
| **دربارهٔ داده** | seed، کنترل‌های کیفیت، محدودیت‌ها و منبع داده |

نکته‌های RTL: چارت‌ها `direction: ltr` هستند تا برچسب فارسی نصفه نشود؛
برچسب میله‌ها `cliponaxis=False`؛ حاشیه‌ها از تابع `style_fig(margin=...)`.

---

## ۷) تست‌ها

```text
python3 -m unittest discover -s tests -v
Ran 37 tests — OK
```

پوشش: یکتایی کلیدها، FK فکت←ابعاد، بازمحاسبهٔ `net`، جمع مبالغ، هم‌خوانی منطقه،
تبدیل هر چهار فرمت تاریخ، حذف کامای هزارگان، تخفیف خالی→۰، اعتبار theme.json و SVG،
و وجود همهٔ تحویل‌ها.

---

## ۸) مسیر بعدی

1. تهیهٔ «شرح خدمات» واقعی و بازنویسی Scope.
2. دریافت دسترسی SQL Server → **DBA Review روی `schema.sql`** → اجرا در Test.
3. ETL روی سرور (SSIS یا Python زمان‌بندی‌شده) + کنترل کیفیت.
4. نصب Report Server + لایسنس + HTTPS + DNS داخلی.
5. ساخت `.pbix`، Publish، پیاده‌سازی و تست RLS با View-as.
6. تست بار، UAT، آموزش و Run Book — سپس بستن آیتم‌های [LIMITATIONS.md](LIMITATIONS.md) یکی‌یکی.

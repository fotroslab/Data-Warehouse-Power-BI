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

**پیش‌نیاز:** پایتون **۳٫۹ یا بالاتر** (تست‌شده روی ۳٫۱۱ و ۳٫۱۳) + `pandas`، `streamlit`،
`plotly`، `jdatetime` (برای اسکرین‌شات: `playwright` + `chromium`).

```bash
python3 scripts/check_compat.py   # نگهبان سازگاری: عدد PEP 701 = 0
```

---

## ۲.۴) فایل `.streamlit/config.toml` — چرا در فایل‌منیجر دیده نمی‌شود

پوشه‌هایی که نامشان با نقطه شروع می‌شود (`.streamlit`، `.git`، `.github`) در بسیاری از
فایل‌منیجرها، آپلودهای drag&drop و GitHub روی موبایل **مخفی** هستند.

| سیستم | نمایش پوشه‌های مخفی |
|---|---|
| macOS Finder | `Cmd + Shift + .` |
| Windows Explorer | View → Hidden items |
| VS Code | به‌صورت پیش‌فرض نمایش می‌دهد (در اکسپلورر) |
| GitHub وب | نمایش داده می‌شود؛ در آپلود دستی، پوشهٔ خالی/مخفی منتقل نمی‌شود |
| FileZilla | Server → Force showing hidden files |

**اگر با آپلود دستی کار می‌کنید:** پوشه را بسازید و فایل را داخلش بگذارید، یا از کپیِ
همین مخزن استفاده کنید: [`config.streamlit.toml`](config.streamlit.toml) — دقیقاً همان محتوا.
برای بازسازی مسیر درست:

```bash
mkdir -p .streamlit && cp config.streamlit.toml .streamlit/config.toml
```

> این فایل **اختیاری** است: رنگ‌ها در خودِ `app.py` هم تعریف شده‌اند. اگر نباشد، اپ کار می‌کند
> و فقط پورت پیش‌فرض ۸۵۰۱ می‌شود (روی Streamlit Cloud مهم نیست چون پورت را خودش می‌دهد).

## ۲.۵) استقرار روی Streamlit Community Cloud — و درسِ PEP 701

اگر اپ را روی Streamlit Cloud منتشر می‌کنید:

1. `requirements.txt` در ریشهٔ مخزن بماند.
2. در **Settings → Python version** نسخهٔ **۳٫۱۱** (یا ۳٫۱۲) را انتخاب کنید.
3. اگر خطای `SyntaxError` گرفتید، اول `python3 scripts/check_compat.py` را اجرا کنید.

**خطای واقعی که رخ داد و رفع شد:** یک f-string با عبارت چندخطی داخل `{}` نوشته شده بود:

```python
# ❌ فقط روی پایتون ۳٫۱۲+ (PEP 701) خوانده می‌شود
f'آخرین بازنویسی: {fa_digits(pd.Timestamp(...)
                            .tz_convert("Asia/Tehran").strftime(...))}'
```

```python
# ✅ سازگار با ۳٫۹+
stamp = pd.Timestamp(DB_PATH.stat().st_mtime, unit="s", tz="UTC")
stamp_fa = fa_digits(stamp.tz_convert("Asia/Tehran").strftime("%Y/%m/%d %H:%M"))
st.markdown(f'آخرین بازنویسی: {stamp_fa}', unsafe_allow_html=True)
```

قاعده: **هیچ عبارت چندخطی، بک‌اسلش، کامنت یا کوتیشن همسان داخل `{}` نگذارید.**
مقدار را در متغیر بگیرید. سه لایه محافظ اضافه شد:

| محافظ | فایل |
|---|---|
| اسکریپت بررسی با `tokenize` (FSTRING_START/MIDDLE/END) | `scripts/check_compat.py` |
| تست قفل‌کننده: `ast.parse(..., feature_version=(3,9))` + تست PEP 701 | `tests/test_data_quality.py::TestCompatibility` |
| گارد زمان اجرا با پیام فارسی + `st.stop()` | ابتدای `app.py` |

**اعتبارسنجی واقعی:** با نصب پایتون ۳٫۱۱٫۱۸ و نصب مجدد وابستگی‌ها، کل تست‌ها (۳۹)، ETL، هر ۵ صفحه
با AppTest و بوت سرور Streamlit اجرا و تأیید شد — نه فقط بررسی گرامر.

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
│   └── theme.json               # تم «Enterprise DW Fa» (#1f2630 + #9c4a3c روی #f7f8f9)
├── data/                        # ۷ فایل CSV + DATA_DICTIONARY + DATA_QUALITY_REPORT
├── scripts/
│   ├── generate_all_data.py     # تولید داده با seed=14030505
│   ├── make_model_diagram.py    # تولید SVG مدل
│   └── make_preview.py          # اسکرین‌شات واقعی با Playwright
├── tests/test_data_quality.py   # ۳۹ تست (کیفیت داده + سازگاری پایتون)
├── tests/test_rtl_layout.py     # ۳ تست مرورگری راست‌چینی
├── requirements.txt             # وابستگی‌ها
├── .streamlit/config.toml       # تم پایه و پورت ۸۵۰۶ (پوشهٔ مخفی)
├── config.streamlit.toml        # کپیِ قابل‌مشاهدهٔ همان فایل (برای انتقال/بازبینی)
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
| **نمای کلی** | KPIها، جریان داده، نمودار مدل، جدول‌ها |
| **پایپ‌لاین ETL** | جدول ردیف‌های کثیف + دکمه‌ای که واقعاً اسکریپت را با `subprocess` اجرا می‌کند و لاگ را نشان می‌دهد + محتوای sqlite |
| **تحلیل فروش** | فیلتر منطقه، روند ماهانه شمسی، فروش منطقه‌ای، دستهٔ کالا، علت مرجوعی، ۱۰ کالای پرفروش |
| **استقرار** | معماری هدف، وضعیت واقعی اجزا، مراحل استقرار، تصمیم‌های فنی و هزینه‌شان |
| **دربارهٔ داده** | seed، کنترل‌های کیفیت، محدودیت‌ها، منبع |

### سیستم طراحی (UI)

یک سیستم **توکن‌محور** در بالای `app.py` (دیکشنری `T`): همهٔ رنگ‌ها، اندازه‌ها، فاصله‌ها و
شعاع‌ها فقط از همان‌جا می‌آیند تا هیچ بخشی اندازهٔ خودش را اختراع نکند.

| توکن | مقدار |
|---|---|
| رنگ | صفحه `#f7f8fa` · سطح `#ffffff` · ملایم `#f6f7f9` · خط `#e4e8ec` · خط مویی `#eef1f4` · متن `#18202b` / `#46525f` / `#78838f` / `#9aa4af` · لهجهٔ آجری `#9c4a3c` |
| تایپ | نمایش `1.5rem` · تیتر بخش `1.02rem` · زیرتیتر `.9rem` · متن `.875rem` · کوچک `.79rem` · ریز `.72rem` — همه با Vazirmatn |
| فاصله | فاصلهٔ صفحه `1.9rem` · بین بلوک‌ها `1.15rem` · شعاع `10px` / `7px` |

**ایده‌های کلیدی چیدمان**

* **یک فونت در کل صفحه** — `font-family` روی `.stApp *` و همهٔ عناصر Markdown اعمال می‌شود.
  علت اشکال قبلی: فونت فقط روی body تنظیم شده بود و محتوا با Source Sans (بدون گلیف فارسی)
  رندر می‌شد؛ مرورگر به فونت عربیِ جایگزین می‌افتاد و تیترها «کج» دیده می‌شدند.
* **کارت واقعی برای ویجت‌ها** — `st.container(border=True)` استایل کارت می‌گیرد؛ کارت HTML
  نمی‌تواند ویجت Streamlit را در خود بگیرد و نمودار بیرون کارت می‌افتاد.
* **نوار KPI یکپارچه** — یک کادر با جداکننده‌های مویی، مقدار `1.12rem`، راهنما `.72rem`.
* **نمودار با قرارداد RTL** — تابع `hbar()` میله را از راست رشد می‌دهد و برچسب دسته را در
  حاشیهٔ آزاد می‌گذارد؛ تابع `fa_axis()` ارقام محور را فارسی می‌کند (Plotly خودش فارسی نمی‌نویسد).
* **نمودار مدل درون‌خطی** — SVG داخل HTML اپ درج می‌شود تا فونت و اندازه‌ها با بقیهٔ صفحه یکی باشد.
* **متن کم** — هر بخش یک تیتر + یک خط توضیح؛ هشدارها در یک بلوک پایانی.

### راست‌چینی (RTL) — چطور تضمین می‌شود

`direction: rtl` **به‌تنهایی کافی نیست**؛ Streamlit خودش `text-align: left` را روی
`[data-testid="stMarkdownContainer"]`، تیترها و کارت‌ها اعمال می‌کند و نتیجه، متنِ چپ‌چین می‌شود.
سه اقدام لازم بود:

| اقدام | جزئیات |
|---|---|
| بازنویسی صریح تراز | `.stApp, .stApp p/span/div/li/label, h1…h6, [data-testid="stMarkdownContainer"] … { direction:rtl; text-align:right }` |
| **حذف `st.dataframe`** | این ویجت (glide-data-grid) همیشه LTR است؛ جای آن تابع `rtl_table()` با جدول HTML راست‌چین (هدر چسبان، سطرهای یک‌درمیان، سلول عددی با `tabular-nums`، سلول فنی `.mono` چپ‌چین) |
| استثناهای عمدی | `code`/`pre` و نام فایل‌ها/ستون‌ها **چپ‌چین** می‌مانند تا T-SQL و نام ستون‌ها خوانا باشد |
| نمودارها | `.js-plotly-plot{direction:ltr}` تا برچسب فارسی نصفه نشود؛ `cliponaxis=False`؛ `margin` از `style_fig` |

این مورد با **تست مرورگری واقعی** قفل شده است: `tests/test_rtl_layout.py` مقدار محاسبه‌شدهٔ
`direction`/`text-align` را از DOM می‌خواند و اگر جایی چپ‌چین باشد می‌شکند (۳ تست).

---

## ۷) تست‌ها

```text
python3 -m unittest discover -s tests -v
Ran 42 tests — OK      # ۳۹ کیفیت داده/سازگاری + ۳ راست‌چینی (مرورگری)
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

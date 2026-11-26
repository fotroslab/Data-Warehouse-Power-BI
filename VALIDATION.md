# اعتبارسنجی (VALIDATION.md)

> این سند فقط چیزهایی را ثبت می‌کند که **واقعاً اجرا شده‌اند** و در پایان، فهرست صریح
> چیزهایی که **تست نشده‌اند** را می‌آورد. تاریخ اجراها: ۱۴۰۵/۰۹/۰۵.

## ۱) اجرای تولید داده

```text
$ python3 scripts/generate_all_data.py
=== خلاصهٔ تولید داده (seed=14030505) ===
dim_date      :      366
dim_region    :       12
dim_product   :       80
dim_customer  :      500
fact_sales    :   30,000
fact_returns  :    2,000
stg_sales_raw :      300  (عمداً کثیف)
sum(net_amount_irr)    : 12,491,123,417,390
sum(return_amount_irr) : 292,436,651,960
ناهم‌خوانی منطقهٔ فکت/مشتری : 0
```

✅ موفق. خروجی: ۷ فایل CSV در `data/` + `DATA_DICTIONARY.md` + `DATA_QUALITY_REPORT.md`.

## ۲) اجرای ETL (واقعی)

```text
$ python3 model/etl_staging_to_dw.py
====================================================================
ETL: stg_sales_raw.csv  →  dw_demo.sqlite   (جایگزین محلیِ SQL Server)
batch: 1b816fb3-5638-4625-9126-1eb5e110494e
====================================================================
[1/4] ابعاد بارگذاری شد → dim_date=366 | dim_region=12 | dim_product=80 | dim_customer=500
[2/4] فکت‌ها بارگذاری شد → fact_sales=30٬000 | fact_returns=2٬000
[3/4] پاک‌سازی staging → خوانده: 300 | تمیز: 300 | Reject: 0
[4/4] کنترل‌های کیفیت:
      fact_sales_rows            = 30٬000
      fact_returns_rows          = 2٬000
      sum_net_amount_irr         = 12٬491٬123٬417٬390
      sum_return_amount_irr      = 292٬436٬651٬960
      distinct_regions           = 12
      orphan_sales_customer      = 0
      orphan_sales_product       = 0
      orphan_sales_date          = 0
      orphan_returns_sale        = 0
      net_mismatch               = 0
      reject_rows                = 0
      sum(net_amount_irr)        = 12٬491٬123٬417٬390 ریال
--------------------------------------------------------------------
وضعیت: SUCCESS  |  DB: model/dw_demo.sqlite
توجه: SQLite فقط جایگزین محلی برای اثبات منطق است؛ SQL Server واقعی اجرا نشده.
====================================================================
```

✅ موفق — کد خروج ۰. خروجی `model/dw_demo.sqlite` (۳٫۰ مگابایت) با ۹ جدول.

### توضیح «Reject = ۰»
هر چهار فرمت تاریخ موجود در staging قابل تبدیل‌اند و هیچ ردیف نامعتبری در نمونه وجود ندارد.
این یک **نتیجه** است، نه ادعای کامل‌بودن: مسیر Reject در کد (`transform_staging`) و در
`schema.sql` (`dw.etl_reject`) آماده است و با تزریق ردیف‌های نامعتبر در تست‌ها اثبات شده
(`TestStagingTransform.test_bad_date_raises`).

## ۳) تست‌ها

```text
$ python3 -m unittest discover -s tests -v
Ran 37 tests in 0.100s
OK
```

| گروه | نمونهٔ کنترل‌ها |
|---|---|
| ابعاد | یکتایی PK، تطابق `jalali_date_key = date_key`، قالب `YYYYMMDD`، ۳۱ روز برای شش ماه اول، پرچم جمعه، حاشیهٔ مثبت کالا |
| فکت‌ها | یکتایی `sale_id`/`return_id`، FK به چهار بعد، بازمحاسبهٔ `net`، `gross = qty×price`، `cost = qty×unit_cost`، هم‌خوانی منطقه، مرجوعی ≤ خط فروش، ثبات جمع مبالغ |
| staging | تبدیل هر ۳۰۰ تاریخ، وجود هر چهار فرمت، خطا برای تاریخ نامعتبر، حذف کاما، تخفیف خالی→۰، پشتیبانی `5%`/`۵٪` |
| اقلام | وجود همهٔ تحویل‌ها، اعتبار `theme.json`، اعتبار XML نمودار، وجود اشیای کلیدی در `schema.sql` |

## ۴) اپ Streamlit

* اجرا: `streamlit run app.py --server.port 8506 --server.address 0.0.0.0` → سرور بالا آمد و
  روی پورت ۸۵۰۶ پاسخ می‌دهد (این محیط، پیش‌نمایش زنده).
* **AppTest** روی هر ۵ صفحه: بدون استثنا؛ `warnings/errors = 0`.
* کلیک واقعی روی دکمهٔ «اجرای ETL روی staging»: `subprocess` اجرا شد، خروجی متنی
  اسکریپت (شامل «خوانده: 300 | تمیز: 300 | Reject: 0») در صفحه نمایش داده شد.
* اسکرین‌شات واقعی با Playwright در viewport `1520×1750` (scale 1.4):
  `assets/preview.png`، `assets/preview_etl.png` (پس از اجرای ETL)، `assets/preview_sales.png`.

## ۵) اقلام ساختاری

| قلم | کنترل | نتیجه |
|---|---|---|
| `report/theme.json` | `json.loads` + وجود `#232b36` و `#d64541` | ✅ معتبر |
| `assets/model_diagram.svg` | `ElementTree.parse` | ✅ XML معتبر |
| `model/schema.sql` | بررسی متنی وجود اشیای کلیدی (`dw.fact_sales`, `jalali_date_key`, `SCHEMA_ID`, …) | ✅ موجود |
| فونت | `Vazirmatn-*.woff2` واقعی (WOFF2، نسخهٔ ۳۳) | ✅ بارگذاری در مرورگر |

## ۶) مواردی که تست نشده‌اند — صریح

| مورد | وضعیت |
|---|---|
| اجرای `schema.sql` روی SQL Server واقعی | ⛔ هرگز اجرا نشده؛ نیازمند DBA Review (کالیشن، فایل‌گروپ، سازگاری) |
| نصب/پیکربندی Power BI Report Server | ⛔ انجام نشده؛ لایسنس تأمین نشده |
| ساخت و اعتبارسنجی فایل `.pbix` | ⛔ وجود ندارد |
| انتشار گزارش و Refresh زمان‌بندی‌شده | ⛔ انجام نشده |
| RLS منطقه‌ای و View-as | ⛔ فقط مستند |
| HTTPS/SSL با گواهی داخلی، DNS | ⛔ تست نشده |
| تست بار و همزمانی روی حجم واقعی | ⛔ انجام نشده |
| UAT با کاربران سازمان | ⛔ انجام نشده |
| انطباق با «شرح خدمات پیوست» | ⛔ پیوست در دسترس نبود؛ Scope طراحی مستقل است |
| دقت اعداد به‌عنوان دادهٔ سازمانی | ⛔ داده نمونه است؛ هیچ ادعای فروش واقعی نیست |

## ۷) بازتولید نتایج

```bash
python3 scripts/generate_all_data.py     # داده‌ها با seed=14030505 بازتولید می‌شوند
python3 model/etl_staging_to_dw.py       # همان ETL، همان خروجی
python3 -m unittest discover -s tests    # ۳۷ تست
```

جمع فروش به‌صورت تست (`test_total_sales_amount`) قفل شده تا تغییر ناخواستهٔ seed یا منطق
بلافاصله دیده شود.

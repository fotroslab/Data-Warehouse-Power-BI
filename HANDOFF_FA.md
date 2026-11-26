# هندآف پروژه ۵ — راهکار سازمانی: SQL Server + Data Warehouse + Power BI Report Server

> **تاریخ:** ۱۴۰۵/۰۹/۰۵ · **پوشه:** `project_05_sqlserver_reportserver/` ·
> **وضعیت:** کامل و اجراشده — اپ زنده روی پورت **۸۵۰۶** (این محیط)
> **واقعی یا نمونه؟** انبار دادهٔ **نمونه** (seed=14030505) + منطق **واقعی** (DDL T-SQL + ETL پایتون که
> واقعاً اجرا شد روی SQLite محلی). SQL Server / Report Server نصب، تست یا لایسنس نشده‌اند.

---

## ۱) مأموریت و معیار پذیرش

«سازمانی با شبکهٔ داخلی می‌خواهد از سیستم‌های عملیاتی‌اش یک DW استاراسکیما بسازد، کیفیت را با Reject
پایش کند و گزارش‌ها را روی Power BI Report Server داخلی منتشر کند — بدون ابر.» در غیاب پیوست
«شرح خدمات» و سرور واقعی، پروژه روی **معماری + اثبات منطق + راهنمای استقرار** متمرکز شد؛ هیچ ادعای
نصب/لایسنس/انتشار سازمانی نمی‌شود. فاقد `.pbix`.

## ۲) وضعیت نهایی تحویل (همه موجود ✅)

| تحویل | فایل |
|---|---|
| اپ ۵ صفحه‌ای | `app.py` (+ `.streamlit/config.toml`) |
| DDL کامل T-SQL | `model/schema.sql` |
| ETL اجراشده | `model/etl_staging_to_dw.py` → `model/dw_demo.sqlite` |
| مدل و سنجه‌ها | `model/MODEL.md` · `model/measures.dax` · `assets/model_diagram.svg` |
| گزارش/استقرار | `report/ARCHITECTURE.md` · `report/DEPLOYMENT_CHECKLIST.md` · `report/POWER_BI_BUILD_GUIDE.md` · `report/theme.json` |
| داده و مستندات آن | `data/*.csv` · `data/DATA_DICTIONARY.md` · `data/DATA_QUALITY_REPORT.md` |
| تست‌ها | `tests/test_data_quality.py` (۳۷ تست) |
| اسناد | `README_FA.md` · `PORTFOLIO_CASE_STUDY_EN.md` · `VALIDATION.md` · `LIMITATIONS.md` · `SOURCES.md` |
| اسکرین‌شات | `assets/preview.png` · `assets/preview_etl.png` · `assets/preview_sales.png` |
| اسکریپت‌های کمکی | `scripts/generate_all_data.py` · `scripts/make_model_diagram.py` · `scripts/make_preview.py` |

## ۳) منبع داده — دقیق و درست

هیچ دیتاست عملیاتی/سازمانی عمومی وجود ندارد. کل داده با `scripts/generate_all_data.py` و
`seed=14030505` تولید شده؛ واحد **ریال**؛ تقویم **شمسی** (jdatetime). `schema.sql` اصولاً T-SQL است
ولی روی سرور واقعی اجرا نشده؛ SQLite صرفاً **جایگزین محلی** برای اثبات منطق ETL است
(`model/dw_demo.sqlite`). هیچ ادعای سازمان واقعی وجود ندارد.

## ۴) پایپ‌لاین واقعی (اجراشده با خروجی)

```text
stg_sales_raw.csv (۳۰۰؛ تاریخ‌های 1403/12/12 و 2024/07/17 و 28-07-2024 و 2024-07-28؛
                   کامای هزارگان؛ فاصله‌های اضافه؛ تخفیف خالی)
  → etl_staging_to_dw.py: خوانده 300 | تمیز 300 | Reject 0
  → تبدیل تاریخ‌ها + حذف کاما + TRIM + تخفیف خالی→۰
  → dw_demo.sqlite: dim_date=366 | dim_region=12 | dim_product=80 | dim_customer=500
                    fact_sales=30,000 | fact_returns=2,000
  → کنترل جمع: sum(net_amount_irr) = 12,491,123,417,390 ریال (≈ ۱۲٫۴۹ همت)
```

فروش ۳۰٬۰۰۰ سند؛ ۱۲ منطقه؛ ۵۰۰ مشتری؛ ۸۰ کالا؛ ۲٬۰۰۰ مرجوعی؛ ۱۴۰۳ شمسی (+ معادل میلادی).

## ۵) مدل (ستاره‌ای، در `schema.sql`)

Schemas: `staging(stg)` → `dw`. جداول: `dim_date` (با `jalali_date_key`) · `dim_customer` ·
`dim_product` · `dim_region` · `fact_sales` · `fact_returns` · `etl_reject` · `etl_load_log` ·
`etl_batch_control`؛ ایندکس‌ها/کلیدها/CHECK. روابط بعد→فکت؛ یکتایی کلیدها تست شده.
**RLS** (مدیر منطقه فقط همان منطقه) فقط مستند است (`DimUserRegion`) و پیاده/تست نشده.
YTD شمسی با `jalali_date_key`؛ مرز سال مالی **نوروز فرض** شده.

## ۶) RTL / تم

تم «Enterprise DW Fa»؛ فونت Vazirmatn (woff2، به‌صورت data-URI در اپ)؛ اعداد فارسی؛ ریال؛
رنگ گرافیتی `#232b36` + قرمز `#d64541` روی `#f6f7f8`.

## ۷) اپ پیش‌نمایش — ۵ صفحه

نمای کلی انبار داده / **پایپ‌لاین زندهٔ ETL** / تحلیل فروش نمونه / استقرار و معماری / دربارهٔ داده

* صفحهٔ ETL با دکمه‌ای که واقعاً `model/etl_staging_to_dw.py` را با `subprocess` اجرا می‌کند و
  خروجی را نشان می‌دهد (۳۰۰/۳۰۰ تمیز؛ ۰ مردود) + جدول محتوای `dw_demo.sqlite`.
* فیلتر منطقه؛ نمودار فروش منطقه‌ای (برچسب‌های فارسی کامل — چارت‌ها `direction:ltr` شده‌اند)؛
  حاشیه‌ها از `style_fig(margin=...)`؛ برچسب میله‌ها `cliponaxis=False`؛ محورها به **همت / میلیارد ریال**.
* اجرا: `streamlit run app.py --server.port 8506 --server.address 0.0.0.0`

## ۸) تست‌ها و اعتبارسنجی

* `python3 -m unittest discover -s tests` — ✅ **۳۷ تست**: یکتایی کلیدها؛ FK فکت‌ها←ابعاد؛ جمع مبالغ
  (قفل‌شده روی `12_491_123_417_390`)؛ stg: هر ۴ فرمت تاریخ؛ تخفیف خالی→۰؛ کامای هزارگان.
* `python3 model/etl_staging_to_dw.py` — واقعی و موفق (لاگ در `VALIDATION.md`).
* AppTest هر ۵ صفحه بدون استثنا؛ کلیک برنامه‌ای روی دکمهٔ ETL و دریافت لاگ واقعی.
* تم JSON معتبر؛ XML نمودار مدل معتبر؛ فونت‌ها واقعی.
* **تست‌نشده (صادقانه):** اجرا روی SQL Server واقعی؛ نصب/پیکربندی Report Server، SSL، شبکه؛
  تست بار/همزمانی؛ UAT؛ انطباق با «شرح خدمات پیوست» (موجود نبود).

## ۹) نکاتی که ایجنت بعدی باید بداند

1. هیچ‌گاه «Report Server نصب است» ننویس؛ `schema.sql` قبل از اجرا نیازمند **DBA Review** است.
2. SQLite را «جایگزین محلی» بنام؛ پارتیشن‌بندی/Columnstore/آمار فقط در سرور واقعی معنا دارد.
3. Reject در نمونه **صفر** است — اگر کارفرما خواست جریان Reject را ببیند، چند ردیف نامعتبر
   (تاریخ `1403/13/45`، مبلغ `abc`، منطقهٔ `R99`) دستی به `data/stg_sales_raw.csv` تزریق کنید.
4. RLS فقط مستند است؛ بدون View-as تست نشده.
5. برچسب‌های «مصنوعی/synthetic» را دوباره به تیترها اضافه نکنید — پروژه عمداً «خوبِ نمونهٔ استقرار»
   معرفی می‌شود، ولی اعدادش واقعی نیستند (این در `LIMITATIONS.md` و بنر هر صفحه قید شده؛ همان بماند).
6. اگر `preview.png` را دوباره ساختید: viewport ≥ `۱۵۰۰×۱۷۵۰`؛ `.js-plotly-plot{direction:ltr}`؛
   `margin` از `style_fig`؛ `cliponaxis=False`. **هرگز `direction="rtl"` روی ریشهٔ SVG نگذارید**
   (با `text-anchor="end"` متن از کادر بیرون می‌زند — درس گرفته‌شده، در `make_model_diagram.py` مستند است).
7. جمع فروش در تست قفل شده؛ اگر seed یا منطق داده عوض شد، تست عمداً می‌شکند — آن را با اعداد
   جدید و توضیح به‌روزرسانی کنید، نه با حذف تست.

## ۱۰) محدودیت‌های کلیدی (خلاصهٔ `LIMITATIONS.md` — ۲۱ آیتم)

بدون زیرساخت واقعی؛ `schema.sql` روی سرور اجرا نشده؛ SQLite جایگزین محلی؛ stg کوچک (۳۰۰) و
Reject=۰؛ RLS فقط مستند؛ YTD وابسته به `dim_date` پروژه و فرض نوروز؛ DAX بدون `.pbix` اجرا نشده؛
هیچ ROI/بهره‌وری ادعا نمی‌شود؛ لایسنس Report Server الزامی است؛ `.pbix` وجود ندارد.

## ۱۱) کارهای بعدی منطقی

تهیهٔ «شرح خدمات» واقعی و بازنویسی Scope → دریافت دسترسی SQL Server → اجرای `schema.sql` با DBA →
ETL با SSIS/پایتون روی سرور → نصب Report Server + لایسنس + SSL + DNS → ساخت `.pbix` و Publish →
View-as (RLS) → تست بار + UAT → بستن آیتم‌های `LIMITATIONS.md` یکی‌یکی.

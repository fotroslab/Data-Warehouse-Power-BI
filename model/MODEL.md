# مدل داده (MODEL.md) — استاراسکیما

> وضعیت: طراحی کامل و مستند. DDL در [`schema.sql`](schema.sql) به‌صورت T-SQL نوشته شده ولی
> **روی SQL Server واقعی اجرا نشده** (نیازمند DBA Review). منطق ETL در `etl_staging_to_dw.py`
> واقعاً اجرا شده و خروجی آن `dw_demo.sqlite` است — جایگزین محلی، نه SQL Server.

## ۱) نگاه کلی

```text
سیستم‌های عملیاتی (ERP / فروش / CRM)
        │  استخراج فایل/CDC (در استقرار واقعی: SSIS یا پایتون روی سرور)
        ▼
   stg.sales_raw            ←  ورودی خام، بدون تغییر (۳۰۰ ردیف عمداً کثیف)
        │  پاک‌سازی و اعتبارسنجی  (model/etl_staging_to_dw.py  ⟷  SP/SSIS)
        ├── نامعتبر ──▶  dw.etl_reject   (stage, reason, raw_payload, batch)
        ▼
   dw.stg_sales_cleaned  →  dw.dim_*  /  dw.fact_*
        │
        ▼
  Power BI Report Server (Import mode)  →  گزارش‌های RTL
```

## ۲) ابعاد (Conformed Dimensions)

| جدول | کلید | ردیف نمونه | نقش |
|---|---|---:|---|
| `dw.dim_date` | `date_key` (YYYYMMDD شمسی) | ۳۶۶ | تقویم؛ شامل `jalali_date_key`، فصل، روز هفته، تعطیلی جمعه |
| `dw.dim_customer` | `customer_id` | ۵۰۰ | مشتری حقیقی/حقوقی + کانال + `region_id` (FK) |
| `dw.dim_product` | `product_id` | ۸۰ | کالا، دسته، قیمت فهرست و بهای تمام‌شده |
| `dw.dim_region` | `region_id` | ۱۲ | منطقه/پهنهٔ جغرافیایی |

## ۳) فکت‌ها

| جدول | دانه (Grain) | ردیف نمونه | کلیدهای خارجی |
|---|---|---:|---|
| `dw.fact_sales` | یک سطر = یک قلم فروش (`sale_id`) | ۳۰٬۰۰۰ | date, customer, product, region |
| `dw.fact_returns` | یک سطر = یک مرجوعی (`return_id`) | ۲٬۰۰۰ | **sale_id** + date, customer, product, region |

`fact_sales` از نوع **transaction fact** است؛ `region_id` به‌صورت denormalized هم در فکت آمده تا
گزارش‌های منطقه‌ای بدون join سنگین اجرا شوند (کنترل هم‌خوانی با منطقهٔ مشتری در تست‌ها).

## ۴) روابط

```text
dim_date    1 ──── *  fact_sales      (date_key)
dim_customer 1 ──── *  fact_sales      (customer_id)
dim_product  1 ──── *  fact_sales      (product_id)
dim_region   1 ──── *  fact_sales      (region_id)
dim_region   1 ──── *  dim_customer    (region_id)
fact_sales   1 ──── *  fact_returns    (sale_id)   ← مرجوعی به سند مبدأ
```

در Power BI این‌ها رابطهٔ **یک‌به‌چند، فیلتر یک‌طرفه** از ابعاد به فکت هستند.
`dim_date` باید Mark as Date Table روی `gregorian_date` شود.

## ۵) تقویم شمسی

* `date_key` = `جalali_date_key` = عددی `YYYYMMDD` شمسی (مثلاً ۱۴۰۳/۱۲/۱۲ → `14031212`).
* `gregorian_date` برای سازگاری با توابع تاریخ DAX و SQL.
* سال مالی = سال شمسی؛ `fiscal_period` = `1403-08`. مرز سال مالی **نوروز فرض شده** است؛ اگر
  سازمان سال مالی دیگری دارد باید در `dim_date` و `measures.dax` اصلاح شود.
* تعطیلی رسمی نمونه: جمعه (`is_weekend = 1`). تعطیلات متغیر (عیدها) در نمونه لحاظ نشده‌اند.

## ۶) جریان Reject

| ستون | معنا |
|---|---|
| `reject_stage` | `DATE_PARSE` / `NUMERIC_PARSE` / `DIM_LOOKUP` / `CONSTRAINT` / `DUPLICATE` |
| `reject_reason` | توضیح فارسی/فنی علت |
| `raw_payload` | ردیف خام به‌صورت JSON برای بررسی دستی |
| `load_batch_id` | ارجاع به `etl_load_log` و `etl_batch_control` |

در نمونهٔ فعلی **۰ ردیف Reject** وجود دارد، چون همهٔ فرمت‌های تاریخ در دادهٔ staging قابل تبدیل‌اند.
برای نمایش جریان Reject باید چند ردیف نامعتبر (تاریخ `1403/13/45`، مبلغ `abc`، منطقهٔ `R99`)
به فایل staging تزریق شود — مسیر کد آماده است و تست جداگانه دارد.

## ۷) سنجه‌ها

فایل [`measures.dax`](measures.dax): فروش خالص/ناخالص، حاشیهٔ سود، نرخ تخفیف، مرجوعی،
YTD/MTD شمسی، MoM/YoY، رتبه و سهم منطقه، ABC کالا، نرخ Reject.

## ۸) تصمیم‌های طراحی و دلیل‌ها

| تصمیم | دلیل | هزینه/ریسک |
|---|---|---|
| تقویم شمسی به‌عنوان کلید اصلی | الزام گزارش‌های فارسی | ابزارهای میلادی‌محور نیاز به ستون میلادی دارند (فراهم شده) |
| Import mode | سادگی استقرار روی Report Server داخلی و کارایی گزارش | نیاز به زمان‌بندی Refresh |
| denormalize `channel_fa` و `region_id` در فکت | کاهش join و ساده‌سازی RLS منطقه‌ای | تکرار داده، نیاز به کنترل سازگاری |
| Reject در DW نه در فایل | قابل گزارش‌گیری و پیگیری توسط تیم داده | نیاز به نگهداشت/پاک‌سازی دوره‌ای جدول |
| staging به‌صورت `TRUNCATE/RESTORE` هر بار | سادگی و idempotent | برای حجم بالا باید incremental شود |

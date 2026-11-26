# فرهنگ داده (Data Dictionary) — DW نمونه
> واحد پول: **ریال** | تقویم: **شمسی 1403** + معادل میلادی | seed=14030505 | تمام داده نمونه است.

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

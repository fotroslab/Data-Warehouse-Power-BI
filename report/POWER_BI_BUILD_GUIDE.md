# راهنمای ساخت گزارش در Power BI Report Server

> این راهنما *مسیر ساخت* است. فایل `.pbix` در این پروژه **ساخته نشده** و هیچ گزارشی روی
> Report Server منتشر نشده است (Report Server نصب نیست). نسخهٔ Report Server از قابلیت‌های
> Power BI Desktop محدودتر است؛ همیشه از نسخهٔ «Power BI Desktop (Report Server)» استفاده کنید.

## ۱) آماده‌سازی اتصال

1. `Power BI Desktop (optimized for Report Server)` را نصب کنید (نسخهٔ آن باید با نسخهٔ سرور
   سازگار باشد).
2. `Get Data → SQL Server`:
   * Server: `sql-dw.org.local`
   * Database: `DWSales`
   * Data Connectivity mode: **Import** (توصیه‌شده)
3. جداول را انتخاب کنید: `dim_date`, `dim_customer`, `dim_product`, `dim_region`,
   `fact_sales`, `fact_returns` (و برای داشبورد کیفیت: `etl_reject`, `etl_load_log`).

## ۲) مدل

1. روابط را بررسی کنید: از هر بعد به فکت، **یک‌به‌چند**، جهت فیلتر **Single**.
2. `dim_date` → راست‌کلیک → **Mark as date table** روی `gregorian_date`.
   (کلید تاریخِ گزارش‌ها `jalali_date_key` است.)
3. ستون‌های غیرلازم را Hide کنید (کلیدهای فنی)، ستون‌های فارسی را با نام نمایشی مناسب rename کنید.
4. مرتب‌سازی: `month_name_fa` را با ستون `month` مرتب کنید (Sort by column) تا «فروردین…اسفند»
   درست مرتب شود. همین کار برای `weekday_fa` با `day_of_week`.
5. سنجه‌ها را از `model/measures.dax` بسازید. قالب اعداد را روی **ریال** با جداکنندهٔ هزارگان
   فارسی تنظیم کنید و در Model view واحد را «ریال» بگذارید.

## ۳) RTL و قالب‌بندی

1. `assets/fonts` → فونت Vazirmatn را نصب کنید (یا در تم تعبیه کنید).
2. `report/theme.json` («Enterprise DW Fa») را از `View → Themes → Browse for themes` بارگذاری کنید:
   * پس‌زمینهٔ `#f6f7f8`، رنگ اصلی گرافیتی `#232b36`، لهجهٔ قرمز `#d64541`
3. برای هر بصری‌سازی، در Format:
   * Title → Alignment: راست
   * X/Y axis → Text direction: راست‌به‌چپ (در نسخه‌هایی که پشتیبانی می‌شود)
   * Legend → Position: بالا/راست
4. اعداد را با `Format → Custom` به شکل `#,0` نمایش دهید؛ واحد را در عنوان بنویسید («ریال»).
5. صفحات پیشنهادی: **خلاصهٔ مدیریتی**، **فروش منطقه‌ای**، **کالا و دسته**، **مرجوعی**،
   **کیفیت داده (Reject)** — هرکدام با فیلتر تاریخ شمسی و منطقه.

## ۴) KPIهای پیشنهادی صفحهٔ اول

| KPI | سنجهٔ DAX | نمایش |
|---|---|---|
| فروش خالص | `[SUM Sales Net]` | کارت + روند ماهانه |
| حاشیهٔ سود | `[Gross Margin %]` | گیج/کارت |
| نرخ مرجوعی | `[Return Rate %]` | کارت با هدف |
| رشد نسبت به سال قبل | `[Sales YoY %]` | کارت با فلش |
| فروش YTD شمسی | `[Sales YTD]` | کارت |
| نرخ Reject | `[Reject Rate %]` | کارت هشدار |

## ۵) RLS منطقه‌ای (فقط دستور کار — پیاده نشده)

```dax
-- روی fact_sales (یا dim_region)
[region_id] =
LOOKUPVALUE (
    DimUserRegion[region_id],
    DimUserRegion[user_principal], USERPRINCIPALNAME ()
)
```

1. جدول نگاشت `DimUserRegion(user_principal, region_id)` را در دیتابیس بسازید و پر کنید.
2. `Modeling → Manage roles` → نقش `RegionManager` با فیلتر بالا.
3. نقش `NationalViewer` بدون فیلتر.
4. تست با `Modeling → View as` برای هر نقش — **قبل از انتشار الزامی**.
5. روی Report Server، نقش‌ها را به گروه‌های AD نگاشت کنید.

> در این پروژه RLS **فقط مستند** است: نه فایل `.pbix` وجود دارد، نه `DimUserRegion` ساخته شده،
> نه تست View-as انجام شده.

## ۶) انتشار

1. `File → Publish → Power BI Report Server` با آدرس `https://bi.org.local/reports`.
2. پوشهٔ `Sales DW` بسازید و گزارش را با نام فارسی منتشر کنید.
3. برای Dataset: `Manage → Scheduled refresh` (مثلاً هر شب ۰۲:۰۰).
4. نقش‌های Portal را تنظیم کنید: `Browser` برای مصرف‌کننده، `Publisher` برای تیم BI.
5. لینک گزارش را در پورتال داخلی منتشر کنید.

## ۷) آنچه در این پروژه تست نشده

* ساخت و اعتبارسنجی خودِ `.pbix`
* Refresh زمان‌بندی‌شده روی Report Server
* View-as و کارکرد RLS
* سازگاری تم JSON با نسخهٔ نصب‌شده (تم معتبر JSON است ولی روی Report Server آزموده نشده)
* رفتار فونت Vazirmatn در مرورگرهای سازمان

/* =====================================================================================
   PROJ-05 / schema.sql
   انبار دادهٔ استاراسکیما برای SQL Server  —  «بدون ابر»
   -------------------------------------------------------------------------------------
   !! هشدار صداقت: این فایل روی هیچ نمونهٔ SQL Server واقعی اجرا نشده است. پیش از اجرا
      در محیط سازمان لازم است DBA آن را Review کند (کالیشن، فایل‌گروپ، رمزنگاری،
      سیاست بکاپ/نگهداشت، سطح سازگاری). تست‌شده فقط از نظر ساختار منطقی و از طریق
      بازتولید همان منطق روی SQLite (model/etl_staging_to_dw.py) است.
   -------------------------------------------------------------------------------------
   طراحی: دو Schema
       stg  → ورودی خام (نگهداری موقت، TRUNCATE هر بار)
       dw   → ابعاد، فکت‌ها، جدول Reject و کنترل بار
   اصول: idempotent (چند بار اجرا شود بی‌خطا)، کلیدهای اصلی/خارجی، CHECK، ایندکس روی
         کلیدهای تاریخ/ابعاد، تقویم شمسی با jalali_date_key.
   اجرا:  sqlcmd -S <server> -d <db> -i model/schema.sql
   ===================================================================================== */

SET NOCOUNT ON;
SET XACT_ABORT ON;
GO

/* ------------------------------------------------------------------ 0) Schemas */
IF SCHEMA_ID(N'stg') IS NULL EXEC(N'CREATE SCHEMA stg AUTHORIZATION dbo;');
IF SCHEMA_ID(N'dw')  IS NULL EXEC(N'CREATE SCHEMA dw  AUTHORIZATION dbo;');
GO

/* ------------------------------------------------------------------ 1) staging */
IF OBJECT_ID(N'stg.sales_raw', N'U') IS NULL
BEGIN
    CREATE TABLE stg.sales_raw (
        row_id              INT             NOT NULL,
        sale_ref            NVARCHAR(20)    NULL,
        sale_date_raw       NVARCHAR(30)    NULL,   -- فرمت‌های مختلط: 1403/12/12 | 2024/07/17 | 28-07-2024 | 2024-07-28
        customer_name_raw   NVARCHAR(150)   NULL,
        product_name_raw    NVARCHAR(150)   NULL,
        region_id_raw       NVARCHAR(10)    NULL,
        quantity_raw        NVARCHAR(20)    NULL,
        unit_price_raw      NVARCHAR(30)    NULL,   -- کامای هزارگان
        discount_raw        NVARCHAR(10)    NULL,   -- خالی = ۰
        load_batch_id       UNIQUEIDENTIFIER NOT NULL
            CONSTRAINT df_stg_sales_batch DEFAULT NEWID(),
        loaded_at           DATETIME2(0)    NOT NULL
            CONSTRAINT df_stg_sales_loaded DEFAULT SYSUTCDATETIME(),
        CONSTRAINT pk_stg_sales_raw PRIMARY KEY CLUSTERED (row_id)
    );
END;
GO

/* ------------------------------------------------------------------ 2) rejection */
IF OBJECT_ID(N'dw.etl_reject', N'U') IS NULL
BEGIN
    CREATE TABLE dw.etl_reject (
        reject_id           BIGINT IDENTITY(1,1) NOT NULL,
        source_table        SYSNAME        NOT NULL CONSTRAINT df_reject_source DEFAULT N'stg.sales_raw',
        source_row_id       INT            NULL,
        reject_stage        VARCHAR(40)    NOT NULL,   -- DATE_PARSE | NUMERIC_PARSE | DIM_LOOKUP | CONSTRAINT | DUPLICATE
        reject_reason       NVARCHAR(400)  NOT NULL,
        raw_payload         NVARCHAR(MAX)  NULL,       -- ردیف خام به شکل JSON برای بررسی دستی
        load_batch_id       UNIQUEIDENTIFIER NULL,
        rejected_at         DATETIME2(0)   NOT NULL CONSTRAINT df_reject_at DEFAULT SYSUTCDATETIME(),
        resolved_by         NVARCHAR(100)  NULL,
        resolved_at         DATETIME2(0)   NULL,
        CONSTRAINT pk_etl_reject PRIMARY KEY CLUSTERED (reject_id)
    );
    CREATE NONCLUSTERED INDEX ix_etl_reject_stage ON dw.etl_reject (reject_stage, rejected_at DESC);
END;
GO

/* ------------------------------------------------------------------ 3) dim_date */
IF OBJECT_ID(N'dw.dim_date', N'U') IS NULL
BEGIN
    CREATE TABLE dw.dim_date (
        date_key            INT           NOT NULL,              -- YYYYMMDD شمسی، مثلاً 14031212
        jalali_date         CHAR(10)      NOT NULL,              -- 1403/12/12
        jalali_date_key     INT           NOT NULL,              -- عمداً همان date_key؛ برای Time Intelligence شمسی
        gregorian_date      DATE          NOT NULL,              -- 2025-03-02
        [year]              SMALLINT      NOT NULL,
        [month]             TINYINT       NOT NULL,
        month_name_fa       NVARCHAR(20)  NOT NULL,
        [day]               TINYINT       NOT NULL,
        [quarter]           TINYINT       NOT NULL,
        season_fa           NVARCHAR(10)  NOT NULL,
        day_of_week         TINYINT       NOT NULL,              -- 0=شنبه … 6=جمعه
        weekday_fa          NVARCHAR(20)  NOT NULL,
        is_weekend          BIT           NOT NULL CONSTRAINT df_dimdate_weekend DEFAULT 0,
        is_month_start      BIT           NOT NULL CONSTRAINT df_dimdate_mstart DEFAULT 0,
        fiscal_year         SMALLINT      NOT NULL,
        fiscal_period       CHAR(7)       NOT NULL,              -- 1403-08
        CONSTRAINT pk_dim_date PRIMARY KEY CLUSTERED (date_key),
        CONSTRAINT uq_dim_date_jalali UNIQUE (jalali_date),
        CONSTRAINT uq_dim_date_greg UNIQUE (gregorian_date),
        CONSTRAINT ck_dimdate_month CHECK ([month] BETWEEN 1 AND 12),
        CONSTRAINT ck_dimdate_day   CHECK ([day]   BETWEEN 1 AND 31),
        CONSTRAINT ck_dimdate_quarter CHECK ([quarter] BETWEEN 1 AND 4),
        CONSTRAINT ck_dimdate_dow   CHECK (day_of_week BETWEEN 0 AND 6),
        CONSTRAINT ck_dimdate_jkey  CHECK (jalali_date_key = date_key),
        CONSTRAINT ck_dimdate_fiscal CHECK (fiscal_year = [year])
    );
    CREATE NONCLUSTERED INDEX ix_dim_date_month ON dw.dim_date ([year], [month]);
    CREATE NONCLUSTERED INDEX ix_dim_date_greg  ON dw.dim_date (gregorian_date);
END;
GO

/* ------------------------------------------------------------------ 4) dim_region */
IF OBJECT_ID(N'dw.dim_region', N'U') IS NULL
BEGIN
    CREATE TABLE dw.dim_region (
        region_id        NVARCHAR(5)    NOT NULL,
        region_name_fa   NVARCHAR(60)   NOT NULL,
        region_code_fa   NVARCHAR(20)   NOT NULL,
        zone_fa          NVARCHAR(30)   NOT NULL,
        CONSTRAINT pk_dim_region PRIMARY KEY CLUSTERED (region_id),
        CONSTRAINT uq_dim_region_name UNIQUE (region_name_fa)
    );
END;
GO

/* ------------------------------------------------------------------ 5) dim_customer */
IF OBJECT_ID(N'dw.dim_customer', N'U') IS NULL
BEGIN
    CREATE TABLE dw.dim_customer (
        customer_id      NVARCHAR(10)   NOT NULL,
        customer_name_fa NVARCHAR(150)  NOT NULL,
        segment_fa       NVARCHAR(20)   NOT NULL,
        channel_fa       NVARCHAR(30)   NOT NULL,
        region_id        NVARCHAR(5)    NOT NULL,
        created_date     CHAR(10)       NULL,
        is_active        BIT            NOT NULL CONSTRAINT df_dimcust_active DEFAULT 1,
        CONSTRAINT pk_dim_customer PRIMARY KEY CLUSTERED (customer_id),
        CONSTRAINT fk_dimcust_region FOREIGN KEY (region_id) REFERENCES dw.dim_region (region_id),
        CONSTRAINT ck_dimcust_segment CHECK (segment_fa IN (N'حقیقی', N'حقوقی')),
        CONSTRAINT ck_dimcust_channel CHECK (channel_fa IN (N'فروش مستقیم', N'نمایندگی', N'فروش آنلاین'))
    );
    CREATE NONCLUSTERED INDEX ix_dim_customer_region ON dw.dim_customer (region_id) INCLUDE (customer_name_fa);
END;
GO

/* ------------------------------------------------------------------ 6) dim_product */
IF OBJECT_ID(N'dw.dim_product', N'U') IS NULL
BEGIN
    CREATE TABLE dw.dim_product (
        product_id       NVARCHAR(10)   NOT NULL,
        product_name_fa  NVARCHAR(150)  NOT NULL,
        category_id      NVARCHAR(10)   NOT NULL,
        category_name_fa NVARCHAR(60)   NOT NULL,
        unit_price_irr   BIGINT         NOT NULL,
        unit_cost_irr    BIGINT         NOT NULL,
        is_active        BIT            NOT NULL CONSTRAINT df_dimprod_active DEFAULT 1,
        CONSTRAINT pk_dim_product PRIMARY KEY CLUSTERED (product_id),
        CONSTRAINT ck_dimprod_price CHECK (unit_price_irr  > 0),
        CONSTRAINT ck_dimprod_cost  CHECK (unit_cost_irr   > 0),
        CONSTRAINT ck_dimprod_margin CHECK (unit_cost_irr < unit_price_irr)
    );
    CREATE NONCLUSTERED INDEX ix_dim_product_category ON dw.dim_product (category_id) INCLUDE (product_name_fa);
END;
GO

/* ------------------------------------------------------------------ 7) fact_sales */
IF OBJECT_ID(N'dw.fact_sales', N'U') IS NULL
BEGIN
    CREATE TABLE dw.fact_sales (
        sale_id           NVARCHAR(12)  NOT NULL,
        date_key          INT           NOT NULL,
        customer_id       NVARCHAR(10)  NOT NULL,
        product_id        NVARCHAR(10)  NOT NULL,
        region_id         NVARCHAR(5)   NOT NULL,
        channel_fa        NVARCHAR(30)  NOT NULL,
        quantity          INT           NOT NULL,
        unit_price_irr    BIGINT        NOT NULL,
        unit_cost_irr     BIGINT        NOT NULL,
        discount_pct      DECIMAL(5,2)  NOT NULL CONSTRAINT df_factsale_disc DEFAULT (0),
        gross_amount_irr  BIGINT        NOT NULL,
        net_amount_irr    BIGINT        NOT NULL,
        cost_amount_irr   BIGINT        NOT NULL,
        CONSTRAINT pk_fact_sales PRIMARY KEY CLUSTERED (sale_id),
        CONSTRAINT fk_factsale_date     FOREIGN KEY (date_key)    REFERENCES dw.dim_date (date_key),
        CONSTRAINT fk_factsale_customer FOREIGN KEY (customer_id) REFERENCES dw.dim_customer (customer_id),
        CONSTRAINT fk_factsale_product  FOREIGN KEY (product_id)  REFERENCES dw.dim_product (product_id),
        CONSTRAINT fk_factsale_region   FOREIGN KEY (region_id)   REFERENCES dw.dim_region (region_id),
        CONSTRAINT ck_factsale_qty    CHECK (quantity > 0),
        CONSTRAINT ck_factsale_disc   CHECK (discount_pct BETWEEN 0 AND 1),
        CONSTRAINT ck_factsale_net    CHECK (net_amount_irr > 0),
        CONSTRAINT ck_factsale_gross  CHECK (gross_amount_irr = quantity * unit_price_irr),
        CONSTRAINT ck_factsale_calc   CHECK (net_amount_irr = CAST(gross_amount_irr * (1 - discount_pct) AS BIGINT)),
        CONSTRAINT ck_factsale_cost   CHECK (cost_amount_irr = quantity * unit_cost_irr)
    );
    CREATE NONCLUSTERED INDEX ix_factsales_date     ON dw.fact_sales (date_key) INCLUDE (net_amount_irr, quantity);
    CREATE NONCLUSTERED INDEX ix_factsales_customer ON dw.fact_sales (customer_id) INCLUDE (net_amount_irr);
    CREATE NONCLUSTERED INDEX ix_factsales_product  ON dw.fact_sales (product_id) INCLUDE (net_amount_irr, quantity);
    CREATE NONCLUSTERED INDEX ix_factsales_region   ON dw.fact_sales (region_id, date_key) INCLUDE (net_amount_irr);
END;
GO

/* ------------------------------------------------------------------ 8) fact_returns */
IF OBJECT_ID(N'dw.fact_returns', N'U') IS NULL
BEGIN
    CREATE TABLE dw.fact_returns (
        return_id         NVARCHAR(12)  NOT NULL,
        sale_id           NVARCHAR(12)  NOT NULL,
        date_key          INT           NOT NULL,
        customer_id       NVARCHAR(10)  NOT NULL,
        product_id        NVARCHAR(10)  NOT NULL,
        region_id         NVARCHAR(5)   NOT NULL,
        quantity_returned INT           NOT NULL,
        return_amount_irr BIGINT        NOT NULL,
        reason_fa         NVARCHAR(60)  NOT NULL,
        CONSTRAINT pk_fact_returns PRIMARY KEY CLUSTERED (return_id),
        CONSTRAINT fk_factret_sale     FOREIGN KEY (sale_id)     REFERENCES dw.fact_sales (sale_id),
        CONSTRAINT fk_factret_date     FOREIGN KEY (date_key)    REFERENCES dw.dim_date (date_key),
        CONSTRAINT fk_factret_customer FOREIGN KEY (customer_id) REFERENCES dw.dim_customer (customer_id),
        CONSTRAINT fk_factret_product  FOREIGN KEY (product_id)  REFERENCES dw.dim_product (product_id),
        CONSTRAINT fk_factret_region   FOREIGN KEY (region_id)   REFERENCES dw.dim_region (region_id),
        CONSTRAINT ck_factret_qty   CHECK (quantity_returned > 0),
        CONSTRAINT ck_factret_amt   CHECK (return_amount_irr > 0)
    );
    CREATE NONCLUSTERED INDEX ix_factret_date ON dw.fact_returns (date_key) INCLUDE (return_amount_irr);
END;
GO

/* ------------------------------------------------------------------ 9) load audit */
IF OBJECT_ID(N'dw.etl_load_log', N'U') IS NULL
BEGIN
    CREATE TABLE dw.etl_load_log (
        load_id         BIGINT IDENTITY(1,1) NOT NULL,
        load_batch_id   UNIQUEIDENTIFIER NOT NULL,
        stage_name      VARCHAR(60)      NOT NULL,
        rows_read       INT              NOT NULL CONSTRAINT df_loadlog_read   DEFAULT 0,
        rows_clean      INT              NOT NULL CONSTRAINT df_loadlog_clean  DEFAULT 0,
        rows_reject     INT              NOT NULL CONSTRAINT df_loadlog_reject DEFAULT 0,
        started_at      DATETIME2(0)     NOT NULL,
        finished_at     DATETIME2(0)     NULL,
        status          VARCHAR(20)      NOT NULL CONSTRAINT df_loadlog_status DEFAULT 'RUNNING',
        message         NVARCHAR(400)    NULL,
        CONSTRAINT pk_etl_load_log PRIMARY KEY CLUSTERED (load_id),
        CONSTRAINT ck_loadlog_counts CHECK (rows_read >= 0 AND rows_clean >= 0 AND rows_reject >= 0),
        CONSTRAINT ck_loadlog_balance CHECK (rows_clean + rows_reject <= rows_read),
        CONSTRAINT ck_loadlog_status CHECK (status IN ('RUNNING','SUCCESS','PARTIAL','FAILED'))
    );
END;
GO

/* ------------------------------------------------------------------ 10) کارگزار کنترل بار (نمونه، اختیاری)
   جلوگیری از دوباره‌شماری در بارهای تکراری: هر بستهٔ بار یک‌بار پردازش می‌شود. */
IF OBJECT_ID(N'dw.etl_batch_control', N'U') IS NULL
BEGIN
    CREATE TABLE dw.etl_batch_control (
        load_batch_id   UNIQUEIDENTIFIER NOT NULL CONSTRAINT pk_etl_batch_control PRIMARY KEY,
        source_file     NVARCHAR(260)    NOT NULL,
        file_hash       CHAR(64)         NOT NULL,   -- SHA-256 فایل ورودی
        processed_at    DATETIME2(0)     NOT NULL CONSTRAINT df_batch_at DEFAULT SYSUTCDATETIME(),
        status          VARCHAR(20)      NOT NULL CONSTRAINT df_batch_status DEFAULT 'DONE'
    );
END;
GO

/* ------------------------------------------------------------------ 11) RLS — فقط مستند
   نقش‌ها: dw_reader (SELECT روی dw)، dw_etl (INSERT/UPDATE روی stg و dw)
   مورد «مدیر منطقه فقط همان منطقه» با جدول نگاشت DimUserRegion پیاده می‌شود اما در این
   پروژه فقط *مستند* است و پیاده/تست نشده (بدون Security Policy و بدون View-as). */

/* ------------------------------------------------------------------ 12) کنترل پذیرش پس از بار (نمونهٔ کوئری) */
-- SELECT COUNT(*) AS n_sales, SUM(net_amount_irr) AS total_net FROM dw.fact_sales;
-- SELECT reject_stage, COUNT(*) FROM dw.etl_reject GROUP BY reject_stage;
GO
PRINT N'schema.sql اجرا شد: stg.sales_raw + dw.* (ابعاد، فکت‌ها، Reject، لاگ بار).';
GO

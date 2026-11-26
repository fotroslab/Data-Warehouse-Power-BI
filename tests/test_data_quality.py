#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست‌های کیفیت داده و منطق ETL — پروژهٔ ۵
اجرا از ریشهٔ مخزن:
    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "model"
sys.path.insert(0, str(MODEL_DIR))

import etl_staging_to_dw as etl  # noqa: E402


def load(name: str, keep_default_na: bool = True) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"{name}.csv", encoding="utf-8-sig",
                       keep_default_na=keep_default_na)


class TestDimensions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.date = load("dim_date")
        cls.region = load("dim_region")
        cls.product = load("dim_product")
        cls.customer = load("dim_customer")

    def test_row_counts(self):
        self.assertEqual(len(self.date), 366)
        self.assertEqual(len(self.region), 12)
        self.assertEqual(len(self.product), 80)
        self.assertEqual(len(self.customer), 500)

    def test_primary_key_uniqueness(self):
        self.assertEqual(self.date["date_key"].duplicated().sum(), 0)
        self.assertEqual(self.date["jalali_date"].duplicated().sum(), 0)
        self.assertEqual(self.date["gregorian_date"].duplicated().sum(), 0)
        self.assertEqual(self.region["region_id"].duplicated().sum(), 0)
        self.assertEqual(self.product["product_id"].duplicated().sum(), 0)
        self.assertEqual(self.customer["customer_id"].duplicated().sum(), 0)

    def test_no_nulls_in_keys(self):
        self.assertFalse(self.date["date_key"].isna().any())
        self.assertFalse(self.product["product_id"].isna().any())
        self.assertFalse(self.customer["region_id"].isna().any())

    def test_jalali_date_key_matches_date_key(self):
        self.assertTrue((self.date["jalali_date_key"] == self.date["date_key"]).all())

    def test_date_key_format(self):
        s = self.date["date_key"].astype(str)
        self.assertTrue(s.str.match(r"^1403(0[1-9]|1[0-2])[0-3][0-9]$").all())

    def test_calendar_covers_year(self):
        self.assertEqual(self.date["month"].min(), 1)
        self.assertEqual(self.date["month"].max(), 12)
        # شش ماه اول ۳۱ روز، شش ماه دوم ۳۰ روز + اسفند ۳۰ (سال کبیسه نیست)
        counts = self.date.groupby("month").size().to_dict()
        for m in range(1, 7):
            self.assertEqual(counts[m], 31, f"ماه {m}")
        self.assertEqual(counts[12], 30)

    def test_weekend_flag(self):
        fri = self.date[self.date["weekday_fa"] == "جمعه"]
        self.assertTrue((fri["is_weekend"] == 1).all())
        self.assertEqual(int(self.date["is_weekend"].sum()), len(fri))

    def test_product_margin_positive(self):
        self.assertTrue((self.product["unit_cost_irr"] < self.product["unit_price_irr"]).all())
        self.assertTrue((self.product["unit_price_irr"] > 0).all())

    def test_customer_region_fk(self):
        self.assertTrue(self.customer["region_id"].isin(self.region["region_id"]).all())

    def test_customer_segment_values(self):
        self.assertTrue(set(self.customer["segment_fa"]) <= {"حقیقی", "حقوقی"})


class TestFacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sales = load("fact_sales")
        cls.returns = load("fact_returns")
        cls.date = load("dim_date")
        cls.region = load("dim_region")
        cls.product = load("dim_product")
        cls.customer = load("dim_customer")

    def test_row_counts(self):
        self.assertEqual(len(self.sales), 30_000)
        self.assertEqual(len(self.returns), 2_000)

    def test_primary_key_uniqueness(self):
        self.assertEqual(self.sales["sale_id"].duplicated().sum(), 0)
        self.assertEqual(self.returns["return_id"].duplicated().sum(), 0)

    def test_foreign_keys(self):
        self.assertEqual((~self.sales["date_key"].isin(self.date["date_key"])).sum(), 0)
        self.assertEqual((~self.sales["customer_id"].isin(self.customer["customer_id"])).sum(), 0)
        self.assertEqual((~self.sales["product_id"].isin(self.product["product_id"])).sum(), 0)
        self.assertEqual((~self.sales["region_id"].isin(self.region["region_id"])).sum(), 0)
        self.assertEqual((~self.returns["sale_id"].isin(self.sales["sale_id"])).sum(), 0)
        self.assertEqual((~self.returns["date_key"].isin(self.date["date_key"])).sum(), 0)

    def test_no_nulls_in_measures(self):
        cols = ["quantity", "unit_price_irr", "discount_pct",
                "gross_amount_irr", "net_amount_irr", "cost_amount_irr"]
        self.assertFalse(self.sales[cols].isna().any().any())

    def test_amount_recalculation(self):
        calc = (self.sales["quantity"] * self.sales["unit_price_irr"]
                * (1 - self.sales["discount_pct"])).round()
        mismatch = (calc.astype("int64") != self.sales["net_amount_irr"]).sum()
        self.assertEqual(mismatch, 0)

    def test_gross_equals_qty_times_price(self):
        self.assertTrue((self.sales["gross_amount_irr"]
                         == self.sales["quantity"] * self.sales["unit_price_irr"]).all())

    def test_cost_equals_qty_times_unit_cost(self):
        self.assertTrue((self.sales["cost_amount_irr"]
                         == self.sales["quantity"] * self.sales["unit_cost_irr"]).all())

    def test_positive_measures(self):
        self.assertTrue((self.sales["quantity"] > 0).all())
        self.assertTrue((self.sales["net_amount_irr"] > 0).all())
        self.assertTrue((self.returns["return_amount_irr"] > 0).all())
        self.assertTrue(self.sales["discount_pct"].between(0, 1).all())

    def test_region_matches_customer_region(self):
        m = self.sales.merge(self.customer[["customer_id", "region_id"]], on="customer_id",
                             suffixes=("", "_c"))
        self.assertEqual(int((m["region_id"] != m["region_id_c"]).sum()), 0)

    def test_returns_not_exceeding_sales_line(self):
        m = self.returns.merge(self.sales[["sale_id", "quantity", "net_amount_irr"]], on="sale_id")
        self.assertTrue((m["quantity_returned"] <= m["quantity"]).all())
        self.assertTrue((m["return_amount_irr"] <= m["net_amount_irr"]).all())

    def test_total_sales_amount(self):
        total = int(self.sales["net_amount_irr"].sum())
        # کنترل پایداری seed: مقدار باید ثابت و قابل بازتولید بماند
        self.assertEqual(total, 12_491_123_417_390)

    def test_all_regions_present(self):
        self.assertEqual(self.sales["region_id"].nunique(), 12)


class TestStagingTransform(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # فایل خام: خالی‌ها باید رشتهٔ خالی بمانند (نه NaN) تا قاعدهٔ «تخفیف خالی → ۰» آزموده شود
        cls.stg = load("stg_sales_raw", keep_default_na=False)

    def test_row_count(self):
        self.assertEqual(len(self.stg), 300)

    def test_all_dates_convertible(self):
        for raw in self.stg["sale_date_raw"]:
            key, jalali = etl.parse_sale_date(raw)
            self.assertIsInstance(key, int)
            self.assertRegex(jalali, r"^1403/\d{2}/\d{2}$")

    def test_mixed_date_formats_present(self):
        raws = self.stg["sale_date_raw"].astype(str)
        self.assertTrue(raws.str.match(r"^1403/").any(), "تاریخ شمسی")
        self.assertTrue(raws.str.match(r"^2\d{3}-\d{2}-\d{2}$").any(), "YYYY-MM-DD میلادی")
        self.assertTrue(raws.str.match(r"^\d{2}-\d{2}-2\d{3}$").any(), "DD-MM-YYYY میلادی")
        self.assertTrue(raws.str.match(r"^2024/\d{2}/\d{2}$").any(), "YYYY/MM/DD میلادی")

    def test_parsers_specific_cases(self):
        self.assertEqual(etl.parse_sale_date("1403/12/12")[0], 14031212)
        self.assertEqual(etl.parse_sale_date("2024-07-28")[0], 14030507)
        self.assertEqual(etl.parse_sale_date("28-07-2024")[0], 14030507)
        self.assertEqual(etl.parse_sale_date(" 2024/07/28 ")[0], 14030507)

    def test_bad_date_raises(self):
        for bad in ["1403/13/45", "abc", "", "1403/00/10"]:
            with self.assertRaises(ValueError):
                etl.parse_sale_date(bad)

    def test_parse_amount(self):
        self.assertEqual(etl.parse_amount("1,234,500"), 1234500)
        self.assertEqual(etl.parse_amount(" 1 234 500 "), 1234500)
        self.assertIsNone(etl.parse_amount(""))
        with self.assertRaises(ValueError):
            etl.parse_amount("abc")

    def test_parse_discount(self):
        self.assertEqual(etl.parse_discount(""), 0.0)
        self.assertEqual(etl.parse_discount("0.05"), 0.05)
        self.assertEqual(etl.parse_discount("5%"), 0.05)
        self.assertEqual(etl.parse_discount("۵٪"), 0.05)
        with self.assertRaises(ValueError):
            etl.parse_discount("150%")

    def test_thousands_comma_removed(self):
        self.assertGreater(int(self.stg["unit_price_raw"].astype(str).str.contains(",").sum()), 0)
        for raw in self.stg["unit_price_raw"].head(50):
            self.assertNotIn(",", str(etl.parse_amount(raw)))

    def test_blank_discount_becomes_zero(self):
        blanks = self.stg["discount_raw"].astype(str).str.strip() == ""
        self.assertGreater(int(blanks.sum()), 0)
        for raw in self.stg.loc[blanks, "discount_raw"]:
            self.assertEqual(etl.parse_discount(raw), 0.0)

    def test_dirty_whitespace_present(self):
        self.assertGreater(int(self.stg["customer_name_raw"].astype(str)
                               .str.match(r"^\s|\s$").sum()), 0)


class TestCompatibility(unittest.TestCase):
    """قفل کردن کفِ نسخهٔ پایتون: استقرار روی Streamlit Cloud/سرور قدیمی نباید بشکند."""

    PY_FILES = [
        "app.py", "model/etl_staging_to_dw.py", "tests/test_data_quality.py",
        "scripts/generate_all_data.py", "scripts/make_model_diagram.py",
        "scripts/make_preview.py", "scripts/check_compat.py",
    ]

    def test_compiles_with_python_39_grammar(self):
        import ast
        for rel in self.PY_FILES:
            path = BASE_DIR / rel
            if not path.exists():
                continue
            src = path.read_text(encoding="utf-8")
            with self.subTest(file=rel):
                try:
                    ast.parse(src, filename=rel, feature_version=(3, 9))
                except SyntaxError as exc:
                    self.fail(f"{rel} خط {exc.lineno}: با گرامر پایتون ۳٫۹ خوانده نمی‌شود "
                              f"({exc.msg}). مقدار f-string را در متغیر بگیرید.")

    def test_no_pep701_fstrings(self):
        """هیچ f-string چندخطی/کوتیشن همسان داخل {} نباشد (فقط ۳٫۱۲+)."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "check_compat", BASE_DIR / "scripts" / "check_compat.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for rel in self.PY_FILES:
            path = BASE_DIR / rel
            if not path.exists():
                continue
            with self.subTest(file=rel):
                problems = mod.scan(path)
                self.assertEqual(problems, [], f"{rel}: {problems}")


class TestArtifacts(unittest.TestCase):
    def test_required_files_exist(self):
        required = [
            "model/schema.sql", "model/etl_staging_to_dw.py", "model/MODEL.md",
            "model/measures.dax", "report/ARCHITECTURE.md", "report/DEPLOYMENT_CHECKLIST.md",
            "report/POWER_BI_BUILD_GUIDE.md", "report/theme.json", "assets/model_diagram.svg",
            "data/DATA_DICTIONARY.md", "data/DATA_QUALITY_REPORT.md", "app.py",
        ]
        for rel in required:
            self.assertTrue((BASE_DIR / rel).exists(), f"موجود نیست: {rel}")

    def test_theme_json_valid(self):
        theme = json.loads((BASE_DIR / "report" / "theme.json").read_text(encoding="utf-8"))
        self.assertEqual(theme["name"], "Enterprise DW Fa")
        # پالت جاری (هم‌راستا با اپ): گرافیتی #1f2630 + آجری #9c4a3c روی #f7f8f9
        self.assertIn("#1f2630", theme["dataColors"])
        self.assertIn("#9c4a3c", theme["dataColors"])
        self.assertEqual(theme["background"], "#f7f8f9")

    def test_sql_contains_core_objects(self):
        sql = (MODEL_DIR / "schema.sql").read_text(encoding="utf-8")
        for obj in ["dw.dim_date", "dw.dim_customer", "dw.dim_product", "dw.dim_region",
                    "dw.fact_sales", "dw.fact_returns", "dw.etl_reject",
                    "stg.sales_raw", "jalali_date_key", "SCHEMA_ID"]:
            self.assertIn(obj, sql, f"در schema.sql نیست: {obj}")

    def test_svg_wellformed(self):
        import xml.etree.ElementTree as ET
        ET.parse(BASE_DIR / "assets" / "model_diagram.svg")

    def test_demo_db_created_by_etl(self):
        if not (MODEL_DIR / "dw_demo.sqlite").exists():
            self.skipTest("dw_demo.sqlite هنوز ساخته نشده (ETL اجرا شود)")
        import sqlite3
        con = sqlite3.connect(MODEL_DIR / "dw_demo.sqlite")
        n = con.execute("SELECT COUNT(*) FROM fact_sales").fetchone()[0]
        con.close()
        self.assertEqual(n, 30_000)


if __name__ == "__main__":
    unittest.main(verbosity=2)

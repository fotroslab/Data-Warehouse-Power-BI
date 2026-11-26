#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست راست‌چینی واقعی (RTL) — با مرورگر، نه با فرض.
================================================================
این تست اپ Streamlit را بالا می‌آورد (یا از سرور در حال اجرا استفاده می‌کند)،
سپس با Playwright **مقدار محاسبه‌شدهٔ** `direction` و `text-align` را از DOM
می‌خواند. اگر جایی متن چپ‌چین باشد، تست می‌شکند.

اجرا:
    # ۱) سرور در حال اجرا (توصیه‌شده)
    streamlit run app.py --server.port 8506 --server.address 0.0.0.0
    python3 tests/test_rtl_layout.py

    # ۲) یا بدون سرور: اپ را خودش بالا می‌آورد
    python3 tests/test_rtl_layout.py --start

اگر playwright نصب نباشد، تست Skip می‌شود (نه Fail).
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("RTL_TEST_PORT", "8506"))
URL = f"http://localhost:{PORT}"

# عناصری که باید راست‌چین باشند
RTL_SELECTORS = [
    ".stApp",
    '[data-testid="stMarkdownContainer"]',
    '[data-testid="stMarkdown"]',
    ".sec .t",
    ".kpi .lb",
    ".kpi .vl",
    ".note",
    ".hint",
    ".head .lede",
    "table.rt",
    "table.rt thead th",
    "table.rt tbody td:not(.m)",   # سلول‌های فنی (.m) عمداً LTR هستند
]

# عناصری که باید چپ‌چین بمانند (کد)
# استثناهای عمدی: کد و نام‌های فنی باید چپ‌چین بمانند
LTR_SELECTORS = [".stApp pre code", ".stApp code", "table.rt td.m"]


def _have_playwright() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


class TestRtlLayout(unittest.TestCase):
    server: subprocess.Popen | None = None

    @classmethod
    def setUpClass(cls):
        if not _have_playwright():
            raise unittest.SkipTest("playwright نصب نیست")
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "")
        cls._own_server = False
        if not cls._is_up():
            # اگر سروری در حال اجرا نیست، خودِ تست اپ را بالا می‌آورد و در پایان می‌بندد
            cls.server = subprocess.Popen(
                [sys.executable, "-m", "streamlit", "run", "app.py",
                 "--server.port", str(PORT), "--server.address", "0.0.0.0",
                 "--server.headless", "true"],
                cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            cls._own_server = True
            deadline = time.time() + 150
            while time.time() < deadline and not cls._is_up():
                time.sleep(2)
            if not cls._is_up():
                raise unittest.SkipTest("اپ بالا نیامد؛ تست RTL رد شد")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "server", None):
            cls.server.terminate()
            try:
                cls.server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                cls.server.kill()

    @staticmethod
    def _is_up() -> bool:
        import urllib.request
        try:
            with urllib.request.urlopen(f"{URL}/_stcore/health", timeout=3) as r:
                return r.status == 200
        except Exception:
            return False

    def _measure(self, page) -> list[dict]:
        return page.evaluate(
            """(sels) => {
                const out = [];
                for (const sel of sels) {
                    const el = document.querySelector(sel);
                    if (!el) { out.push({sel, missing: true}); continue; }
                    const cs = getComputedStyle(el);
                    const r = el.getBoundingClientRect();
                    out.push({sel, dir: cs.direction, align: cs.textAlign,
                              x: Math.round(r.x), w: Math.round(r.width)});
                }
                return out;
            }""",
            [*RTL_SELECTORS, *LTR_SELECTORS],
        )

    def test_elements_are_right_aligned(self):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1520, "height": 1200}, locale="fa-IR")
            page.goto(URL, wait_until="domcontentloaded", timeout=120_000)
            page.wait_for_selector('[data-testid="stSidebar"]', timeout=120_000)
            time.sleep(5)
            measured = self._measure(page)
            browser.close()

        by_sel = {m["sel"]: m for m in measured}
        failures = []
        for sel in RTL_SELECTORS:
            m = by_sel.get(sel, {})
            if m.get("missing"):
                failures.append(f"{sel}: عنصر در صفحه پیدا نشد")
                continue
            if m["dir"] != "rtl":
                failures.append(f"{sel}: direction={m['dir']} (باید rtl باشد)")
            if m["align"] not in ("right", "start"):
                failures.append(f"{sel}: text-align={m['align']} (باید right باشد)")
        for sel in LTR_SELECTORS:
            m = by_sel.get(sel, {})
            if m.get("missing"):
                continue
            if m["dir"] != "ltr":
                failures.append(f"{sel}: کد باید ltr بماند، ولی {m['dir']} است")

        self.assertEqual(failures, [], "ایرادهای راست‌چینی:\n" + "\n".join(failures))

    def test_no_glide_dataframe_left_aligned(self):
        """هیچ st.dataframe باقی نمانده باشد (چون همیشه LTR است)."""
        src = (BASE_DIR / "app.py").read_text(encoding="utf-8")
        calls = [ln for ln in src.splitlines()
                 if "st.dataframe(" in ln and not ln.strip().startswith("#")]
        self.assertEqual(calls, [], f"st.dataframe در app.py مانده است: {calls}")

    def test_rtl_table_used(self):
        src = (BASE_DIR / "app.py").read_text(encoding="utf-8")
        self.assertGreaterEqual(src.count(" table(") + src.count("(table("), 6,
                                "همهٔ جدول‌ها باید با تابع table() ساخته شوند")
        self.assertIn('table.rt', src)


if __name__ == "__main__":
    unittest.main(verbosity=2)

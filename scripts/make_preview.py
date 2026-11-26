#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_preview.py — اسکرین‌شات واقعی اپ با Playwright
=====================================================
پیش‌نیاز: streamlit روی پورت 8506 در حال اجرا + playwright + chromium.

    streamlit run app.py --server.port 8506 --server.address 0.0.0.0 &
    python3 scripts/make_preview.py

خروجی:
    assets/preview.png        (صفحهٔ نمای کلی، viewport ۱۵۲۰×۱۷۵۰)
    assets/preview_etl.png    (صفحهٔ ETL پس از اجرای واقعی اسکریپت)
    assets/preview_sales.png  (صفحهٔ تحلیل فروش)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS = BASE_DIR / "assets"
URL = "http://localhost:8506"
VIEWPORT = {"width": 1520, "height": 1750}

CSS_FIX = """
.js-plotly-plot, .js-plotly-plot .plot-container, .js-plotly-plot svg { direction: ltr !important; }
header[data-testid="stHeader"] { display: none !important; }
.block-container { padding-top: 1.2rem !important; }
"""


def goto_page(page, label: str) -> None:
    """کلیک روی گزینهٔ صفحه در سایدبار بر اساس متن."""
    item = page.locator('section[data-testid="stSidebar"] label', has_text=label).first
    item.scroll_into_view_if_needed()
    item.click()
    time.sleep(2.6)


def settle(page, extra: float = 2.0) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except Exception:
        pass
    time.sleep(extra)


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-device-scale-factor=1"])
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1.4,
                                locale="fa-IR")
        page.goto(URL, wait_until="domcontentloaded", timeout=120_000)
        # انتظار تا رندر کامل (وجود سایدبار و اولین نمودار/تصویر)
        page.wait_for_selector('section[data-testid="stSidebar"]', timeout=120_000)
        try:
            page.wait_for_selector(".js-plotly-plot, [data-testid='stImage']", timeout=60_000)
        except Exception:
            pass
        settle(page, 4)
        page.add_style_tag(content=CSS_FIX)
        settle(page, 1.5)

        # ---- ۱) نمای کلی
        page.screenshot(path=str(ASSETS / "preview.png"), full_page=True)
        print("✔ assets/preview.png")

        # ---- ۲) ETL زنده: اجرای واقعی اسکریپت از طریق دکمه
        goto_page(page, "پایپ‌لاین ETL")
        page.add_style_tag(content=CSS_FIX)
        btn = page.get_by_role("button", name="اجرای ETL", exact=True)
        btn.click()
        # انتظار برای خروجی متنی واقعی اسکریپت
        page.wait_for_selector("pre", timeout=180_000)
        page.wait_for_function(
            """() => Array.from(document.querySelectorAll('pre'))
                     .some(e => e.innerText.includes('dw_demo.sqlite'))""",
            timeout=180_000,
        )
        settle(page, 3)
        page.screenshot(path=str(ASSETS / "preview_etl.png"), full_page=True)
        print("✔ assets/preview_etl.png")

        # ---- ۳) تحلیل فروش
        goto_page(page, "تحلیل فروش")
        settle(page, 3)
        page.add_style_tag(content=CSS_FIX)
        settle(page, 1.5)
        page.screenshot(path=str(ASSETS / "preview_sales.png"), full_page=True)
        print("✔ assets/preview_sales.png")

        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_update.py — اعمال بستهٔ به‌روزرسانی روی مخزن GitHub
============================================================
این اسکریپت را در **ریشهٔ مخزن کلون‌شده** بگذارید و اجرا کنید:

    python3 apply_update.py            # فقط بررسی (dry-run)
    python3 apply_update.py --apply    # اعمال واقعی

کارهایی که انجام می‌دهد:

  1. پوشهٔ اشتباه `.streamlit ` (با فاصلهٔ انتها) را به `.streamlit` تغییر نام می‌دهد.
     Streamlit این پوشه را نمی‌خواند و تنظیمات تم/پورت اعمال نمی‌شد.
  2. نسخه‌های جدید فایل‌ها را می‌گذارد (app.py، اسناد، تم، تست‌ها، نمودار، اسکرین‌شات‌ها، sqlite).
  3. فایل‌های جدید را اضافه می‌کند (rig، nav، تست راست‌چینی، نمودار HTML، فونت TTF).
  4. کپیِ ریشه‌ای `config.streamlit.toml` را پاک می‌کند تا با `.streamlit/config.toml` قاطی نشود.

سپس خودتان commit/push می‌کنید (اسکریپت دستورها را چاپ می‌کند).
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path.cwd()
APPLY = "--apply" in sys.argv

# (فایل در بسته، مقصد در مخزن)
FILES = [
    ("app.py", "app.py"),
    ("README_FA.md", "README_FA.md"),
    ("VALIDATION.md", "VALIDATION.md"),
    ("LIMITATIONS.md", "LIMITATIONS.md"),
    ("HANDOFF_FA.md", "HANDOFF_FA.md"),
    ("report/theme.json", "report/theme.json"),
    ("tests/test_data_quality.py", "tests/test_data_quality.py"),
    ("tests/test_rtl_layout.py", "tests/test_rtl_layout.py"),
    ("scripts/check_compat.py", "scripts/check_compat.py"),
    ("scripts/make_model_diagram.py", "scripts/make_model_diagram.py"),
    ("scripts/make_preview.py", "scripts/make_preview.py"),
    ("assets/model_diagram.svg", "assets/model_diagram.svg"),
    ("assets/model_diagram.html", "assets/model_diagram.html"),
    ("assets/preview.png", "assets/preview.png"),
    ("assets/preview_etl.png", "assets/preview_etl.png"),
    ("assets/preview_sales.png", "assets/preview_sales.png"),
    ("assets/fonts/Vazirmatn-Regular.ttf", "assets/fonts/Vazirmatn-Regular.ttf"),
    ("assets/fonts/Vazirmatn-Medium.ttf", "assets/fonts/Vazirmatn-Medium.ttf"),
    ("assets/fonts/Vazirmatn-Bold.ttf", "assets/fonts/Vazirmatn-Bold.ttf"),
    ("model/dw_demo.sqlite", "model/dw_demo.sqlite"),
]

REMOVE = [".streamlit /config.toml", "config.streamlit.toml"]


def fix_streamlit_dir() -> None:
    wrong = ROOT / ".streamlit "
    right = ROOT / ".streamlit"
    if wrong.exists():
        print(f"  • پوشهٔ اشتباه پیدا شد: {wrong.name!r} (با فاصله)")
        if APPLY:
            if right.exists():
                for f in wrong.iterdir():
                    shutil.copy2(f, right / f.name)
                shutil.rmtree(wrong)
                print("    → محتوا به .streamlit منتقل و پوشهٔ اشتباه حذف شد")
            else:
                wrong.rename(right)
                print("    → تغییر نام به .streamlit انجام شد")
        else:
            print("    (در حالت --apply تغییر نام داده می‌شود)")
    elif right.exists():
        print("  ✓ پوشهٔ .streamlit درست است")
    else:
        print("  ! نه پوشهٔ .streamlit هست و نه نسخهٔ اشتباه؛ بسته را دوباره بگیرید")


def main() -> int:
    if not (HERE / "app.py").exists():
        print("این اسکریپت باید کنار فایل‌های بسته اجرا شود.")
        return 1
    if not (ROOT / "app.py").exists():
        print(f"ریشهٔ مخزن پیدا نشد: {ROOT}\n"
              "داخل مخزن کلون‌شده بروید و دوباره اجرا کنید.")
        return 1

    print("۱) اصلاح پوشهٔ تنظیمات Streamlit")
    fix_streamlit_dir()

    print("\n۲) کپی فایل‌ها")
    for src, dst in FILES:
        s, d = HERE / src, ROOT / dst
        if not s.exists():
            print(f"  ! در بسته نیست: {src}")
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        state = "به‌روزرسانی" if d.exists() else "جدید"
        print(f"  • {dst}  ({state})")
        if APPLY:
            shutil.copy2(s, d)

    print("\n۳) حذف فایل‌های اضافه")
    for rel in REMOVE:
        p = ROOT / rel
        if p.exists():
            print(f"  • حذف {rel}")
            if APPLY:
                p.unlink()
        else:
            print(f"  · نبود: {rel}")

    if not APPLY:
        print("\nحالت بررسی تمام شد. برای اعمال واقعی:")
        print("    python3 apply_update.py --apply")
        return 0

    print("\n✅ اعمال شد. حالا خودتان commit و push کنید:\n")
    print('    git rm -r --cached ".streamlit " 2>/dev/null || true')
    print("    git add -A")
    print('    git commit -m "fix: .streamlit folder name, RTL layout, design system, diagram + tests"')
    print("    git push origin main")
    return 0


if __name__ == "__main__":
    sys.exit(main())

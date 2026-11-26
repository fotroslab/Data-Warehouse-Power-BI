#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_compat.py — نگهبان سازگاری نسخهٔ پایتون
===============================================
Streamlit Community Cloud (و بعضی سرورهای داخلی) ممکن است با پایتون قدیمی‌تر از ۳٫۱۲ اجرا شوند.
قابلیت‌های **PEP 701** (پایتون ۳٫۱۲+) روی ۳٫۱۱ و پایین‌تر `SyntaxError` می‌دهند:

  * عبارت چندخطی داخل {} در f-string
  * بک‌اسلش یا کامنت داخل {}
  * استفادهٔ همان نوع کوتیشنِ بیرونی داخل {}

این اسکریپت با `tokenize` (توکن‌های FSTRING_START/MIDDLE/END) این موارد را دقیق پیدا می‌کند.

اجرا:
    python3 scripts/check_compat.py            # همهٔ فایل‌های پروژه
    python3 scripts/check_compat.py app.py     # یک فایل مشخص

کد خروج ۱ اگر موردی پیدا شود.
"""
from __future__ import annotations

import io
import sys
import tokenize
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
TARGETS = ["app.py", "model/etl_staging_to_dw.py", "tests/test_data_quality.py",
           "scripts/generate_all_data.py", "scripts/make_model_diagram.py",
           "scripts/make_preview.py", "scripts/check_compat.py"]

FSTRING_START = getattr(tokenize, "FSTRING_START", None)
FSTRING_END = getattr(tokenize, "FSTRING_END", None)


def scan(path: Path) -> list[tuple[int, str]]:
    src = path.read_text(encoding="utf-8")
    if FSTRING_START is None:            # پایتون < ۳٫۱۲: f-string یک STRING معمولی است
        return _scan_text(src)

    problems: list[tuple[int, str]] = []
    stack: list[dict] = []   # هر f-string باز: {row, quote, brace_depth}
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, SyntaxError) as exc:
        return [(getattr(exc, "lineno", 0) or 0, f"خطای توکن‌سازی: {exc}")]

    for tok in toks:
        if tok.type == FSTRING_START:
            q = tok.string.lstrip("fFrRbBuU")
            stack.append({"row": tok.start[0], "quote": q, "brace": 0,
                          "triple": q.startswith('"""') or q.startswith("'''")})
            continue
        if tok.type == FSTRING_END:
            if stack:
                stack.pop()
            continue
        if not stack:
            continue
        top = stack[-1]
        if tok.type == tokenize.OP and tok.string == "{":
            top["brace"] += 1
        elif tok.type == tokenize.OP and tok.string == "}":
            top["brace"] = max(0, top["brace"] - 1)
        elif tok.type in (tokenize.NL, tokenize.NEWLINE) and top["brace"] > 0:
            problems.append((tok.start[0],
                             "عبارت f-string چندخطی است (PEP 701؛ روی پایتون < ۳٫۱۲ "
                             "SyntaxError می‌دهد)"))
        elif tok.type == tokenize.STRING and top["brace"] > 0 and not top["triple"]:
            # کوتیشن همسان داخلی در پایتون < ۳٫۱۲ مجاز نیست (اگر طول ۱ یا ۲ باشد)
            inner = tok.string.lstrip("fFrRbBuU")
            if len(top["quote"]) <= 2 and inner[:1] == top["quote"][:1]:
                problems.append((tok.start[0],
                                 "کوتیشن یکسان با بیرون داخل {} (PEP 701)"))
    return sorted(set(problems))


def _scan_text(src: str) -> list[tuple[int, str]]:
    """مسیر پشتیبان (پایتون < ۳٫۱۲): بررسی متنی ساده."""
    out, open_line = [], None
    for no, line in enumerate(src.splitlines(), start=1):
        if open_line is None:
            if ("f'" in line or 'f"' in line) and line.count("{") > line.count("}"):
                open_line = no
        else:
            if "{" in line and "}" not in line:
                out.append((no, "عبارت f-string چندخطی است (PEP 701)"))
            if "}" in line:
                open_line = None
    return sorted(set(out))


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv[1:]] or [BASE_DIR / t for t in TARGETS]
    total = 0
    for path in targets:
        if not path.exists():
            print(f"رد شد (موجود نیست): {path}")
            continue
        problems = scan(path)
        name = str(path.relative_to(BASE_DIR)) if path.is_relative_to(BASE_DIR) else str(path)
        if problems:
            total += len(problems)
            print(f"❌ {name}")
            for no, msg in problems:
                print(f"   خط {no}: {msg}")
        else:
            print(f"✅ {name}")
    print("-" * 56)
    if total:
        print(f"{total} مورد ناسازگار با پایتون < ۳٫۱۲ پیدا شد.")
        print("قاعده: مقدار را در متغیر بگیرید و f-string را تک‌خطی/ساده نگه دارید.")
        return 1
    print("بدون مورد PEP 701 — روی پایتون ۳٫۹+ قابل اجراست.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

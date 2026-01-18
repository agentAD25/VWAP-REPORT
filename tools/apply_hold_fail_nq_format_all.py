#!/usr/bin/env python3
"""
Apply NQ-format to all hold_fail_rates.html across all instruments and timeframes.

- Discovers *_hold_fail_rates.html under docs/reports and site/docs/reports.
- Infers contract and timeframe from filename; infers instrument (NQ, MGC, …) for subtitle.
- Applies: CSS (via nq_format_helpers), subtitle, insights-table, chart 400px,
  remove Downloads, title casing (Mgc*->MGC*, 1M->1m).

Idempotent and non-destructive: safe to run multiple times.
Warns when CSS placeholder is not found and not already themed; use --strict to exit 1.
"""

import argparse
import re
import sys
from pathlib import Path

# Ensure tools/ is on path when run as py tools\apply_hold_fail_nq_format_all.py
_tools = Path(__file__).resolve().parent
if str(_tools) not in sys.path:
    sys.path.insert(0, str(_tools))

from nq_format_helpers import (
    contract_to_instrument,
    replace_placeholder_css_with_nq_theme,
)

BASE = Path(__file__).parent.parent
REPORTS_DIRS = [BASE / "docs" / "reports", BASE / "site" / "docs" / "reports"]

# Stem pattern: SOMETHING_1m_hold_fail_rates -> prefix, tf
_STEM_RE = re.compile(r"^(.+)_(\d+m)_hold_fail_rates$")


def _parse_contract_tf(path: Path) -> tuple[str | None, str | None]:
    stem = path.stem
    m = _STEM_RE.match(stem)
    if not m:
        return (None, None)
    prefix, tf = m.group(1), m.group(2)
    contract = prefix.split("_")[0] if prefix else None
    return (contract, tf)


def _subtitle_block(instrument: str, tf: str) -> str:
    return (
        f'<div class="subtitle">\n'
        f"            {instrument} | \n"
        f"            RTH | \n"
        f"            {tf} | \n"
        f"            Built by TonySnow | ALPHA DRIP\n"
        f"        </div>"
    )


def _apply(s: str, instrument: str, tf: str) -> str:
    # 1) Subtitle: replace any subtitle with our format
    s = re.sub(
        r'<div class="subtitle">\s*[\s\S]*?</div>',
        _subtitle_block(instrument, tf),
        s,
        count=1,
    )
    # 2) insights-table: panel+Data Preview+data-table -> insights-table and plain table
    s = s.replace(
        '<div class="panel">\n        <div class="insights-title">Data Preview</div>\n        <table class="data-table" id="dataTable">',
        '<div class="insights-table">\n        <div class="insights-title">Data Preview</div>\n        <table id="dataTable">',
    )
    # 3) chart height
    s = s.replace(
        'style="height: 450px; width: 100%; margin: 0 auto;"',
        'style="height: 400px;"',
    )
    # 4) remove Downloads block (hold_fail_rates.csv)
    s = re.sub(
        r'\s*</div>\s*\n\s*\n\s*\n\s*<div class="download-section">\s*<h3[^>]*>Downloads</h3>.*?'
        r'<a href="[^"]*hold_fail_rates\.csv"[^>]*>.*?</a>\s*</div>\s*\n\s*\n\s*\n\s*'
        r'<div class="panel">\s*<h3[^>]*>Notes</h3>',
        '\n    </div>\n\n    <div class="panel">\n        <h3 style="color: var(--text-accent); margin-bottom: var(--spacing-sm);">Notes</h3>',
        s,
        flags=re.DOTALL,
    )
    # 5) title casing: MgcXnn -> MGCXnn, 1M/5M/15M/30M -> 1m/5m/15m/30m
    s = re.sub(r"Mgc([a-zA-Z])(\d+)", lambda m: "MGC" + m.group(1).upper() + m.group(2), s)
    s = re.sub(r"\b(\d+)M\b", r"\1m", s)
    return s


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply NQ-format to all hold_fail_rates (all contracts/timeframes).")
    ap.add_argument("--strict", action="store_true", help="Exit 1 if CSS replace not applied (placeholder not found and not already themed).")
    args = ap.parse_args()

    # Discover all hold_fail_rates.html
    files: list[Path] = []
    for rd in REPORTS_DIRS:
        if not rd.exists():
            continue
        for p in rd.rglob("*hold_fail_rates.html"):
            files.append(p)

    updated = 0
    css_not_found: list[str] = []

    for path in sorted(files):
        rel = path.relative_to(BASE)
        contract, tf = _parse_contract_tf(path)
        if not contract or not tf:
            print(f"  [SKIP] {rel} (could not parse contract/tf)")
            continue

        instrument = contract_to_instrument(contract)

        try:
            s = path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  [ERROR] {rel}: {e}")
            if args.strict:
                return 1
            continue

        # CSS via shared helper
        s, css_status = replace_placeholder_css_with_nq_theme(s)
        if css_status == "not_found":
            css_not_found.append(str(rel))
        # (replaced / already: no extra message)

        # Structural and text edits
        s = _apply(s, instrument, tf)

        try:
            path.write_text(s, encoding="utf-8")
        except Exception as e:
            print(f"  [ERROR] write {rel}: {e}")
            if args.strict:
                return 1
            continue

        updated += 1
        print(f"  Updated: {rel} ({contract} {tf} -> {instrument})")

    if css_not_found:
        print("")
        print("  WARNING: CSS placeholder not found (NQ theme may not be applied):")
        for x in css_not_found:
            print(f"    - {x}")
        if args.strict:
            return 1

    print("")
    print(f"  Done: {updated} hold_fail_rates updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

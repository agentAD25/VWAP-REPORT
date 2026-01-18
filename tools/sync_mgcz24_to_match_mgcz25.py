#!/usr/bin/env python3
"""
Sync MGCZ24 from local vwap_reports to website docs/reports so it matches MGCZ25:
- Same report set (heatmap, hold_fail_rates, mfe_mae, regime_segment_grid, first_touch, touch_sequence, etc.)
- Remove cross-contamination (MGCQ24_*, wrong-timeframe MGCZ24_*_Xm_* in Xm folder)
- Copy dashboards/ subfolder with MGCZ24_*_Xm_* for each timeframe.
"""

import re
import shutil
from pathlib import Path

REPORTS_DIR = Path(__file__).parent.parent / "docs" / "reports"
LOCAL = Path(r"D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports")

MGCZ24_FOLDERS = [
    "MGCZ24_20240725-20241122_1m",
    "MGCZ24_20240725-20241122_5m",
    "MGCZ24_20240725-20241122_15m",
    "MGCZ24_20240725-20241122_30m",
]

# Filename has CONTRACT_YYYYMMDD-YYYYMMDD_TF_ or .csv/.png
PREFIX = re.compile(r'^([A-Z0-9]+)_\d{8}-\d{8}_(\d+m)(?:_|\.)')


def file_wrong_contract(name: str) -> bool:
    m = PREFIX.match(name)
    return m is not None and m.group(1) != "MGCZ24"


def file_wrong_timeframe(name: str, folder_tf: str) -> bool:
    """True if filename has MGCZ24_..._Xm_* and Xm != folder_tf."""
    m = PREFIX.match(name)
    if not m or m.group(1) != "MGCZ24":
        return False
    return m.group(2) != folder_tf


def main():
    for folder in MGCZ24_FOLDERS:
        m = re.match(r'MGCZ24_\d{8}-\d{8}_(\d+m)', folder)
        if not m:
            continue
        tf = m.group(1)
        web = REPORTS_DIR / folder
        local = LOCAL / folder
        if not local.exists():
            print(f"Skip {folder}: local missing")
            continue
        web.mkdir(parents=True, exist_ok=True)

        # 1) Delete wrong files from web root
        for p in list(web.iterdir()):
            if not p.is_file():
                continue
            if file_wrong_contract(p.name) or file_wrong_timeframe(p.name, tf):
                p.unlink()
                print(f"  Removed: {folder}/{p.name}")

        # 2) Delete wrong files from web dashboards
        dpath = web / "dashboards"
        if dpath.exists():
            for p in list(dpath.iterdir()):
                if not p.is_file():
                    continue
                if file_wrong_contract(p.name) or file_wrong_timeframe(p.name, tf):
                    p.unlink()
                    print(f"  Removed: {folder}/dashboards/{p.name}")

        # 3) Copy from local root: MGCZ24_*_Xm_* only (and .json, short names if we want)
        for p in local.iterdir():
            if not p.is_file():
                continue
            if file_wrong_contract(p.name) or file_wrong_timeframe(p.name, tf):
                continue
            ext = p.suffix.lower()
            if ext not in ('.html', '.csv', '.png', '.json'):
                continue
            shutil.copy2(p, web / p.name)
            print(f"  Copied root: {p.name}")

        # 4) Copy from local dashboards: MGCZ24_*_Xm_* (and short names) to web/dashboards
        ld = local / "dashboards"
        if ld.exists():
            dpath.mkdir(parents=True, exist_ok=True)
            for p in ld.iterdir():
                if not p.is_file():
                    continue
                # allow short names (daily_max_extensions.html, etc.) or MGCZ24_*_Xm_*
                if PREFIX.match(p.name):
                    if file_wrong_contract(p.name) or file_wrong_timeframe(p.name, tf):
                        continue
                elif not p.name.endswith(('.html', '.png')):
                    continue
                ext = p.suffix.lower()
                if ext not in ('.html', '.png'):
                    continue
                shutil.copy2(p, dpath / p.name)
                print(f"  Copied dash: {p.name}")

    print("MGCZ24 sync done.")


if __name__ == "__main__":
    main()

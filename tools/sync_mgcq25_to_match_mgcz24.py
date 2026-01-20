#!/usr/bin/env python3
"""
Sync MGCQ25 from local vwap_reports to website docs/reports and clean site/docs/reports
so MGCQ25 matches MGCZ24's report set:

- hold_fail_rates, heatmap_time_of_day_x_reaction, mfe_mae_by_event_window, regime_segment_grid
- daily_max_extensions, extension_tail_metrics, oos_by_month (from dashboards when needed)
- Remove cross-contamination (MGCQ24_*, wrong-timeframe) from both docs and site.
"""

import re
import shutil
from pathlib import Path

BASE = Path(__file__).parent.parent
DOCS_REPORTS = BASE / "docs" / "reports"
SITE_REPORTS = BASE / "site" / "docs" / "reports"
LOCAL = Path(r"D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports")

MGCQ25_FOLDERS = [
    "MGCQ25_20250528-20250725_1m",
    "MGCQ25_20250528-20250725_5m",
    "MGCQ25_20250528-20250725_15m",
    "MGCQ25_20250528-20250725_30m",
]

PREFIX = re.compile(r"^([A-Z0-9]+)_\d{8}-\d{8}_(\d+m)(?:_|\.)")

# HTMLs to copy from local/dashboards to web root (canonical; root can be missing or stale)
DASH_TO_ROOT = {
    "daily_max_extensions",
    "extension_tail_metrics",
    "oos_by_month",
    "hold_fail_rates",
    "heatmap_time_of_day_x_reaction",
    "mfe_mae_by_event_window",
    "regime_segment_grid",
}


def file_wrong_contract(name: str, want: str) -> bool:
    m = PREFIX.match(name)
    return m is not None and m.group(1) != want


def file_wrong_timeframe(name: str, want_contract: str, folder_tf: str) -> bool:
    m = PREFIX.match(name)
    if not m or m.group(1) != want_contract:
        return False
    return m.group(2) != folder_tf


def clean_folder(web: Path, contract: str, tf: str) -> None:
    """Remove wrong-contract and wrong-timeframe files from web root and dashboards."""
    for p in list(web.iterdir()):
        if not p.is_file():
            continue
        if file_wrong_contract(p.name, contract) or file_wrong_timeframe(p.name, contract, tf):
            p.unlink()
            print(f"    Removed: {p.name}")
    dpath = web / "dashboards"
    if dpath.exists():
        for p in list(dpath.iterdir()):
            if not p.is_file():
                continue
            if file_wrong_contract(p.name, contract) or file_wrong_timeframe(p.name, contract, tf):
                p.unlink()
                print(f"    Removed: dashboards/{p.name}")


def sync_docs(local: Path, web: Path, folder: str, tf: str) -> None:
    """Copy from local to docs/reports (match MGCZ24 sync logic)."""
    # Copy from local root: MGCQ25_*_tf_* only; skip HTMLs for DASH_TO_ROOT (use dash->root)
    for p in local.iterdir():
        if not p.is_file():
            continue
        if file_wrong_contract(p.name, "MGCQ25") or file_wrong_timeframe(p.name, "MGCQ25", tf):
            continue
        ext = p.suffix.lower()
        if ext not in (".html", ".csv", ".png", ".json"):
            continue
        stem = p.stem
        if ext == ".html" and (
            stem in DASH_TO_ROOT or any(stem == f"{folder}_{s}" for s in DASH_TO_ROOT)
        ):
            continue
        shutil.copy2(p, web / p.name)
        print(f"    Copied root: {p.name}")

    ld = local / "dashboards"
    if ld.exists():
        dpath = web / "dashboards"
        dpath.mkdir(parents=True, exist_ok=True)
        for p in ld.iterdir():
            if not p.is_file():
                continue
            if PREFIX.match(p.name):
                if file_wrong_contract(p.name, "MGCQ25") or file_wrong_timeframe(p.name, "MGCQ25", tf):
                    continue
            elif not p.name.endswith((".html", ".png")):
                continue
            if p.suffix.lower() not in (".html", ".png"):
                continue
            shutil.copy2(p, dpath / p.name)
            print(f"    Copied dash: {p.name}")

        # Dash->root for DASH_TO_ROOT
        for slug in DASH_TO_ROOT:
            for src_name in (f"{folder}_{slug}.html", f"{slug}.html"):
                src = ld / src_name
                if not src.exists():
                    continue
                shutil.copy2(src, web / src_name)
                print(f"    Dash->root: {src_name}")


def main() -> None:
    for folder in MGCQ25_FOLDERS:
        m = re.match(r"MGCQ25_\d{8}-\d{8}_(\d+m)", folder)
        if not m:
            continue
        tf = m.group(1)
        local = LOCAL / folder
        if not local.exists():
            print(f"Skip {folder}: local missing")
            continue

        # --- docs/reports: full sync from local ---
        web_docs = DOCS_REPORTS / folder
        web_docs.mkdir(parents=True, exist_ok=True)
        print(f"[docs] {folder}:")
        clean_folder(web_docs, "MGCQ25", tf)
        sync_docs(local, web_docs, folder, tf)

        # --- site/docs/reports: only clean (sync_reports fills from local) ---
        web_site = SITE_REPORTS / folder
        if web_site.exists():
            print(f"[site] {folder}: cleaning only")
            clean_folder(web_site, "MGCQ25", tf)

    print("MGCQ25 sync done.")


if __name__ == "__main__":
    main()

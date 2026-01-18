#!/usr/bin/env python3
"""
Overwrite MGCZ24 root HTMLs with dashboards versions for reports that had 0/NaN in root.
Data exists; root was serving stale/wrong builds. Use dashboards (built from correct CSV) as source.
Matches what worked for MGCZ25: canonical data lives in dashboards.
"""

import re
import shutil
from pathlib import Path

BASE = Path(__file__).parent.parent
# Fix both docs/reports and site/docs/reports when present (deploy may use either)
REPORTS_DIRS = [
    BASE / "docs" / "reports",
    BASE / "site" / "docs" / "reports",
]

MGCZ24_FOLDERS = [
    "MGCZ24_20240725-20241122_1m",
    "MGCZ24_20240725-20241122_5m",
    "MGCZ24_20240725-20241122_15m",
    "MGCZ24_20240725-20241122_30m",
]

# Slugs that had 0/NaN in root but correct data in dashboards
ROOT_OVERRIDE_SLUGS = ["daily_max_extensions", "extension_tail_metrics", "oos_by_month"]


def _fix_one(reports_dir: Path) -> None:
    for folder in MGCZ24_FOLDERS:
        m = re.match(r"MGCZ24_(\d{8}-\d{8})_(\d+m)", folder)
        if not m:
            continue
        date_range, tf = m.group(1), m.group(2)
        web = reports_dir / folder
        dash = web / "dashboards"
        if not dash.exists():
            continue
        prefix = f"MGCZ24_{date_range}_{tf}"
        for slug in ROOT_OVERRIDE_SLUGS:
            long_name = f"{prefix}_{slug}.html"
            short_name = f"{slug}.html"
            for src_name, dest_name in [(long_name, long_name), (short_name, short_name)]:
                src = dash / src_name
                if not src.exists():
                    continue
                dest = web / dest_name
                shutil.copy2(src, dest)
                print(f"  {reports_dir.relative_to(BASE)} {folder}: dashboards/{src_name} -> {dest_name}")


def _copy_from_primary(primary: Path, other: Path) -> None:
    """When other has no dashboards, copy fixed root HTMLs from primary (e.g. docs -> site/docs)."""
    for folder in MGCZ24_FOLDERS:
        m = re.match(r"MGCZ24_(\d{8}-\d{8})_(\d+m)", folder)
        if not m:
            continue
        date_range, tf = m.group(1), m.group(2)
        prefix = f"MGCZ24_{date_range}_{tf}"
        dest_dir = other / folder
        if not dest_dir.exists() or (dest_dir / "dashboards").exists():
            continue  # has own dashboards, skip
        src_dir = primary / folder
        if not src_dir.exists():
            continue
        for slug in ROOT_OVERRIDE_SLUGS:
            for name in (f"{prefix}_{slug}.html", f"{slug}.html"):
                src = src_dir / name
                if src.exists():
                    shutil.copy2(src, dest_dir / name)
                    print(f"  {other.relative_to(BASE)} {folder}: (from docs) {name}")


def main():
    primary = None
    for rd in REPORTS_DIRS:
        if not rd.exists():
            continue
        _fix_one(rd)
        if primary is None:
            primary = rd
    if primary:
        for rd in REPORTS_DIRS:
            if rd.exists() and rd != primary:
                _copy_from_primary(primary, rd)
    print("MGCZ24 root-override-from-dashboards done.")


if __name__ == "__main__":
    main()

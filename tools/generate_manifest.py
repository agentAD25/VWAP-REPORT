#!/usr/bin/env python3
"""
generate_manifest.py

Scans the reports directory and generates a manifest.json file that
organizes all reports by contract, timeframe, and date range.

Each entry includes gallery routing metadata (dashboard_index, active,
canonical, public_safe) for idempotent root-gallery navigation.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# Reports directory (relative to this script)
# Check both docs/ and site/docs/ (for compatibility)
if (Path(__file__).parent.parent / "docs" / "reports").exists():
    REPORTS_DIR = Path(__file__).parent.parent / "docs" / "reports"
    MANIFEST_FILE = Path(__file__).parent.parent / "docs" / "manifest.json"
else:
    REPORTS_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports"
    MANIFEST_FILE = Path(__file__).parent.parent / "site" / "docs" / "manifest.json"

# Pattern to extract metadata from folder names
# Format: CONTRACT_YYYYMMDD-YYYYMMDD_TIMEFRAME
FOLDER_PATTERN = re.compile(r"^(?P<contract>[A-Z0-9]+)_(?P<start>\d{8})-(?P<end>\d{8})_(?P<tf>\d+m)$")

# Pattern to detect another contract's prefix in a filename (CONTRACT_YYYYMMDD-YYYYMMDD_1m_)
CONTRACT_PREFIX_IN_FILENAME = re.compile(r"^([A-Z0-9]+)_\d{8}-\d{8}_(\d+m)(?:_|\.)")


def file_belongs_to_folder(filename: str, folder_contract: str, folder_tf: str = None) -> bool:
    """
    Return True if this file belongs to the folder's contract (and timeframe if folder_tf given).
    """
    m = CONTRACT_PREFIX_IN_FILENAME.match(filename)
    if not m:
        return True
    if m.group(1) != folder_contract:
        return False
    if folder_tf and m.lastindex >= 2 and m.group(2) != folder_tf:
        return False
    return True


def parse_folder_name(folder_name):
    """Parse folder name; return None if pattern does not match."""
    match = FOLDER_PATTERN.match(folder_name)
    if not match:
        return None
    data = match.groupdict()
    data["date_range"] = f"{data['start']}-{data['end']}"
    return data


def extract_timeframe_minutes(tf_str):
    """Extract numeric minutes from timeframe string (e.g., "15m" -> 15)."""
    match = re.match(r"(\d+)m", tf_str)
    return int(match.group(1)) if match else 0


def resolve_dashboard_index(folder_name: str, folder_path: Path) -> str | None:
    """Return docs-relative path to the gallery dashboard index, if present."""
    dashboards_index = folder_path / "dashboards" / "index.html"
    root_index = folder_path / "index.html"
    if dashboards_index.is_file():
        return f"reports/{folder_name}/dashboards/index.html"
    if root_index.is_file():
        return f"reports/{folder_name}/index.html"
    return None


def classify_entry(
    *,
    folder_name: str,
    folder_path: Path,
    has_csv_exports: bool,
    dashboard_index: str | None,
) -> dict:
    """
    Deterministic gallery status for a report folder.

    CURRENT_CERTIFIED_PUBLIC: dashboards/index.html and no CSV exports.
    LEGACY_WITH_DATA_EXPORTS: root index.html, CSV present (e.g. MNQZ25) — routable, not public_safe.
    LEGACY_CORRUPT_SUPPRESS: CSV present, no certified dashboards gallery — hidden from gallery.
    INTERNAL_ONLY: no routable index.
    """
    has_dashboards_gallery = (folder_path / "dashboards" / "index.html").is_file()
    has_root_index = (folder_path / "index.html").is_file()

    if has_dashboards_gallery and not has_csv_exports:
        status = "CURRENT_CERTIFIED_PUBLIC"
        active = True
        public_safe = True
    elif has_root_index and has_csv_exports:
        status = "LEGACY_WITH_DATA_EXPORTS"
        active = True
        public_safe = False
    elif has_csv_exports:
        status = "LEGACY_CORRUPT_SUPPRESS"
        active = False
        public_safe = False
    elif dashboard_index:
        status = "CURRENT_CERTIFIED_PUBLIC"
        active = True
        public_safe = True
    else:
        status = "INTERNAL_ONLY"
        active = False
        public_safe = False

    return {
        "status": status,
        "active": active,
        "public_safe": public_safe,
    }


def apply_cross_entry_suppression(manifest: dict) -> None:
    """
    When a certified public dashboards entry exists for contract+timeframe,
    suppress legacy CSV-only windows for the same pair.
    """
    for contract in manifest:
        for timeframe in manifest[contract]:
            ranges = manifest[contract][timeframe]
            certified = [
                dr
                for dr, entry in ranges.items()
                if entry.get("status") == "CURRENT_CERTIFIED_PUBLIC"
            ]
            if not certified:
                continue
            for date_range, entry in ranges.items():
                if date_range in certified:
                    continue
                if entry.get("has_csv_exports"):
                    entry["status"] = "LEGACY_CORRUPT_SUPPRESS"
                    entry["active"] = False
                    entry["canonical"] = False
                    entry["public_safe"] = False


def apply_mnqh25_public_only_policy(manifest: dict) -> None:
    """MNQH25: gallery routes only certified public dashboards (5m sample)."""
    mnqh25 = manifest.get("MNQH25")
    if not mnqh25:
        return
    for ranges in mnqh25.values():
        for entry in ranges.values():
            if entry.get("status") != "CURRENT_CERTIFIED_PUBLIC":
                entry["active"] = False
                entry["canonical"] = False
                if entry.get("status") == "LEGACY_WITH_DATA_EXPORTS":
                    entry["status"] = "LEGACY_CORRUPT_SUPPRESS"


def mark_canonical_entries(manifest: dict) -> None:
    """Exactly one canonical active entry per contract+timeframe (if any active)."""
    for contract in manifest:
        for timeframe in manifest[contract]:
            ranges = manifest[contract][timeframe]
            for entry in ranges.values():
                entry["canonical"] = False

            active_items = [
                (date_range, entry)
                for date_range, entry in ranges.items()
                if entry.get("active") and entry.get("dashboard_index")
            ]
            if not active_items:
                continue

            def sort_key(item):
                date_range, entry = item
                return (
                    1 if entry.get("public_safe") else 0,
                    1 if "/dashboards/index.html" in (entry.get("dashboard_index") or "") else 0,
                    entry.get("end") or entry.get("end_date") or "",
                    date_range,
                )

            best_dr, _ = max(active_items, key=sort_key)
            ranges[best_dr]["canonical"] = True


def generate_manifest():
    """Scan reports directory and generate manifest.json."""
    if not REPORTS_DIR.exists():
        print(f"ERROR: Reports directory does not exist: {REPORTS_DIR}")
        print("Please run sync_reports.py first to copy reports.")
        return

    print(f"Scanning reports directory: {REPORTS_DIR}")

    manifest = defaultdict(lambda: defaultdict(lambda: {}))

    for folder_path in sorted(REPORTS_DIR.iterdir()):
        if not folder_path.is_dir():
            continue

        folder_name = folder_path.name
        metadata = parse_folder_name(folder_name)
        if not metadata:
            print(f"Skipping folder (doesn't match pattern): {folder_name}")
            continue

        contract = metadata["contract"]
        timeframe = metadata["tf"]
        date_range = metadata["date_range"]

        png_files = []
        html_files = []
        csv_files = []

        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue
            if not file_belongs_to_folder(file_path.name, contract, timeframe):
                continue
            relative_path_str = str(file_path.relative_to(REPORTS_DIR.parent)).replace("\\", "/")
            ext = file_path.suffix.lower()
            if ext == ".png":
                png_files.append(relative_path_str)
            elif ext == ".html":
                html_files.append(relative_path_str)
            elif ext == ".csv":
                csv_files.append(relative_path_str)

        dashboards_path = folder_path / "dashboards"
        if dashboards_path.is_dir():
            for file_path in dashboards_path.iterdir():
                if not file_path.is_file():
                    continue
                if not file_belongs_to_folder(file_path.name, contract, timeframe):
                    continue
                relative_path_str = str(file_path.relative_to(REPORTS_DIR.parent)).replace("\\", "/")
                ext = file_path.suffix.lower()
                if ext == ".png":
                    png_files.append(relative_path_str)
                elif ext == ".html":
                    html_files.append(relative_path_str)
                elif ext == ".csv":
                    csv_files.append(relative_path_str)

        png_files.sort()
        html_files.sort()
        csv_files.sort()

        has_csv_exports = len(csv_files) > 0
        dashboard_index = resolve_dashboard_index(folder_name, folder_path)
        classification = classify_entry(
            folder_name=folder_name,
            folder_path=folder_path,
            has_csv_exports=has_csv_exports,
            dashboard_index=dashboard_index,
        )

        manifest[contract][timeframe][date_range] = {
            "png": png_files,
            "html": html_files,
            "csv": [],
            "has_csv_exports": has_csv_exports,
            "start_date": metadata["start"],
            "end_date": metadata["end"],
            "start": metadata["start"],
            "end": metadata["end"],
            "contract": contract,
            "timeframe": timeframe,
            "date_range": date_range,
            "dashboard_index": dashboard_index,
            "canonical": False,
            **classification,
        }

    apply_cross_entry_suppression(manifest)
    apply_mnqh25_public_only_policy(manifest)
    mark_canonical_entries(manifest)

    sorted_contracts = sorted(manifest.keys())
    sorted_manifest = {}
    for contract in sorted_contracts:
        sorted_manifest[contract] = {}
        timeframes = sorted(manifest[contract].keys(), key=extract_timeframe_minutes)
        for timeframe in timeframes:
            sorted_manifest[contract][timeframe] = {}
            date_ranges = sorted(
                manifest[contract][timeframe].keys(),
                key=lambda dr: manifest[contract][timeframe][dr]["start_date"],
            )
            for date_range in date_ranges:
                entry = manifest[contract][timeframe][date_range]
                sorted_manifest[contract][timeframe][date_range] = {
                    k: v for k, v in entry.items() if k != "has_csv_exports"
                }

    manifest_file_path = MANIFEST_FILE
    manifest_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_file_path, "w", encoding="utf-8") as f:
        json.dump(sorted_manifest, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Manifest generated: {manifest_file_path}")
    print(f"  Contracts: {len(sorted_manifest)}")
    total_runs = sum(len(tf) for contract in sorted_manifest.values() for tf in contract.values())
    active_runs = sum(
        1
        for contract in sorted_manifest.values()
        for tf in contract.values()
        for entry in tf.values()
        if entry.get("active")
    )
    print(f"  Total report runs: {total_runs}")
    print(f"  Active gallery routes: {active_runs}")
    print("=" * 60)


if __name__ == "__main__":
    generate_manifest()

#!/usr/bin/env python3
"""
generate_manifest.py

Scans the reports directory and generates a manifest.json file that
organizes all reports by contract, timeframe, and date range.

Scans both legacy canonical folders (CONTRACT_YYYYMMDD-YYYYMMDD_TF) and
validated public slug folders (vwap-*-*-historical-sample-*). Preserves
validated routes from the previous manifest when still present on disk.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Reports directory (relative to this script)
if (Path(__file__).parent.parent / "docs" / "reports").exists():
    REPORTS_DIR = Path(__file__).parent.parent / "docs" / "reports"
    MANIFEST_FILE = Path(__file__).parent.parent / "docs" / "manifest.json"
else:
    REPORTS_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports"
    MANIFEST_FILE = Path(__file__).parent.parent / "site" / "docs" / "manifest.json"

FOLDER_PATTERN = re.compile(r"^(?P<contract>[A-Z0-9]+)_(?P<start>\d{8})-(?P<end>\d{8})_(?P<tf>\d+m)$")
SLUG_FOLDER_PATTERN = re.compile(
    r"^vwap-(?P<root>[a-z0-9]+)-(?P<contract>[a-z0-9]+)-(?P<tf>1m|5m|15m|30m)"
    r"(?:-(?P<partial>partial))?-historical-sample-(?P<stamp>\d{8})$",
    re.IGNORECASE,
)
CONTRACT_PREFIX_IN_FILENAME = re.compile(r"^([A-Z0-9]+)_(\d{8})-(\d{8})_(\d+m)(?:_|\.)")
FORBIDDEN_HTML_PATTERNS = (
    re.compile(r"LOCAL\s+DATABASE", re.IGNORECASE),
    re.compile(r"file://", re.IGNORECASE),
    re.compile(r"[a-zA-Z]:\\"),
)


def file_belongs_to_folder(filename: str, folder_contract: str, folder_tf: str | None = None) -> bool:
    m = CONTRACT_PREFIX_IN_FILENAME.match(filename)
    if not m:
        return True
    if m.group(1) != folder_contract:
        return False
    if folder_tf and m.lastindex >= 2 and m.group(2) != folder_tf:
        return False
    return True


def parse_folder_name(folder_name: str) -> dict | None:
    match = FOLDER_PATTERN.match(folder_name)
    if not match:
        return None
    data = match.groupdict()
    data["date_range"] = f"{data['start']}-{data['end']}"
    return data


def parse_slug_folder_name(folder_name: str) -> dict | None:
    match = SLUG_FOLDER_PATTERN.match(folder_name)
    if not match:
        return None
    contract = match.group("contract").upper()
    return {
        "contract": contract,
        "tf": match.group("tf"),
        "partial": bool(match.group("partial")),
        "stamp": match.group("stamp"),
        "root": match.group("root").upper(),
    }


def extract_timeframe_minutes(tf_str: str) -> int:
    match = re.match(r"(\d+)m", tf_str)
    return int(match.group(1)) if match else 0


def resolve_dashboard_index(folder_name: str, folder_path: Path) -> str | None:
    dashboards_index = folder_path / "dashboards" / "index.html"
    root_index = folder_path / "index.html"
    if dashboards_index.is_file():
        return f"reports/{folder_name}/dashboards/index.html"
    if root_index.is_file():
        return f"reports/{folder_name}/index.html"
    return None


def infer_date_range_from_dashboards(folder_path: Path, contract: str, timeframe: str) -> str | None:
    dashboards = folder_path / "dashboards"
    if not dashboards.is_dir():
        return None
    for file_path in sorted(dashboards.iterdir()):
        if file_path.suffix.lower() != ".html" or file_path.name == "index.html":
            continue
        m = CONTRACT_PREFIX_IN_FILENAME.match(file_path.name)
        if not m or m.group(1) != contract or m.group(4) != timeframe:
            continue
        return f"{m.group(2)}-{m.group(3)}"
    return None


def folder_has_csv_exports(folder_path: Path) -> bool:
    for file_path in folder_path.rglob("*.csv"):
        if file_path.is_file():
            return True
    return False


def html_passes_public_safety(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return not any(p.search(text) for p in FORBIDDEN_HTML_PATTERNS)


def route_valid_on_disk(entry: dict, reports_dir: Path) -> bool:
    dashboard_index = entry.get("dashboard_index")
    if not dashboard_index or not dashboard_index.startswith("reports/"):
        return False
    index_path = reports_dir.parent / dashboard_index
    if not index_path.is_file():
        return False
    folder_name = dashboard_index.removeprefix("reports/").split("/")[0]
    folder_path = reports_dir / folder_name
    if folder_has_csv_exports(folder_path):
        return False
    return html_passes_public_safety(index_path)


def classify_entry(
    *,
    folder_name: str,
    folder_path: Path,
    has_csv_exports: bool,
    dashboard_index: str | None,
) -> dict:
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


def collect_folder_assets(
    folder_path: Path,
    folder_name: str,
    contract: str,
    timeframe: str,
    reports_parent: Path,
) -> tuple[list[str], list[str], list[str], bool]:
    png_files: list[str] = []
    html_files: list[str] = []
    csv_files: list[str] = []

    def _scan_file(file_path: Path) -> None:
        if not file_path.is_file():
            return
        if not file_belongs_to_folder(file_path.name, contract, timeframe):
            return
        relative_path_str = str(file_path.relative_to(reports_parent)).replace("\\", "/")
        ext = file_path.suffix.lower()
        if ext == ".png":
            png_files.append(relative_path_str)
        elif ext == ".html":
            html_files.append(relative_path_str)
        elif ext == ".csv":
            csv_files.append(relative_path_str)

    for file_path in folder_path.iterdir():
        _scan_file(file_path)

    dashboards_path = folder_path / "dashboards"
    if dashboards_path.is_dir():
        for file_path in dashboards_path.iterdir():
            _scan_file(file_path)

    png_files.sort()
    html_files.sort()
    csv_files.sort()
    return png_files, html_files, csv_files, bool(csv_files)


def build_manifest_entry(
    *,
    folder_name: str,
    folder_path: Path,
    contract: str,
    timeframe: str,
    date_range: str,
    start: str,
    end: str,
    reports_parent: Path,
) -> dict | None:
    dashboard_index = resolve_dashboard_index(folder_name, folder_path)
    if not dashboard_index:
        return None
    png_files, html_files, csv_files, has_csv_exports = collect_folder_assets(
        folder_path, folder_name, contract, timeframe, reports_parent
    )
    index_path = folder_path / "dashboards" / "index.html"
    if not index_path.is_file():
        index_path = folder_path / "index.html"
    if not html_passes_public_safety(index_path):
        return None
    classification = classify_entry(
        folder_name=folder_name,
        folder_path=folder_path,
        has_csv_exports=has_csv_exports,
        dashboard_index=dashboard_index,
    )
    if not classification["active"]:
        return None
    return {
        "png": png_files,
        "html": html_files,
        "csv": [],
        "has_csv_exports": has_csv_exports,
        "start_date": start,
        "end_date": end,
        "start": start,
        "end": end,
        "contract": contract,
        "timeframe": timeframe,
        "date_range": date_range,
        "dashboard_index": dashboard_index,
        "canonical": False,
        **classification,
    }


def scan_legacy_folders(reports_dir: Path) -> dict:
    manifest: dict = defaultdict(lambda: defaultdict(dict))
    reports_parent = reports_dir.parent
    for folder_path in sorted(reports_dir.iterdir()):
        if not folder_path.is_dir():
            continue
        metadata = parse_folder_name(folder_path.name)
        if not metadata:
            continue
        entry = build_manifest_entry(
            folder_name=folder_path.name,
            folder_path=folder_path,
            contract=metadata["contract"],
            timeframe=metadata["tf"],
            date_range=metadata["date_range"],
            start=metadata["start"],
            end=metadata["end"],
            reports_parent=reports_parent,
        )
        if entry:
            manifest[metadata["contract"]][metadata["tf"]][metadata["date_range"]] = entry
    return manifest


def scan_slug_folders(reports_dir: Path) -> dict:
    manifest: dict = defaultdict(lambda: defaultdict(dict))
    reports_parent = reports_dir.parent
    for folder_path in sorted(reports_dir.iterdir()):
        if not folder_path.is_dir():
            continue
        metadata = parse_slug_folder_name(folder_path.name)
        if not metadata:
            continue
        date_range = infer_date_range_from_dashboards(
            folder_path, metadata["contract"], metadata["tf"]
        )
        if not date_range:
            continue
        start, end = date_range.split("-", 1)
        entry = build_manifest_entry(
            folder_name=folder_path.name,
            folder_path=folder_path,
            contract=metadata["contract"],
            timeframe=metadata["tf"],
            date_range=date_range,
            start=start,
            end=end,
            reports_parent=reports_parent,
        )
        if entry:
            manifest[metadata["contract"]][metadata["tf"]][date_range] = entry
    return manifest


def merge_manifest_dicts(base: dict, overlay: dict) -> dict:
    for contract, tfs in overlay.items():
        for timeframe, ranges in tfs.items():
            for date_range, entry in ranges.items():
                if date_range not in base.setdefault(contract, {}).setdefault(timeframe, {}):
                    base[contract][timeframe][date_range] = entry
    return base


def preserve_validated_routes(
    manifest: dict,
    previous: dict | None,
    reports_dir: Path,
) -> tuple[dict, list[tuple[str, str, str]]]:
    preserved: list[tuple[str, str, str]] = []
    if not previous:
        return manifest, preserved
    for contract, tfs in previous.items():
        for timeframe, ranges in tfs.items():
            for date_range, entry in ranges.items():
                if not entry.get("active") or not entry.get("dashboard_index"):
                    continue
                if date_range in manifest.get(contract, {}).get(timeframe, {}):
                    continue
                clean_entry = {k: v for k, v in entry.items() if k != "has_csv_exports"}
                if not route_valid_on_disk(clean_entry, reports_dir):
                    continue
                clean_entry["canonical"] = False
                manifest.setdefault(contract, {}).setdefault(timeframe, {})[date_range] = clean_entry
                preserved.append((contract, timeframe, date_range))
    return manifest, preserved


def audit_route_removals(previous: dict | None, current: dict) -> list[dict]:
    if not previous:
        return []
    removed = []
    for contract, tfs in previous.items():
        for timeframe, ranges in tfs.items():
            for date_range, entry in ranges.items():
                if not entry.get("active"):
                    continue
                still = current.get(contract, {}).get(timeframe, {}).get(date_range)
                if still and still.get("active"):
                    continue
                removed.append(
                    {
                        "contract": contract,
                        "timeframe": timeframe,
                        "date_range": date_range,
                        "dashboard_index": entry.get("dashboard_index", ""),
                        "reason": "not_regenerated_and_not_preserved",
                    }
                )
    return removed


def apply_cross_entry_suppression(manifest: dict) -> None:
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


def sort_manifest(manifest: dict) -> dict:
    sorted_manifest: dict = {}
    for contract in sorted(manifest.keys()):
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
    return sorted_manifest


def load_manifest_file(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def count_active_routes(manifest: dict, prefix: str | None = None) -> int:
    count = 0
    for contract, tfs in manifest.items():
        if prefix == "6E":
            if not contract.startswith("6E"):
                continue
        elif prefix and not contract.startswith(prefix):
            continue
        for ranges in tfs.values():
            for entry in ranges.values():
                if entry.get("active") and entry.get("dashboard_index"):
                    count += 1
    return count


def generate_manifest(
    reports_dir: Path | None = None,
    manifest_file: Path | None = None,
    *,
    preserve_validated: bool = True,
    write: bool = True,
    verbose: bool = True,
) -> dict:
    reports_dir = reports_dir or REPORTS_DIR
    manifest_file = manifest_file or MANIFEST_FILE

    if not reports_dir.exists():
        raise FileNotFoundError(f"Reports directory does not exist: {reports_dir}")

    if verbose:
        print(f"Scanning reports directory: {reports_dir}")

    previous = load_manifest_file(manifest_file) if preserve_validated else None

    manifest = scan_legacy_folders(reports_dir)
    slug_manifest = scan_slug_folders(reports_dir)
    merge_manifest_dicts(manifest, slug_manifest)

    preserved_keys: list[tuple[str, str, str]] = []
    if preserve_validated:
        manifest, preserved_keys = preserve_validated_routes(manifest, previous, reports_dir)

    apply_cross_entry_suppression(manifest)
    apply_mnqh25_public_only_policy(manifest)
    mark_canonical_entries(manifest)

    sorted_manifest = sort_manifest(manifest)
    removals = audit_route_removals(previous, sorted_manifest)

    if verbose:
        print(f"  Preserved validated routes: {len(preserved_keys)}")
        print(f"  Removed active routes vs previous: {len(removals)}")
        print(f"  MES active routes: {count_active_routes(sorted_manifest, 'MES')}")
        print(f"  MCL active routes: {count_active_routes(sorted_manifest, 'MCL')}")

    if write:
        manifest_file.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(sorted_manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")
        if verbose:
            total_runs = sum(len(tf) for contract in sorted_manifest.values() for tf in contract.values())
            active_runs = sum(
                1
                for contract in sorted_manifest.values()
                for tf in contract.values()
                for entry in tf.values()
                if entry.get("active")
            )
            print(f"Manifest generated: {manifest_file}")
            print(f"  Contracts: {len(sorted_manifest)}")
            print(f"  Total report runs: {total_runs}")
            print(f"  Active gallery routes: {active_runs}")
            print("=" * 60)

    return {
        "manifest": sorted_manifest,
        "preserved_validated_count": len(preserved_keys),
        "removed_active_routes": removals,
    }


def main() -> int:
    try:
        generate_manifest()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

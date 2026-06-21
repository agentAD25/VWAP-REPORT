#!/usr/bin/env python3
"""Additive NQ entries to docs/manifest.json for gallery routing (idempotent)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
REPORTS = DOCS / "reports"
MANIFEST = DOCS / "manifest.json"
BUNDLE_MANIFEST = (
    REPO.parent
    / "supabase-opti-database"
    / "configs/vwap_report/instruments/nq_all20_public_manifest_20260525.json"
)


NQ_CONTRACT_PREFIXES = ("NQH25", "NQM25", "NQU25", "NQZ25", "NQH26")


def is_nq_contract(contract: str) -> bool:
    return contract.startswith("NQ") and not contract.startswith("MNQ")


def dashboard_index_exists(entry: dict) -> bool:
    """Return True when the manifest dashboard_index resolves to a local file."""
    idx = entry.get("dashboard_index", "")
    if not idx:
        return False
    return (DOCS / idx).is_file()


def deactivate_legacy_nq_entries(manifest: dict) -> int:
    """Deactivate invalid NQ routes only; preserve active routes with local dashboards."""
    deactivated = 0
    for contract in list(manifest.keys()):
        if not is_nq_contract(contract):
            continue
        for tf, ranges in manifest[contract].items():
            if not isinstance(ranges, dict):
                continue
            for _dr, entry in ranges.items():
                if not isinstance(entry, dict) or not entry.get("active"):
                    continue
                if dashboard_index_exists(entry):
                    continue
                invalid = (
                    entry.get("status") == "LEGACY_WITH_DATA_EXPORTS"
                    or entry.get("public_safe") is False
                )
                if invalid or "vwap-nq-" not in entry.get("dashboard_index", ""):
                    entry["active"] = False
                    entry["canonical"] = False
                    deactivated += 1
    return deactivated


def load_nq_bundles() -> list[tuple[str, str, str, str, str, bool]]:
    raw = json.loads(BUNDLE_MANIFEST.read_text(encoding="utf-8"))
    rows: list[tuple[str, str, str, str, str, bool]] = []
    for item in raw["bundles"]:
        start = item["start"].replace("-", "")
        end = item["end"].replace("-", "")
        rows.append(
            (
                item["contract"],
                item["timeframe"],
                item["slug"],
                start,
                end,
                bool(item.get("partial", False)),
            )
        )
    return rows


def scan_assets(slug: str) -> tuple[list[str], list[str]]:
    folder = REPORTS / slug
    dash = folder / "dashboards"
    if not dash.is_dir():
        raise FileNotFoundError(f"Missing dashboards: {dash}")
    png: list[str] = []
    html: list[str] = []
    for f in sorted(dash.iterdir()):
        if not f.is_file():
            continue
        rel = f"reports/{slug}/dashboards/{f.name}".replace("\\", "/")
        if f.suffix.lower() == ".png":
            png.append(rel)
        elif f.suffix.lower() == ".html":
            html.append(rel)
    if not any(p.endswith("index.html") for p in html):
        raise FileNotFoundError(f"Missing dashboards/index.html under {slug}")
    return png, html


def build_entry(
    contract: str,
    tf: str,
    slug: str,
    start: str,
    end: str,
    *,
    partial: bool,
) -> dict:
    png, html = scan_assets(slug)
    date_range = f"{start}-{end}"
    return {
        "png": png,
        "html": html,
        "csv": [],
        "start_date": start,
        "end_date": end,
        "start": start,
        "end": end,
        "contract": contract,
        "timeframe": tf,
        "date_range": date_range,
        "dashboard_index": f"reports/{slug}/dashboards/index.html",
        "canonical": True,
        "status": "CURRENT_CERTIFIED_PUBLIC",
        "active": True,
        "public_safe": True,
    }


def apply_patch(*, dry_run: bool = False) -> dict:
    original: dict = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest: dict = json.loads(MANIFEST.read_text(encoding="utf-8"))
    before_keys = set(manifest.keys())
    added = 0
    reused = 0
    deactivated = deactivate_legacy_nq_entries(manifest)
    nq_bundles = load_nq_bundles()
    for contract, tf, slug, start, end, partial in nq_bundles:
        if not (REPORTS / slug).is_dir():
            raise FileNotFoundError(f"Missing staged report {slug}")
        entry = build_entry(contract, tf, slug, start, end, partial=partial)
        dr = entry["date_range"]
        manifest.setdefault(contract, {})
        manifest[contract].setdefault(tf, {})
        if dr in manifest[contract][tf]:
            existing = manifest[contract][tf][dr]
            if existing.get("dashboard_index") == entry["dashboard_index"]:
                manifest[contract][tf][dr] = entry
                reused += 1
                continue
            if dashboard_index_exists(existing):
                continue
            raise RuntimeError(
                f"{contract}/{tf}/{dr} exists with different dashboard_index: "
                f"{existing.get('dashboard_index')}"
            )
        manifest[contract][tf][dr] = entry
        added += 1

    after_keys = set(manifest.keys())
    if not before_keys.issubset(after_keys):
        raise RuntimeError("manifest keys removed")
    for k in before_keys:
        if k.startswith("NQ"):
            continue
        if manifest.get(k) != original.get(k):
            raise RuntimeError(f"non-NQ key modified: {k}")
    if manifest.get("MNQH25") != original.get("MNQH25"):
        raise RuntimeError("MNQH25 modified")
    if manifest.get("MESH25") != original.get("MESH25"):
        raise RuntimeError("MESH25 modified")

    preserve = ("NQM26", "NQU25", "NQZ25")
    for contract in preserve:
        for tf, ranges in original.get(contract, {}).items():
            for dr, entry in ranges.items():
                if not isinstance(entry, dict) or not entry.get("active"):
                    continue
                patched = manifest.get(contract, {}).get(tf, {}).get(dr)
                if not patched or not patched.get("active"):
                    raise RuntimeError(f"preservation failed: {contract}/{tf}/{dr}")

    result = {
        "added": added,
        "reused": reused,
        "legacy_deactivated": deactivated,
        "nq_contracts": sorted({b[0] for b in nq_bundles}),
        "dry_run": dry_run,
    }
    if not dry_run:
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch NQ gallery manifest entries")
    parser.add_argument("--dry-run", action="store_true", help="Validate patch without writing manifest")
    args = parser.parse_args()
    try:
        result = apply_patch(dry_run=args.dry_run)
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""
Idempotent sync of approved MNQH25 5m public-safe sample into VWAP-REPORT docs.

Copies:
  1) Full sample tree -> docs/reports/vwap-mnqh25-5m-historical-sample-20260519/
  2) dashboards HTML+PNG only -> docs/reports/MNQH25_20241216-20250314_5m/dashboards/
     (for manifest.json gallery registration via generate_manifest.py)

Does not copy CSV/JSON/parquet. Does not modify other report folders.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
DEFAULT_SOURCE = (
    Path(__file__).resolve().parent.parent.parent
    / "supabase-opti-database"
    / "docs"
    / "reports"
    / "vwap-mnqh25-5m-historical-sample-20260519"
)

SAMPLE_SLUG_DIR = "vwap-mnqh25-5m-historical-sample-20260519"
MANIFEST_FOLDER = "MNQH25_20241216-20250314_5m"

BLOCKED_SUFFIXES = {".csv", ".json", ".parquet", ".txt"}
ALLOWED_SUFFIXES = {".html", ".png", ".md"}

CORE_STEMS = (
    "daily_max_extensions",
    "dashboard_all_events",
    "dashboard_crosses",
    "extension_tail_metrics",
    "heatmap_time_of_day_x_reaction",
    "hold_fail_rates",
    "mfe_mae_by_event_window",
    "oos_by_month",
    "regime_segment_grid",
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _inventory(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(
        str(p.relative_to(root)).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file()
    )


def _copy_tree_idempotent(src: Path, dest: Path) -> tuple[int, int]:
    """Copy allowed files; return (copied, skipped_unchanged)."""
    copied = 0
    unchanged = 0
    for src_file in sorted(src.rglob("*")):
        if not src_file.is_file():
            continue
        rel = src_file.relative_to(src)
        if src_file.suffix.lower() in BLOCKED_SUFFIXES:
            continue
        if src_file.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        if src_file.name == "README_PUBLIC_SAMPLE.md" or rel.parts[0] == "dashboards" or rel.name.endswith(".md"):
            pass  # allow md only at sample root
        dest_file = dest / rel
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        if dest_file.is_file():
            if _sha256_file(src_file) == _sha256_file(dest_file):
                unchanged += 1
                continue
        shutil.copy2(src_file, dest_file)
        copied += 1
    return copied, unchanged


def _scan_public_safety(target: Path) -> dict:
    errors: list[str] = []
    files: list[str] = []
    for p in sorted(target.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(target)).replace("\\", "/")
        files.append(rel)
        ext = p.suffix.lower()
        if ext in BLOCKED_SUFFIXES:
            errors.append(f"blocked_suffix:{rel}")
        if "audit_bar_lattice" in p.name.lower() or "vwap_events" in p.name.lower():
            errors.append(f"blocked_stem:{rel}")
        if p.name.endswith("_data.json") or p.name in {
            "report_params.json",
            "report_lineage.json",
            "manifest.json",
        }:
            errors.append(f"forbidden_name:{rel}")
    combined = "\n".join(
        f.read_text(encoding="utf-8", errors="replace")
        for f in target.rglob("*.html")
    )
    if re.search(r"LOCAL\s+DATABASE", combined, re.I):
        errors.append("local_database_path_in_html")
    if re.search(r"[A-Za-z]:\\", combined):
        errors.append("windows_absolute_path_in_html")
    if "Generic dashboard for " in combined:
        errors.append("generic_csv_fallback_dashboard")
    for f in target.rglob("*.html"):
        tx = f.read_text(encoding="utf-8", errors="replace")
        if re.search(r'href\s*=\s*"[^"]*\.csv"', tx, re.I):
            errors.append(f"csv_href:{f.name}")
    return {"files": files, "errors": errors, "passed": len(errors) == 0}


def sync(source: Path, *, force_clean: bool = False) -> dict:
    if not source.is_dir():
        raise FileNotFoundError(f"Source sample missing: {source}")

    slug_dest = DOCS / "reports" / SAMPLE_SLUG_DIR
    manifest_dest = DOCS / "reports" / MANIFEST_FOLDER / "dashboards"

    if force_clean:
        if slug_dest.is_dir():
            shutil.rmtree(slug_dest)
        if manifest_dest.is_dir():
            shutil.rmtree(manifest_dest)

    # Full public sample slug folder
    slug_dest.mkdir(parents=True, exist_ok=True)
    c1, u1 = _copy_tree_idempotent(source, slug_dest)

    # Gallery registration folder (dashboards only)
    src_dash = source / "dashboards"
    if not src_dash.is_dir():
        raise FileNotFoundError(f"Missing dashboards in source: {src_dash}")
    manifest_dest.mkdir(parents=True, exist_ok=True)
    c2, u2 = 0, 0
    for f in sorted(src_dash.iterdir()):
        if not f.is_file():
            continue
        if f.suffix.lower() not in {".html", ".png"}:
            continue
        dest_f = manifest_dest / f.name
        if dest_f.is_file() and _sha256_file(f) == _sha256_file(dest_f):
            u2 += 1
        else:
            shutil.copy2(f, dest_f)
            c2 += 1

    # .nojekyll for Jekyll bypass
    nojekyll = DOCS / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.touch()

    scan_slug = _scan_public_safety(slug_dest)
    scan_manifest = _scan_public_safety(manifest_dest)

    audit_dir = REPO_ROOT / "out" / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "slug_dest": str(slug_dest),
        "manifest_dest": str(manifest_dest),
        "copied_slug": c1,
        "unchanged_slug": u1,
        "copied_manifest_dashboards": c2,
        "unchanged_manifest_dashboards": u2,
        "slug_inventory": _inventory(slug_dest),
        "manifest_inventory": _inventory(manifest_dest),
        "scan_slug": scan_slug,
        "scan_manifest": scan_manifest,
    }
    audit_path = audit_dir / "mnqh25_public_sample_sync_latest.json"
    audit_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return payload


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Sync MNQH25 public sample into VWAP-REPORT")
    p.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    p.add_argument("--force-clean", action="store_true")
    args = p.parse_args(argv)

    result = sync(args.source.resolve(), force_clean=args.force_clean)
    if not result["scan_slug"]["passed"] or not result["scan_manifest"]["passed"]:
        print("PUBLIC_SAFETY_FAIL", file=sys.stderr)
        print(result["scan_slug"]["errors"], result["scan_manifest"]["errors"], file=sys.stderr)
        return 1
    print("MNQH25_PUBLIC_SYNC_PASS")
    print(f"slug files: {len(result['slug_inventory'])}")
    print(f"manifest dashboards files: {len(result['manifest_inventory'])}")
    print(f"audit: {REPO_ROOT / 'out' / 'audits' / 'mnqh25_public_sample_sync_latest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

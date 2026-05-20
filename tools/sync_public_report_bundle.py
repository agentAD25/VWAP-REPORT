#!/usr/bin/env python3
"""
Idempotent sync of a certified public-safe VWAP report bundle into VWAP-REPORT docs.

Copies HTML/PNG/MD only, updates canonical folder + optional slug alias,
optionally removes superseded legacy folders for the same contract/timeframe,
regenerates manifest.json, and writes an audit summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
REPORTS_DIR = DOCS / "reports"

BLOCKED_SUFFIXES = {".csv", ".json", ".parquet", ".txt"}
ALLOWED_SUFFIXES = {".html", ".png", ".md"}
FOLDER_PATTERN = re.compile(r"^(?P<contract>[A-Z0-9]+)_(?P<start>\d{8})-(?P<end>\d{8})_(?P<tf>\d+m)$")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(
        str(path.relative_to(root)).replace("\\", "/")
        for path in root.rglob("*")
        if path.is_file()
    )


def canonical_folder_name(contract: str, start: str, end: str, timeframe: str) -> str:
    return f"{contract}_{start}-{end}_{timeframe}"


def _copy_allowed_tree(src: Path, dest: Path) -> tuple[int, int]:
    copied = 0
    unchanged = 0
    for src_file in sorted(src.rglob("*")):
        if not src_file.is_file():
            continue
        ext = src_file.suffix.lower()
        if ext in BLOCKED_SUFFIXES:
            continue
        if ext not in ALLOWED_SUFFIXES:
            continue
        rel = src_file.relative_to(src)
        dest_file = dest / rel
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        if dest_file.is_file() and _sha256_file(src_file) == _sha256_file(dest_file):
            unchanged += 1
            continue
        shutil.copy2(src_file, dest_file)
        copied += 1
    return copied, unchanged


def _copy_dashboards_only(src_dashboards: Path, dest_dashboards: Path) -> tuple[int, int]:
    copied = 0
    unchanged = 0
    if not src_dashboards.is_dir():
        raise FileNotFoundError(f"Missing dashboards in source: {src_dashboards}")
    dest_dashboards.mkdir(parents=True, exist_ok=True)
    for src_file in sorted(src_dashboards.iterdir()):
        if not src_file.is_file():
            continue
        if src_file.suffix.lower() not in {".html", ".png"}:
            continue
        dest_file = dest_dashboards / src_file.name
        if dest_file.is_file() and _sha256_file(src_file) == _sha256_file(dest_file):
            unchanged += 1
            continue
        shutil.copy2(src_file, dest_file)
        copied += 1
    return copied, unchanged


def _folder_has_csv_exports(folder: Path) -> bool:
    if not folder.is_dir():
        return False
    return any(path.suffix.lower() == ".csv" for path in folder.rglob("*") if path.is_file())


def _folder_is_legacy_corrupt(folder: Path, target_folder: str) -> bool:
    if folder.name == target_folder:
        return False
    metadata = FOLDER_PATTERN.match(folder.name)
    if not metadata:
        return False
    has_dashboards_gallery = (folder / "dashboards" / "index.html").is_file()
    if has_dashboards_gallery and not _folder_has_csv_exports(folder):
        return False
    return _folder_has_csv_exports(folder) or not has_dashboards_gallery


def _purge_legacy_root_files(canonical_dest: Path) -> list[str]:
    """Remove stale root-level artifacts; keep dashboards/ subfolder only."""
    removed: list[str] = []
    if not canonical_dest.is_dir():
        return removed
    for item in list(canonical_dest.iterdir()):
        if item.name == "dashboards":
            continue
        if item.is_file():
            item.unlink()
            removed.append(item.name)
    return removed


def _find_replace_candidates(
    contract: str,
    timeframe: str,
    target_folder: str,
) -> list[Path]:
    candidates: list[Path] = []
    for folder in sorted(REPORTS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        metadata = FOLDER_PATTERN.match(folder.name)
        if not metadata:
            continue
        if metadata.group("contract") != contract or metadata.group("tf") != timeframe:
            continue
        if folder.name == target_folder:
            continue
        if _folder_is_legacy_corrupt(folder, target_folder):
            candidates.append(folder)
    return candidates


def _scan_public_safety(target: Path) -> dict:
    errors: list[str] = []
    files: list[str] = []
    for path in sorted(target.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(target)).replace("\\", "/")
        files.append(rel)
        ext = path.suffix.lower()
        if ext in BLOCKED_SUFFIXES:
            errors.append(f"blocked_suffix:{rel}")
        if "audit_bar_lattice" in path.name.lower() or path.name.lower() == "vwap_events.html":
            errors.append(f"blocked_stem:{rel}")
        if path.name.endswith("_data.json") or path.name in {
            "report_params.json",
            "report_lineage.json",
        }:
            errors.append(f"forbidden_name:{rel}")

    combined = "\n".join(
        html.read_text(encoding="utf-8", errors="replace")
        for html in target.rglob("*.html")
    )
    if re.search(r"LOCAL\s+DATABASE", combined, re.I):
        errors.append("local_database_path_in_html")
    if re.search(r"[A-Za-z]:\\", combined):
        errors.append("windows_absolute_path_in_html")
    if "Generic dashboard for " in combined:
        errors.append("generic_csv_fallback_dashboard")
    for html in target.rglob("*.html"):
        text = html.read_text(encoding="utf-8", errors="replace")
        if re.search(r'href\s*=\s*"[^"]*\.csv"', text, re.I):
            errors.append(f"csv_href:{html.name}")

    return {"files": files, "errors": errors, "passed": len(errors) == 0}


def _regenerate_manifest() -> None:
    script = REPO_ROOT / "tools" / "generate_manifest.py"
    subprocess.run([sys.executable, str(script)], check=True, cwd=REPO_ROOT)


def sync_bundle(
    *,
    source: Path,
    contract: str,
    timeframe: str,
    start: str,
    end: str,
    target_folder: str | None,
    slug_alias: str | None,
    replace_same_contract_timeframe: bool,
    approval: str,
) -> dict:
    required_prefix = (
        f"GO_REPLACE_PUBLIC_REPORT_{contract.upper()}_{timeframe.upper()}_CERTIFIED_"
    )
    if not approval.startswith(required_prefix) or len(approval) <= len(required_prefix):
        raise ValueError(
            f"Invalid approval. Required prefix: {required_prefix}<tag> "
            f"(example: {required_prefix}20260519)"
        )

    source = source.resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Source bundle missing: {source}")

    target_name = target_folder or canonical_folder_name(contract, start, end, timeframe)
    if not FOLDER_PATTERN.match(target_name):
        raise ValueError(f"Invalid target folder name: {target_name}")

    canonical_dest = REPORTS_DIR / target_name
    dashboards_dest = canonical_dest / "dashboards"
    src_dashboards = source / "dashboards"
    deleted: list[str] = []
    purged_root: list[str] = []

    if replace_same_contract_timeframe:
        for folder in _find_replace_candidates(contract, timeframe, target_name):
            shutil.rmtree(folder)
            deleted.append(folder.name)
        if canonical_dest.is_dir():
            purged_root = _purge_legacy_root_files(canonical_dest)

    canonical_dest.mkdir(parents=True, exist_ok=True)
    slug_copied = (0, 0)
    slug_dest: Path | None = None
    if slug_alias:
        slug_dest = REPORTS_DIR / slug_alias
        slug_dest.mkdir(parents=True, exist_ok=True)
        slug_copied = _copy_allowed_tree(source, slug_dest)

    dash_copied = _copy_dashboards_only(src_dashboards, dashboards_dest)

    nojekyll = DOCS / ".nojekyll"
    if not nojekyll.exists():
        nojekyll.touch()

    scan_canonical = _scan_public_safety(dashboards_dest)
    scan_slug = (
        _scan_public_safety(slug_dest)
        if slug_dest is not None
        else {"files": [], "errors": [], "passed": True}
    )

    if not scan_canonical["passed"] or not scan_slug["passed"]:
        raise RuntimeError(
            f"Public safety failed: canonical={scan_canonical['errors']} "
            f"slug={scan_slug['errors']}"
        )

    _regenerate_manifest()

    audit_dir = REPO_ROOT / "out" / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "synced_at": datetime.now(timezone.utc).isoformat(),
        "approval": approval,
        "source": str(source),
        "contract": contract,
        "timeframe": timeframe,
        "start": start,
        "end": end,
        "target_folder": target_name,
        "slug_alias": slug_alias,
        "replace_same_contract_timeframe": replace_same_contract_timeframe,
        "deleted_folders": deleted,
        "purged_root_files": purged_root,
        "canonical_dest": str(canonical_dest),
        "slug_dest": str(slug_dest) if slug_dest else None,
        "copied_slug": slug_copied[0],
        "unchanged_slug": slug_copied[1],
        "copied_dashboards": dash_copied[0],
        "unchanged_dashboards": dash_copied[1],
        "canonical_inventory": _inventory(dashboards_dest),
        "slug_inventory": _inventory(slug_dest) if slug_dest else [],
        "scan_canonical": scan_canonical,
        "scan_slug": scan_slug,
    }
    audit_name = (
        f"public_report_sync_{contract.lower()}_{timeframe}_{start}_{end}_latest.json"
    )
    audit_path = audit_dir / audit_name
    audit_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["audit_path"] = str(audit_path)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Sync certified public-safe report bundle into VWAP-REPORT"
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--timeframe", required=True, help="e.g. 5m")
    parser.add_argument("--start", required=True, help="YYYYMMDD")
    parser.add_argument("--end", required=True, help="YYYYMMDD")
    parser.add_argument(
        "--target-folder",
        default=None,
        help="Canonical folder under docs/reports/ (default: CONTRACT_START-END_TF)",
    )
    parser.add_argument(
        "--keep-slug-alias",
        default=None,
        help="Optional slug folder name under docs/reports/",
    )
    parser.add_argument(
        "--replace-same-contract-timeframe",
        action="store_true",
        help="Remove superseded legacy folders for same contract+timeframe",
    )
    parser.add_argument(
        "--approval",
        required=True,
        help="Explicit operator approval string",
    )
    args = parser.parse_args(argv)

    try:
        result = sync_bundle(
            source=args.source,
            contract=args.contract.upper(),
            timeframe=args.timeframe,
            start=args.start,
            end=args.end,
            target_folder=args.target_folder,
            slug_alias=args.keep_slug_alias,
            replace_same_contract_timeframe=args.replace_same_contract_timeframe,
            approval=args.approval,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"PUBLIC_REPORT_SYNC_FAIL: {exc}", file=sys.stderr)
        return 1

    print("PUBLIC_REPORT_IDEMPOTENT_REPLACE_PASS")
    print(f"target: {result['target_folder']}")
    print(f"deleted: {result['deleted_folders']}")
    print(f"canonical files: {len(result['canonical_inventory'])}")
    if result["slug_dest"]:
        print(f"slug files: {len(result['slug_inventory'])}")
    print(f"audit: {result['audit_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

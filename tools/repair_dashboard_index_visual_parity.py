#!/usr/bin/env python3
"""Rebuild public dashboard index.html for visual parity and gallery navigation."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUPABASE = Path(__file__).resolve().parents[2] / "supabase-opti-database"
sys.path.insert(0, str(SUPABASE / "scripts"))
sys.path.insert(0, str(SUPABASE / "src"))
sys.path.insert(0, str(SUPABASE))

from package_vwap_public_sample_from_bundle import (  # noqa: E402
    CORE_PUBLIC_STEMS,
    _inject_disclosure,
)
from vwap_reports.reporting.dashboards.index_builder import (  # noqa: E402
    build_gallery_back_href,
    build_index,
)
from vwap_reports.reporting.dashboards.screenshot import generate_screenshot  # noqa: E402
from vwap_reports.reporting.filename_utils import contract_to_instrument  # noqa: E402

DOCS = REPO / "docs"
REPORTS = DOCS / "reports"
MANIFEST = DOCS / "manifest.json"

CONTRACT_META: dict[str, dict] = {
    "MNQH25": {
        "start": "20241216",
        "end": "20250314",
        "sessions": 59,
        "iso_start": "2024-12-16",
        "iso_end": "2025-03-14",
    },
    "MNQM25": {
        "start": "20250317",
        "end": "20250613",
        "sessions": 63,
        "iso_start": "2025-03-17",
        "iso_end": "2025-06-13",
    },
    "MNQU25": {
        "start": "20250616",
        "end": "20250912",
        "sessions": 40,
        "iso_start": "2025-06-16",
        "iso_end": "2025-09-12",
    },
    "MNQZ25": {
        "start": "20250914",
        "end": "20251212",
        "sessions": 63,
        "iso_start": "2025-09-14",
        "iso_end": "2025-12-12",
    },
}

LATTICE_BARS: dict[str, int] = {"1m": 390, "5m": 78, "15m": 26, "30m": 13}

FOLDER_RE = re.compile(r"^([A-Z0-9]+)_(\d{8})-(\d{8})_(\d+m)$")
SAMPLE_SLUG_RE = re.compile(
    r"vwap-(?:[a-z]+-)*([a-z]{2,4}[hmuz]\d{2})-(\d+m)(?:-partial)?-historical-sample",
    re.IGNORECASE,
)


@dataclass
class RepairTarget:
    contract: str
    timeframe: str
    dash_dir: Path
    iso_start: str
    iso_end: str
    sessions: int | None
    index_rel: str


class _Cfg:
    def __init__(
        self,
        contract: str,
        timeframe: str,
        start: str,
        end: str,
        sessions: int | None,
    ):
        self.contract = contract
        self.timeframe = timeframe
        self.start = start
        self.end = end
        self.session_type = "RTH"
        self.complete_sessions = sessions
        self.bars_per_session = LATTICE_BARS[timeframe]


def _iso_date(yyyymmdd: str) -> str:
    return f"{yyyymmdd[0:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def _manifest_dashboard_map() -> dict[str, dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    for contract, tfs in manifest.items():
        for tf, ranges in tfs.items():
            for _dr, entry in ranges.items():
                dash_ix = entry.get("dashboard_index") or ""
                dash_ix = dash_ix.replace("\\", "/")
                if "/dashboards/index.html" in dash_ix:
                    out[dash_ix] = {
                        "contract": contract,
                        "timeframe": tf,
                        "iso_start": _iso_date(entry.get("start") or entry.get("start_date", "00010101")[:8]),
                        "iso_end": _iso_date(entry.get("end") or entry.get("end_date", "00010101")[:8]),
                        "sessions": entry.get("complete_sessions"),
                    }
                elif dash_ix.endswith("/index.html"):
                    dashboards_ix = dash_ix.replace("/index.html", "/dashboards/index.html")
                    out[dashboards_ix] = {
                        "contract": contract,
                        "timeframe": tf,
                        "iso_start": _iso_date(entry.get("start") or entry.get("start_date", "00010101")[:8]),
                        "iso_end": _iso_date(entry.get("end") or entry.get("end_date", "00010101")[:8]),
                        "sessions": entry.get("complete_sessions"),
                    }
    return out


def _infer_from_dashboard_html(dash_dir: Path) -> tuple[str, str, str, str] | None:
    for html_path in sorted(dash_dir.glob("*.html")):
        if html_path.name == "index.html":
            continue
        match = re.match(r"^([A-Z0-9]+)_(\d{8})-(\d{8})_(\d+m)_", html_path.name)
        if match:
            contract, start, end, tf = match.groups()
            return contract, tf, _iso_date(start), _iso_date(end)
    return None


def _infer_target(index_path: Path, manifest_map: dict[str, dict]) -> RepairTarget | None:
    index_rel_docs = str(index_path.relative_to(DOCS)).replace("\\", "/")
    index_rel = str(index_path.relative_to(REPO)).replace("\\", "/")
    dash_dir = index_path.parent
    folder = dash_dir.parent.name

    if index_rel_docs in manifest_map:
        meta = manifest_map[index_rel_docs]
        return RepairTarget(
            contract=meta["contract"],
            timeframe=meta["timeframe"],
            dash_dir=dash_dir,
            iso_start=meta["iso_start"],
            iso_end=meta["iso_end"],
            sessions=meta.get("sessions"),
            index_rel=index_rel,
        )

    folder_match = FOLDER_RE.match(folder)
    if folder_match:
        contract, start, end, tf = folder_match.groups()
        return RepairTarget(
            contract=contract,
            timeframe=tf,
            dash_dir=dash_dir,
            iso_start=_iso_date(start),
            iso_end=_iso_date(end),
            sessions=None,
            index_rel=index_rel,
        )

    sample_match = SAMPLE_SLUG_RE.search(folder)
    inferred = _infer_from_dashboard_html(dash_dir)
    if sample_match and inferred:
        contract, tf, iso_start, iso_end = inferred
        return RepairTarget(
            contract=contract,
            timeframe=tf,
            dash_dir=dash_dir,
            iso_start=iso_start,
            iso_end=iso_end,
            sessions=None,
            index_rel=index_rel,
        )

    if inferred:
        contract, tf, iso_start, iso_end = inferred
        return RepairTarget(
            contract=contract,
            timeframe=tf,
            dash_dir=dash_dir,
            iso_start=iso_start,
            iso_end=iso_end,
            sessions=None,
            index_rel=index_rel,
        )

    return None


def certified_dashboard_dirs() -> list[RepairTarget]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows: list[RepairTarget] = []
    for contract, meta in CONTRACT_META.items():
        for tf in ("1m", "5m", "15m", "30m"):
            for _dr, entry in manifest.get(contract, {}).get(tf, {}).items():
                if entry.get("status") != "CURRENT_CERTIFIED_PUBLIC":
                    continue
                dash_ix_path = DOCS / entry["dashboard_index"]
                dash_dir = (
                    dash_ix_path.parent
                    if dash_ix_path.name == "index.html"
                    else dash_ix_path
                )
                index_rel = str((dash_dir / "index.html").relative_to(REPO)).replace(
                    "\\", "/"
                )
                rows.append(
                    RepairTarget(
                        contract=contract,
                        timeframe=tf,
                        dash_dir=dash_dir,
                        iso_start=meta["iso_start"],
                        iso_end=meta["iso_end"],
                        sessions=meta["sessions"],
                        index_rel=index_rel,
                    )
                )
    return rows


def all_dashboard_index_paths() -> list[Path]:
    return sorted(REPORTS.rglob("dashboards/index.html"))


def inventory_rows() -> list[dict[str, str]]:
    manifest_map = _manifest_dashboard_map()
    rows: list[dict[str, str]] = []
    for index_path in all_dashboard_index_paths():
        text = index_path.read_text(encoding="utf-8", errors="replace")
        has_back = "back-to-gallery" in text or "Back to Gallery" in text
        target = _infer_target(index_path, manifest_map)
        if target:
            expected = build_gallery_back_href(target.contract, target.timeframe)
            safe = "yes"
            reason = ""
        else:
            expected = ""
            safe = "no"
            reason = "cannot infer contract/timeframe"
        missing_stems = [
            stem
            for stem in CORE_PUBLIC_STEMS
            if len(list(index_path.parent.glob(f"*_{stem}.html"))) != 1
        ]
        if missing_stems:
            safe = "no"
            reason = f"missing CORE_PUBLIC dashboards: {','.join(missing_stems[:3])}"
        rows.append(
            {
                "path": str(index_path.relative_to(REPO)).replace("\\", "/"),
                "contract": target.contract if target else "",
                "timeframe": target.timeframe if target else "",
                "has_back_to_gallery": "yes" if has_back else "no",
                "expected_back_href": expected,
                "safe_to_repair": safe,
                "reason": reason,
            }
        )
    return rows


def repair_one(target: RepairTarget, *, skip_screenshots: bool) -> None:
    dash_dir = target.dash_dir
    html_files: list[Path] = []
    for stem in CORE_PUBLIC_STEMS:
        matches = sorted(dash_dir.glob(f"*_{stem}.html"))
        if len(matches) != 1:
            raise RuntimeError(
                f"{dash_dir}: expected one *_{stem}.html, found {len(matches)}"
            )
        html_files.append(matches[0])

    contract = target.contract
    timeframe = target.timeframe
    report_params = {
        "instrument": contract_to_instrument(contract) or contract[:3],
        "contract": contract,
        "session_type": "RTH",
        "timeframe": timeframe,
        "date_range": {
            "start_date": target.iso_start,
            "end_date": target.iso_end,
        },
    }
    start_compact = target.iso_start.replace("-", "")
    end_compact = target.iso_end.replace("-", "")
    cfg = _Cfg(contract, timeframe, start_compact, end_compact, target.sessions)

    index_path = build_index(dash_dir, html_files, report_params)
    _inject_disclosure(index_path, policy_on_index=True, cfg=cfg)
    if not skip_screenshots:
        generate_screenshot(index_path, dash_dir)
    print(f"repaired {contract}|{timeframe} -> {index_path.relative_to(REPO)}")


def main() -> int:
    import os

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--scope",
        choices=("certified", "all"),
        default="all",
        help="Repair certified MNQ only or every dashboards/index.html",
    )
    ap.add_argument(
        "--skip-screenshots",
        action="store_true",
        default=True,
        help="Do not regenerate index.png (default: true)",
    )
    ap.add_argument(
        "--write-inventory",
        type=Path,
        default=None,
        help="Optional CSV inventory output path",
    )
    ap.add_argument(
        "--inventory-only",
        action="store_true",
        help="Write inventory and exit without repairing",
    )
    args = ap.parse_args()

    os.chdir(SUPABASE)
    manifest_map = _manifest_dashboard_map()
    inv = inventory_rows()

    if args.write_inventory:
        args.write_inventory.parent.mkdir(parents=True, exist_ok=True)
        with args.write_inventory.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(
                fh,
                fieldnames=[
                    "path",
                    "contract",
                    "timeframe",
                    "has_back_to_gallery",
                    "expected_back_href",
                    "safe_to_repair",
                    "reason",
                ],
            )
            writer.writeheader()
            writer.writerows(inv)

    if args.inventory_only:
        safe = sum(1 for r in inv if r["safe_to_repair"] == "yes")
        print(f"inventory_count={len(inv)} safe_to_repair={safe}")
        return 0

    certified_paths = {
        (REPO / t.index_rel).as_posix()
        for t in certified_dashboard_dirs()
    }
    repaired: list[str] = []
    skipped: list[str] = []
    for row in inv:
        rel = row["path"]
        if row["safe_to_repair"] != "yes":
            skipped.append(rel)
            continue
        if args.scope == "certified" and (REPO / rel).as_posix() not in certified_paths:
            skipped.append(rel)
            continue
        index_path = REPO / rel
        target = _infer_target(index_path, manifest_map)
        if target is None:
            skipped.append(rel)
            continue
        repair_one(target, skip_screenshots=args.skip_screenshots)
        repaired.append(rel)

    audit_dir = (
        SUPABASE
        / "out/audits/vwap_report_generic"
        / f"VWAP_DASHBOARD_BACK_TO_GALLERY_INDEX_REPAIR_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    )
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "repaired_dashboard_indexes.txt").write_text(
        "\n".join(repaired) + ("\n" if repaired else ""),
        encoding="utf-8",
    )
    (audit_dir / "skipped_dashboard_indexes.txt").write_text(
        "\n".join(skipped) + ("\n" if skipped else ""),
        encoding="utf-8",
    )
    print(f"repaired_count={len(repaired)} skipped_count={len(skipped)}")
    print(f"audit_dir={audit_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Repair Chart.js primary dashboard timeframe labels on certified MNQ public reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUPABASE = REPO.parent / "supabase-opti-database"
sys.path.insert(0, str(SUPABASE / "src"))
sys.path.insert(0, str(SUPABASE))

from vwap_reports.reporting.dashboard import normalize_chartjs_dashboard_timeframe_labels  # noqa: E402
from vwap_reports.reporting.dashboards.screenshot import generate_screenshot  # noqa: E402

from audit_report_timeframe_semantics import (  # noqa: E402
    CERTIFIED_MATRIX,
    TIMEFRAMES,
    run_audit,
)

REPORTS_ROOT = REPO / "docs" / "reports"
PRIMARY_STEMS = ("dashboard_all_events", "dashboard_crosses")
CHART_SUBTITLE_RE = re.compile(
    r'<div class="chart-subtitle">MNQ\s*\|\s*RTH\s*\|\s*(\d+m)</div>',
    re.IGNORECASE,
)
EMBEDDED_DATA_RE = re.compile(
    r"(const embeddedDashboardData = \{[\s\S]*?\};)",
)


def _repair_html(path: Path, timeframe: str) -> tuple[bool, str]:
    raw = path.read_text(encoding="utf-8")
    data_match = EMBEDDED_DATA_RE.search(raw)
    data_blob = data_match.group(1) if data_match else ""
    fixed = normalize_chartjs_dashboard_timeframe_labels(
        raw,
        instrument="MNQ",
        session_type="RTH",
        timeframe=timeframe,
    )
    if data_blob:
        after = EMBEDDED_DATA_RE.search(fixed)
        if not after or after.group(1) != data_blob:
            raise RuntimeError(f"embedded data changed during label repair: {path}")
    if fixed == raw:
        return False, raw
    path.write_text(fixed, encoding="utf-8")
    return True, fixed


def repair_reports(
    *,
    contracts: list[str] | None = None,
    regenerate_png: bool = True,
    dry_run: bool = False,
) -> dict:
    audit_before = run_audit()
    changed: list[str] = []
    pngs: list[str] = []
    for contract, date_range, _s, _e in CERTIFIED_MATRIX:
        if contracts and contract not in contracts:
            continue
        for tf in TIMEFRAMES:
            dash = REPORTS_ROOT / f"{contract}_{date_range}_{tf}" / "dashboards"
            if not dash.is_dir():
                continue
            for stem in PRIMARY_STEMS:
                for html_path in sorted(dash.glob(f"*{stem}.html")):
                    text = html_path.read_text(encoding="utf-8", errors="replace")
                    labels = CHART_SUBTITLE_RE.findall(text)
                    needs = "MNQ | RTH | 5m" in text and tf != "5m"
                    if labels:
                        needs = needs or any(lbl != tf for lbl in labels)
                    if not needs:
                        continue
                    if dry_run:
                        changed.append(str(html_path.relative_to(REPO)))
                        continue
                    did, _ = _repair_html(html_path, tf)
                    if did:
                        rel = str(html_path.relative_to(REPO))
                        changed.append(rel)
                        if regenerate_png:
                            png = generate_screenshot(html_path, html_path.parent)
                            pngs.append(str(png.relative_to(REPO)))

    audit_after = run_audit() if not dry_run else audit_before
    return {
        "dry_run": dry_run,
        "html_changed": changed,
        "png_regenerated": pngs,
        "audit_before_drift": audit_before["drift_count"],
        "audit_after_drift": audit_after["drift_count"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", action="append", help="Limit repair to contract(s), e.g. MNQH26")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-png", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "out" / "audits" / "timeframe_label_repair.json",
    )
    args = parser.parse_args()
    result = repair_reports(
        contracts=args.contract,
        regenerate_png=not args.no_png,
        dry_run=args.dry_run,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["audit_after_drift"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

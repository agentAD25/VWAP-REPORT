#!/usr/bin/env python3
"""Repair individual CORE_PUBLIC dashboard HTML pages (BOM + disclosure CSS in <style>)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUPABASE = REPO.parent / "supabase-opti-database"
DOCS = REPO / "docs"
MANIFEST = DOCS / "manifest.json"

sys.path.insert(0, str(SUPABASE / "scripts"))
sys.path.insert(0, str(SUPABASE / "src"))

from vwap_reports.reporting.dashboards.builder import normalize_dashboard_page_html  # noqa: E402

CORE_PUBLIC_STEMS = (
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


def certified_dashboard_pages(*, include_index: bool = False) -> list[Path]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    paths: list[Path] = []
    for contract in ("MNQZ25", "MNQH25", "MNQM25", "MNQU25"):
        for tf in ("1m", "5m", "15m", "30m"):
            for _dr, entry in manifest.get(contract, {}).get(tf, {}).items():
                if entry.get("status") != "CURRENT_CERTIFIED_PUBLIC":
                    continue
                dash = DOCS / Path(entry["dashboard_index"]).parent
                for stem in CORE_PUBLIC_STEMS:
                    matches = sorted(dash.glob(f"*_{stem}.html"))
                    if len(matches) != 1:
                        raise RuntimeError(f"{dash}: expected one *_{stem}.html, got {len(matches)}")
                    paths.append(matches[0])
                if include_index:
                    idx = dash / "index.html"
                    if idx.is_file():
                        paths.append(idx)
    return paths


def repair_page(path: Path) -> bool:
    before = path.read_text(encoding="utf-8-sig")
    after = normalize_dashboard_page_html(before)
    if after == before:
        return False
    path.write_text(after, encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for html_path in certified_dashboard_pages(include_index=False):
        if repair_page(html_path):
            changed += 1
            print(f"repaired {html_path.relative_to(REPO)}")
    print(f"repair_page_count={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

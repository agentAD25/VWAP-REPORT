#!/usr/bin/env python3
"""Rebuild hold_fail_rates HTML (KPI labels) and refresh hold_fail PNG thumbnails."""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

from html.parser import HTMLParser

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SUPABASE = REPO.parent / "supabase-opti-database"
DOCS = REPO / "docs"
MANIFEST = DOCS / "manifest.json"

sys.path.insert(0, str(SUPABASE / "scripts"))
sys.path.insert(0, str(SUPABASE / "src"))

from package_vwap_public_sample_from_bundle import _inject_disclosure  # noqa: E402
from vwap_reports.reporting.dashboards.builder import (  # noqa: E402
    build_dashboard,
    normalize_dashboard_page_html,
)
from vwap_reports.reporting.dashboards.registry import get_report_spec  # noqa: E402
from vwap_reports.reporting.dashboards.screenshot import generate_screenshot  # noqa: E402
from vwap_reports.reporting.filename_utils import contract_to_instrument  # noqa: E402

CONTRACT_META: dict[str, dict] = {
    "MNQH25": {"iso_start": "2024-12-16", "iso_end": "2025-03-14", "sessions": 59},
    "MNQM25": {"iso_start": "2025-03-17", "iso_end": "2025-06-13", "sessions": 63},
    "MNQU25": {"iso_start": "2025-06-16", "iso_end": "2025-09-12", "sessions": 40},
    "MNQZ25": {"iso_start": "2025-09-14", "iso_end": "2025-12-12", "sessions": 63},
}
LATTICE_BARS: dict[str, int] = {"1m": 390, "5m": 78, "15m": 26, "30m": 13}


class _Cfg:
    def __init__(self, contract: str, timeframe: str, start: str, end: str, sessions: int):
        self.contract = contract
        self.timeframe = timeframe
        self.start = start.replace("-", "")
        self.end = end.replace("-", "")
        self.session_type = "RTH"
        self.complete_sessions = sessions
        self.bars_per_session = LATTICE_BARS[timeframe]
        self.source_bundle = Path(".")


class _DataTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_tbody = False
        self._in_row = False
        self._in_cell = False
        self._cell_buf: list[str] = []
        self._row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tbody":
            self._in_tbody = True
        elif self._in_tbody and tag == "tr":
            self._in_row = True
            self._row = []
        elif self._in_row and tag == "td":
            self._in_cell = True
            self._cell_buf = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self._in_tbody = False
        elif tag == "tr" and self._in_row:
            self._in_row = False
            if self._row:
                self.rows.append(self._row)
        elif tag == "td" and self._in_cell:
            self._in_cell = False
            self._row.append("".join(self._cell_buf).strip())

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_buf.append(data)


def _parse_rate(cell: str) -> float:
    s = str(cell).strip().replace("%", "")
    v = float(s)
    return v / 100.0 if v > 1.0 else v


def _load_table(html_path: Path) -> pd.DataFrame:
    parser = _DataTableParser()
    parser.feed(html_path.read_text(encoding="utf-8-sig"))
    if not parser.rows:
        raise ValueError(f"No data table in {html_path}")
    keys = [
        "event_type",
        "direction",
        "total_events",
        "held_count",
        "failed_count",
        "hold_rate",
        "fail_rate",
    ]
    records = [dict(zip(keys, row)) for row in parser.rows]
    df = pd.DataFrame(records)
    df["held_count"] = df["held_count"].astype(int)
    df["failed_count"] = df["failed_count"].astype(int)
    df["total_events"] = df["total_events"].astype(int)
    df["hold_rate"] = df["hold_rate"].map(_parse_rate)
    df["fail_rate"] = df["fail_rate"].map(_parse_rate)
    return df


def certified_hold_fail_pages() -> list[tuple[str, str, Path]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows: list[tuple[str, str, Path]] = []
    for contract, meta in CONTRACT_META.items():
        for tf in ("1m", "5m", "15m", "30m"):
            for _dr, entry in manifest.get(contract, {}).get(tf, {}).items():
                if entry.get("status") != "CURRENT_CERTIFIED_PUBLIC":
                    continue
                dash = DOCS / Path(entry["dashboard_index"]).parent
                html = next(dash.glob("*_hold_fail_rates.html"))
                rows.append((contract, tf, html))
    return rows


def repair_one(contract: str, timeframe: str, html_path: Path) -> None:
    meta = CONTRACT_META[contract]
    df = _load_table(html_path)
    spec = get_report_spec("hold_fail_rates")
    assert spec is not None

    report_params = {
        "instrument": contract_to_instrument(contract) or "MNQ",
        "session_type": "RTH",
        "timeframe": timeframe,
        "contract_name": contract,
        "date_range": {"start_date": meta["iso_start"], "end_date": meta["iso_end"]},
    }
    cfg = _Cfg(contract, timeframe, meta["iso_start"], meta["iso_end"], meta["sessions"])

    with tempfile.TemporaryDirectory() as tmp:
        built = build_dashboard(
            Path(tmp),
            spec,
            {"hold_fail_rates.csv": df},
            report_params,
        )
        raw = built.read_text(encoding="utf-8-sig")
    cleaned = normalize_dashboard_page_html(raw)
    html_path.write_text(cleaned, encoding="utf-8")
    _inject_disclosure(html_path, policy_on_index=False, cfg=cfg)
    generate_screenshot(html_path, html_path.parent)
    print(f"repaired {html_path.relative_to(REPO)}")


def main() -> int:
    import os

    os.chdir(SUPABASE)
    for contract, tf, path in certified_hold_fail_pages():
        repair_one(contract, tf, path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Rebuild certified public dashboard index.html (+ index.png) for visual parity."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUPABASE = Path(__file__).resolve().parents[2] / "supabase-opti-database"
sys.path.insert(0, str(SUPABASE / "scripts"))
sys.path.insert(0, str(SUPABASE / "src"))
sys.path.insert(0, str(SUPABASE))

from package_vwap_public_sample_from_bundle import (  # noqa: E402
    CORE_PUBLIC_STEMS,
    _inject_disclosure,
    _session_policy_banner_kwargs,
)
from vwap_reports.reporting.dashboards.index_builder import build_index  # noqa: E402
from vwap_reports.reporting.dashboards.screenshot import generate_screenshot  # noqa: E402
from vwap_reports.reporting.filename_utils import contract_to_instrument  # noqa: E402

DOCS = REPO / "docs"
MANIFEST = DOCS / "manifest.json"

CONTRACT_META: dict[str, dict] = {
    "MNQH25": {"start": "20241216", "end": "20250314", "sessions": 59, "iso_start": "2024-12-16", "iso_end": "2025-03-14"},
    "MNQM25": {"start": "20250317", "end": "20250613", "sessions": 63, "iso_start": "2025-03-17", "iso_end": "2025-06-13"},
    "MNQU25": {"start": "20250616", "end": "20250912", "sessions": 40, "iso_start": "2025-06-16", "iso_end": "2025-09-12"},
    "MNQZ25": {"start": "20250914", "end": "20251212", "sessions": 63, "iso_start": "2025-09-14", "iso_end": "2025-12-12"},
}

LATTICE_BARS: dict[str, int] = {"1m": 390, "5m": 78, "15m": 26, "30m": 13}


class _Cfg:
    def __init__(self, contract: str, timeframe: str, start: str, end: str, sessions: int):
        self.contract = contract
        self.timeframe = timeframe
        self.start = start
        self.end = end
        self.session_type = "RTH"
        self.complete_sessions = sessions
        self.bars_per_session = LATTICE_BARS[timeframe]


def certified_dashboard_dirs() -> list[tuple[str, str, Path]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows: list[tuple[str, str, Path]] = []
    for contract, meta in CONTRACT_META.items():
        for tf in ("1m", "5m", "15m", "30m"):
            for _dr, entry in manifest.get(contract, {}).get(tf, {}).items():
                if entry.get("status") != "CURRENT_CERTIFIED_PUBLIC":
                    continue
                dash = DOCS / entry["dashboard_index"]
                rows.append((contract, tf, dash.parent))
    return rows


def repair_one(contract: str, timeframe: str, dash_dir: Path) -> None:
    meta = CONTRACT_META[contract]
    html_files: list[Path] = []
    for stem in CORE_PUBLIC_STEMS:
        matches = sorted(dash_dir.glob(f"*_{stem}.html"))
        if len(matches) != 1:
            raise RuntimeError(f"{dash_dir}: expected one *_{stem}.html, found {len(matches)}")
        html_files.append(matches[0])

    report_params = {
        "instrument": contract_to_instrument(contract) or "MNQ",
        "contract": contract,
        "session_type": "RTH",
        "timeframe": timeframe,
        "date_range": {
            "start_date": meta["iso_start"],
            "end_date": meta["iso_end"],
        },
    }
    cfg = _Cfg(contract, timeframe, meta["iso_start"], meta["iso_end"], meta["sessions"])
    cfg.bars_per_session = LATTICE_BARS[timeframe]

    index_path = build_index(dash_dir, html_files, report_params)
    _inject_disclosure(index_path, policy_on_index=True, cfg=cfg)
    generate_screenshot(index_path, dash_dir)
    print(f"repaired {contract}|{timeframe} -> {index_path.relative_to(REPO)}")


def main() -> int:
    import os

    os.chdir(SUPABASE)
    for contract, tf, dash_dir in certified_dashboard_dirs():
        repair_one(contract, tf, dash_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

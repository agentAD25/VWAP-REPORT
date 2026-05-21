#!/usr/bin/env python3
"""Audit certified MNQ public reports for timeframe semantic parity (labels + filenames)."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
MANIFEST_PATH = DOCS / "manifest.json"
REPORTS_ROOT = DOCS / "reports"

CERTIFIED_MATRIX: list[tuple[str, str, str, str]] = [
    ("MNQZ25", "20250914-20251212", "20250914", "20251212"),
    ("MNQH25", "20241216-20250314", "20241216", "20250314"),
    ("MNQM25", "20250317-20250613", "20250317", "20250613"),
    ("MNQU25", "20250616-20250912", "20250616", "20250912"),
    ("MNQH26", "20251215-20260313", "20251215", "20260313"),
]
TIMEFRAMES = ("1m", "5m", "15m", "30m")
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
CHART_SUBTITLE_RE = re.compile(
    r'<div class="chart-subtitle">MNQ\s*\|\s*RTH\s*\|\s*(\d+m)</div>',
    re.IGNORECASE,
)
EMBEDDED_DATA_RE = re.compile(
    r"const embeddedDashboardData = (\{[\s\S]*?\});",
)


@dataclass
class PageAudit:
    contract: str
    timeframe: str
    page: str
    expected_tf: str
    visible_tf_values: list[str]
    filename_tf: str
    manifest_tf: str
    verdict: str
    notes: str


def _manifest_entry(manifest: dict, contract: str, tf: str, date_range: str) -> dict | None:
    return manifest.get(contract, {}).get(tf, {}).get(date_range)


def _filename_tf(path: Path, expected_tf: str) -> str:
    name = path.name
    for tf in TIMEFRAMES:
        if f"_{tf}_" in name or name.endswith(f"_{tf}.html"):
            return tf
    return expected_tf if expected_tf in name else "unknown"


def audit_page(
    *,
    contract: str,
    timeframe: str,
    date_range: str,
    stem: str,
    html_path: Path,
    manifest_tf: str,
) -> PageAudit:
    text = html_path.read_text(encoding="utf-8", errors="replace")
    visible = CHART_SUBTITLE_RE.findall(text)
    fname_tf = _filename_tf(html_path, timeframe)
    notes: list[str] = []
    verdict = "TIMEFRAME_SEMANTIC_PASS"

    if fname_tf != timeframe:
        verdict = "TIMEFRAME_FILENAME_DRIFT"
        notes.append(f"filename_tf={fname_tf}")
    if manifest_tf != timeframe:
        verdict = "TIMEFRAME_MANIFEST_DRIFT"
        notes.append(f"manifest_tf={manifest_tf}")

    if stem in ("dashboard_all_events", "dashboard_crosses"):
        if not visible:
            notes.append("no_chart_subtitle_tf_label")
        wrong = sorted({v for v in visible if v != timeframe})
        if wrong:
            verdict = "TIMEFRAME_LABEL_DRIFT"
            notes.append(f"chart_subtitle_wrong={wrong}")
        elif visible and all(v == timeframe for v in visible):
            pass
        elif not visible:
            verdict = "TIMEFRAME_UNKNOWN_DRIFT"

    if "| 5m" in text and timeframe != "5m" and stem in ("dashboard_all_events", "dashboard_crosses"):
        if "MNQ | RTH | 5m" in text:
            verdict = "TIMEFRAME_LABEL_DRIFT"
            notes.append("hardcoded_MNQ_RTH_5m")

    return PageAudit(
        contract=contract,
        timeframe=timeframe,
        page=html_path.name,
        expected_tf=timeframe,
        visible_tf_values=visible,
        filename_tf=fname_tf,
        manifest_tf=manifest_tf,
        verdict=verdict,
        notes="; ".join(notes),
    )


def run_audit(docs_root: Path = DOCS) -> dict:
    manifest = json.loads((docs_root / "manifest.json").read_text(encoding="utf-8"))
    rows: list[PageAudit] = []
    for contract, date_range, _start, _end in CERTIFIED_MATRIX:
        for tf in TIMEFRAMES:
            folder = REPORTS_ROOT / f"{contract}_{date_range}_{tf}"
            dash = folder / "dashboards"
            entry = _manifest_entry(manifest, contract, tf, date_range) or {}
            manifest_tf = tf
            if entry.get("dashboard_index") and tf not in entry["dashboard_index"]:
                manifest_tf = "drift"
            for stem in CORE_PUBLIC_STEMS:
                matches = sorted(dash.glob(f"*{stem}.html"))
                if not matches:
                    rows.append(
                        PageAudit(
                            contract,
                            tf,
                            stem,
                            tf,
                            [],
                            "missing",
                            manifest_tf,
                            "TIMEFRAME_UNKNOWN_DRIFT",
                            "html_missing",
                        )
                    )
                    continue
                for html_path in matches:
                    rows.append(
                        audit_page(
                            contract=contract,
                            timeframe=tf,
                            date_range=date_range,
                            stem=stem,
                            html_path=html_path,
                            manifest_tf=manifest_tf,
                        )
                    )
    drift = [r for r in rows if r.verdict != "TIMEFRAME_SEMANTIC_PASS"]
    return {
        "pages_audited": len(rows),
        "drift_count": len(drift),
        "drift": [asdict(r) for r in drift],
        "rows": [asdict(r) for r in rows],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "out" / "audits" / "timeframe_semantics_audit.json",
    )
    args = parser.parse_args()
    result = run_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"pages_audited": result["pages_audited"], "drift_count": result["drift_count"]}, indent=2))
    return 1 if result["drift_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Audit hold_fail_rates table rows across certified MNQ 2025 public reports."""

from __future__ import annotations

import json
import re
from pathlib import Path

from html.parser import HTMLParser

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
MANIFEST = DOCS / "manifest.json"

CERTIFIED = [
    ("MNQZ25", "1m", "20250914", "20251212"),
    ("MNQZ25", "5m", "20250914", "20251212"),
    ("MNQZ25", "15m", "20250914", "20251212"),
    ("MNQZ25", "30m", "20250914", "20251212"),
    ("MNQH25", "1m", "20241216", "20250314"),
    ("MNQH25", "5m", "20241216", "20250314"),
    ("MNQH25", "15m", "20241216", "20250314"),
    ("MNQH25", "30m", "20241216", "20250314"),
    ("MNQM25", "1m", "20250317", "20250613"),
    ("MNQM25", "5m", "20250317", "20250613"),
    ("MNQM25", "15m", "20250317", "20250613"),
    ("MNQM25", "30m", "20250317", "20250613"),
    ("MNQU25", "1m", "20250616", "20250912"),
    ("MNQU25", "5m", "20250616", "20250912"),
    ("MNQU25", "15m", "20250616", "20250912"),
    ("MNQU25", "30m", "20250616", "20250912"),
]


def _n_flag(n: int) -> str:
    if n < 5:
        return "VERY_LOW_N"
    if n < 10:
        return "LOW_N"
    return "OK_N"


def _parse_rate(cell: str) -> float:
    s = str(cell).strip().replace("%", "")
    v = float(s)
    return v / 100.0 if v > 1.0 else v


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


def load_hold_fail_table(html_path: Path) -> list[dict]:
    text = html_path.read_text(encoding="utf-8-sig")
    parser = _DataTableParser()
    parser.feed(text)
    if not parser.rows:
        raise ValueError(f"No hold_fail table in {html_path}")
    keys = [
        "event_type",
        "direction",
        "total_events",
        "held_count",
        "failed_count",
        "hold_rate",
        "fail_rate",
    ]
    return [dict(zip(keys, row)) for row in parser.rows]


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows: list[dict] = []

    for contract, tf, start, end in CERTIFIED:
        dr = f"{start}-{end}"
        entry = manifest[contract][tf][dr]
        dash = DOCS / Path(entry["dashboard_index"]).parent
        html = next(dash.glob("*_hold_fail_rates.html"))
        for r in load_hold_fail_table(html):
            n = int(r["total_events"])
            hold = _parse_rate(r["hold_rate"])
            fail = _parse_rate(r["fail_rate"])
            rows.append(
                {
                    "contract": contract,
                    "timeframe": tf,
                    "event_type": r["event_type"],
                    "direction": r["direction"],
                    "total_events": n,
                    "held_count": int(r["held_count"]),
                    "failed_count": int(r["failed_count"]),
                    "hold_rate": hold,
                    "fail_rate": fail,
                    "small_n_flag": _n_flag(n),
                }
            )

    out_dir = REPO / "out" / "audits" / "hold_fail_small_n_20260521"
    out_dir.mkdir(parents=True, exist_ok=True)
    import csv

    audit_path = out_dir / "hold_fail_small_n_audit.csv"
    fields = list(rows[0].keys()) if rows else []
    with audit_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    extremes = [
        r
        for r in rows
        if r["hold_rate"] in (0.0, 1.0) or r["fail_rate"] in (0.0, 1.0)
    ]
    low_only = [r for r in extremes if r["small_n_flag"] != "OK_N"]
    print(f"rows={len(rows)} extreme_rate_rows={len(extremes)} extreme_in_low_n={len(low_only)}")
    print(f"extreme_not_low_n={len(extremes) - len(low_only)}")
    print(f"audit_csv={audit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

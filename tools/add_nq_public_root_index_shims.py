#!/usr/bin/env python3
"""Add root index.html redirect shims for NQ public sample slug folders."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / "docs" / "reports"
MANIFEST_SRC = (
    REPO.parent
    / "supabase-opti-database"
    / "configs/vwap_report/instruments/nq_all20_public_manifest_20260525.json"
)


def shim_html(*, instrument: str, contract: str, timeframe: str, partial: bool) -> str:
    tag = " (partial)" if partial else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=dashboards/index.html">
  <title>{instrument} VWAP Historical Sample — {contract} {timeframe}{tag}</title>
</head>
<body>
<div class="vwap-public-disclosure-banner" role="note" aria-label="Research disclosure">
  <p><strong>Historical RTH VWAP research report.</strong> This content is <strong>not</strong> real-time market data
  and must not be used as a live quote or execution feed. Session calculations use
  <strong>America/New_York</strong> <strong>regular trading hours (RTH)</strong>. VWAP is
  <strong>cumulative HLC3 (typical-price) VWAP</strong> on the report bar lattice.</p>
  <p class="vwap-public-disclosure-oneline">Not real-time • Historical research output • RTH • America/New_York • HLC3 VWAP</p>
</div>
<div class="vwap-no-export" role="note" style="margin:12px 16px;padding:12px 16px;border:1px solid rgba(0,180,216,0.35);border-radius:8px;">
  <p><strong>No public machine-readable exports.</strong> This page does not publish CSV, JSON, Parquet, or raw bar/event downloads.</p>
</div>
<p style="margin:12px 16px;color:#b8d4e8;font-size:0.9em;"><strong>Disclaimer:</strong> For research and educational use only. Not investment, tax, or trading advice.</p>
  <p style="margin:16px;"><a href="dashboards/index.html"><strong>Open dashboards</strong></a></p>
  <p style="margin:16px;color:#94a3b8;font-size:0.85em;">If you are not redirected automatically, use the link above.</p>
</body>
</html>
"""


def main() -> int:
    bundles = json.loads(MANIFEST_SRC.read_text(encoding="utf-8"))["bundles"]
    created = reused = 0
    for item in bundles:
        slug = item["slug"]
        folder = REPORTS / slug
        if not folder.is_dir():
            raise FileNotFoundError(f"Missing report folder: {folder}")
        path = folder / "index.html"
        html = shim_html(
            instrument="NQ",
            contract=item["contract"],
            timeframe=item["timeframe"],
            partial=bool(item.get("partial")),
        )
        if path.is_file() and path.read_text(encoding="utf-8") == html:
            reused += 1
            continue
        if path.is_file():
            raise RuntimeError(f"Root index exists and differs: {path}")
        path.write_text(html, encoding="utf-8")
        created += 1
    print(json.dumps({"created": created, "reused": reused, "total": len(bundles)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

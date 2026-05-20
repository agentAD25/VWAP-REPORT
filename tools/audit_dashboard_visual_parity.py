#!/usr/bin/env python3
"""Audit certified MNQ 2025 dashboard index.html visual/style parity vs MNQH25 5m canonical."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
MANIFEST = DOCS / "manifest.json"
CANONICAL = DOCS / "reports/MNQH25_20241216-20250314_5m/dashboards/index.html"
CONTRACTS = ("MNQZ25", "MNQH25", "MNQM25", "MNQU25")
TIMEFRAMES = ("1m", "5m", "15m", "30m")


def _style_block(html: str) -> str:
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL | re.IGNORECASE)
    return m.group(1) if m else ""


def _markers(html: str) -> dict:
    css = _style_block(html)
    return {
        "has_bom_in_style": "\ufeff" in css,
        "has_bg_primary": "--bg-primary" in css,
        "has_extended_gallery": "margin-top: var(--spacing-lg)" in css,
        "has_disclosure_css": ".vwap-public-disclosure-banner" in css,
        "has_gallery_class": bool(re.search(r'class="gallery"', html)),
        "card_links": len(re.findall(r'class="dashboard-card"', html)),
        "img_tags": len(re.findall(r"<img\s", html)),
        "style_len": len(css),
    }


def certified_entries() -> list[dict]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for contract in CONTRACTS:
        for tf in TIMEFRAMES:
            for date_range, entry in manifest.get(contract, {}).get(tf, {}).items():
                if entry.get("status") != "CURRENT_CERTIFIED_PUBLIC":
                    continue
                di = entry["dashboard_index"]
                rows.append(
                    {
                        "contract": contract,
                        "timeframe": tf,
                        "date_range": date_range,
                        "dashboard_index": di,
                        "local_path": str(DOCS / di),
                        "live_url": f"https://agentad25.github.io/VWAP-REPORT/{di}",
                        "active": entry.get("active"),
                        "canonical": entry.get("canonical"),
                        "public_safe": entry.get("public_safe"),
                        "status": entry.get("status"),
                        "csv": entry.get("csv"),
                    }
                )
    return rows


def classify(markers: dict, canon: dict) -> str:
    if markers["has_bom_in_style"]:
        return "VISUAL_PARITY_FAIL_MISSING_THEME_CSS"
    if not markers["has_bg_primary"]:
        return "VISUAL_PARITY_FAIL_MISSING_THEME_CSS"
    if markers["card_links"] < 9:
        return "VISUAL_PARITY_FAIL_CARD_GRID"
    if not markers["has_extended_gallery"] and canon["has_extended_gallery"]:
        return "VISUAL_PARITY_FAIL_CARD_GRID"
    if not markers["has_disclosure_css"] and canon["has_disclosure_css"]:
        return "VISUAL_PARITY_FAIL_DISCLOSURE_LAYOUT"
    if markers["style_len"] < canon["style_len"] * 0.85:
        return "VISUAL_PARITY_FAIL_UNKNOWN"
    return "VISUAL_PARITY_PASS"


def main() -> int:
    canon_html = CANONICAL.read_text(encoding="utf-8")
    canon_m = _markers(canon_html)
    print("CANONICAL MNQH25 5m markers:", canon_m)

    rows = certified_entries()
    print(f"certified_count={len(rows)}")
    fails: list[dict] = []
    for row in rows:
        path = Path(row["local_path"])
        html = path.read_text(encoding="utf-8")
        m = _markers(html)
        verdict = classify(m, canon_m)
        row.update(m)
        row["verdict"] = verdict
        print(
            f"{row['contract']}|{row['timeframe']}|{verdict}|bom={m['has_bom_in_style']}|"
            f"ext_gallery={m['has_extended_gallery']}|disc_css={m['has_disclosure_css']}|"
            f"cards={m['card_links']}|style_len={m['style_len']}"
        )
        if verdict != "VISUAL_PARITY_PASS":
            fails.append(row)

    out = REPO / "out/audits/dashboard_visual_parity_20260520.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"canonical": canon_m, "reports": rows, "fail_count": len(fails)}, indent=2),
        encoding="utf-8",
    )
    print(f"audit: {out}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

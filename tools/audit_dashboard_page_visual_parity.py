#!/usr/bin/env python3
"""Playwright + HTML marker audit for certified dashboard index and CORE_PUBLIC pages."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
MANIFEST = DOCS / "manifest.json"
OUT = REPO / "out" / "audits" / "dashboard_page_visual_parity_20260521"

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


def html_markers(html: str) -> dict:
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL | re.I)
    css = m.group(1) if m else ""
    legacy_dark = "#0a0e27" in html and "Segoe UI" in html
    return {
        "bom": "\ufeff" in css,
        "bg_primary": "--bg-primary" in html,
        "legacy_dark": legacy_dark,
        "disclosure_css": ".vwap-public-disclosure-banner" in html,
        "font_var": "font-family: var(--font-family)" in html or "Segoe UI" in html,
    }


def classify(markers: dict, computed: dict) -> str:
    if markers["bom"]:
        return "DASHBOARD_PAGE_FAIL_BOM"
    if not markers["bg_primary"] and not markers["legacy_dark"]:
        return "DASHBOARD_PAGE_FAIL_MISSING_THEME_CSS"
    if not markers["disclosure_css"]:
        return "DASHBOARD_PAGE_FAIL_DISCLOSURE_LAYOUT"
    if computed.get("white_body"):
        return "DASHBOARD_PAGE_FAIL_DEFAULT_WHITE_BODY"
    if computed.get("serif_font"):
        return "DASHBOARD_PAGE_FAIL_DEFAULT_SERIF_FONT"
    return "DASHBOARD_PAGE_VISUAL_PARITY_PASS"


def page_paths() -> list[tuple[str, Path, str]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows: list[tuple[str, Path, str]] = []
    for contract, tf, start, end in CERTIFIED:
        dr = f"{start}-{end}"
        entry = manifest[contract][tf][dr]
        dash = DOCS / Path(entry["dashboard_index"]).parent
        rel_base = f"reports/{contract}_{dr}_{tf}/dashboards"
        rows.append((f"{contract}|{tf}|index", dash / "index.html", f"{rel_base}/index.html"))
        for stem in CORE_PUBLIC_STEMS:
            html = next(dash.glob(f"*_{stem}.html"))
            rows.append((f"{contract}|{tf}|{stem}", html, f"{rel_base}/{html.name}"))
    return rows


def run_playwright(rows: list[tuple[str, Path, str]], port: int) -> dict[str, dict]:
    from playwright.sync_api import sync_playwright

    out: dict[str, dict] = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        for key, local_path, rel in rows:
            url = f"http://127.0.0.1:{port}/{rel}"
            try:
                page.goto(url, wait_until="networkidle", timeout=60000)
                data = page.evaluate(
                    """() => ({
                      bodyBg: getComputedStyle(document.body).backgroundColor,
                      font: getComputedStyle(document.body).fontFamily,
                    })"""
                )
                white = data["bodyBg"] in ("rgb(255, 255, 255)", "white")
                font = data.get("font") or ""
                serif = "times new roman" in font.lower() and "segoe" not in font.lower()
                out[key] = {
                    "url": url,
                    "body_bg": data["bodyBg"],
                    "font": font,
                    "white_body": white,
                    "serif_font": serif,
                }
            except Exception as ex:
                out[key] = {"error": str(ex)}
        browser.close()
    return out


def main() -> int:
    rows = page_paths()
    OUT.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for key, path, rel in rows:
        html = path.read_text(encoding="utf-8-sig")
        markers = html_markers(html)
        results.append(
            {
                "key": key,
                "path": str(path.relative_to(REPO)),
                "markers": markers,
                "verdict_html": classify(markers, {}),
            }
        )

    port = 8770
    pw = run_playwright(rows, port)
    fails = 0
    for row in results:
        key = row["key"]
        comp = pw.get(key, {})
        row["computed"] = comp
        if "error" in comp:
            row["verdict"] = "DASHBOARD_PAGE_FAIL_UNKNOWN"
        else:
            row["verdict"] = classify(row["markers"], comp)
        if row["verdict"] != "DASHBOARD_PAGE_VISUAL_PARITY_PASS":
            fails += 1
        print(f"{key}|{row['verdict']}|bom={row['markers']['bom']}|disc={row['markers']['disclosure_css']}")

    summary = {
        "page_count": len(results),
        "fail_count": fails,
        "results": results,
    }
    out_json = OUT / "audit_summary.json"
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"audit: {out_json}")
    print(f"fail_count={fails}/{len(results)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())

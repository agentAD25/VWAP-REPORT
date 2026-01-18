#!/usr/bin/env python3
"""
Shared helpers for NQ-format hold_fail_rates: single place for CSS replace logic
and NQ dark-theme. Used by apply_hold_fail_nq_format_all.py (and can be used by
update_hold_fail_rates_visual.py or other scripts to avoid duplicated regexes).
"""

import re

# Inner CSS only (no <style> wrapper). Full replacement block is built in
# replace_placeholder_css_with_nq_theme.
NQ_THEME_CSS_INNER = """        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%);
            color: #ffffff;
            padding: 20px;
            min-height: 100vh;
        }

        .header {
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(0, 100, 200, 0.1);
            border-radius: 10px;
            border: 1px solid rgba(0, 150, 255, 0.3);
        }

        .header h1 {
            font-size: 2.5em;
            background: linear-gradient(135deg, #00b4d8 0%, #0077b6 50%, #90e0ef 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
            text-shadow: 0 0 20px rgba(0, 180, 216, 0.5);
        }

        .header .subtitle {
            color: #90e0ef;
            font-size: 1.1em;
        }

        .takeaways {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .takeaway-card {
            background: rgba(15, 20, 35, 0.8);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(0, 150, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            text-align: center;
        }

        .takeaway-card .label {
            color: #7dd3fc;
            font-size: 0.9em;
            margin-bottom: 10px;
        }

        .takeaway-card .value {
            color: #90e0ef;
            font-size: 2em;
            font-weight: 600;
            margin-bottom: 5px;
        }

        .takeaway-card .description {
            color: rgba(255, 255, 255, 0.6);
            font-size: 0.85em;
        }

        .dashboard-container {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }

        .chart-container {
            background: rgba(15, 20, 35, 0.8);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(0, 150, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            max-width: 800px;
            width: 100%;
            margin: 0 auto;
        }

        #chart-1 {
            margin: 0 auto;
            display: block;
            width: 100%;
        }

        .chart-title {
            font-size: 1.3em;
            margin-bottom: 20px;
            color: #90e0ef;
            text-align: center;
            font-weight: 600;
        }

        .chart-subtitle {
            font-size: 0.9em;
            color: #7dd3fc;
            text-align: center;
            margin-bottom: 15px;
        }

        .insights-table {
            background: rgba(15, 20, 35, 0.8);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(0, 150, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
        }

        .insights-title {
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #90e0ef;
            text-align: center;
            font-weight: 600;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }

        th {
            background: linear-gradient(135deg, #0077b6 0%, #00b4d8 100%);
            color: #ffffff;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            border: 1px solid rgba(0, 180, 216, 0.3);
        }

        td {
            padding: 12px 15px;
            border: 1px solid rgba(0, 150, 255, 0.2);
            color: #e0f7fa;
        }

        tr:nth-child(even) {
            background: rgba(0, 100, 200, 0.1);
        }

        tr:hover {
            background: rgba(0, 150, 255, 0.2);
            transition: background 0.3s;
        }

        .panel {
            background: rgba(15, 20, 35, 0.8);
            border-radius: 15px;
            padding: 25px;
            border: 1px solid rgba(0, 150, 255, 0.2);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            margin-bottom: 30px;
        }

        .panel h3 {
            color: #90e0ef;
            margin-bottom: 15px;
            font-size: 1.2em;
        }

        .panel .text-muted {
            color: rgba(255, 255, 255, 0.6);
        }
"""

# Full block to replace: <style>...placeholder...</style></head>
NQ_THEME_CSS_BLOCK = "    <style>\n" + NQ_THEME_CSS_INNER + "    </style>\n</head>"

# Robust patterns: allow newline/whitespace after */ and before </style>
_CSS_PATTERN_PRIMARY = re.compile(
    r"    <style>\s*/\* Theme CSS will be inlined here \*/\s*</style>\s*</head>"
)
_CSS_PATTERN_FALLBACK = re.compile(
    r"<style>\s*/\* Theme CSS will be inlined here \*/\s*</style>\s*</head>"
)

# Sentinels: already has NQ theme inlined
_CSS_ALREADY_1 = "#0a0e27"
_CSS_ALREADY_2 = "linear-gradient(135deg, #0a0e27"
_PLACEHOLDER = "/* Theme CSS will be inlined here */"


def replace_placeholder_css_with_nq_theme(html: str) -> tuple[str, str]:
    """
    Replace the placeholder style block with the full NQ dark-theme CSS.

    Returns:
        (new_html, status) where status is:
        - "replaced": placeholder was found and replaced
        - "already": placeholder not present but NQ theme is (no-op, no warn)
        - "not_found": placeholder not found and no NQ theme -> caller should warn

    Uses 1–2 robust regexes; idempotent when already replaced.
    """
    # Try primary (4-space indent) then fallback (any <style>)
    if _CSS_PATTERN_PRIMARY.search(html):
        out = _CSS_PATTERN_PRIMARY.sub(NQ_THEME_CSS_BLOCK, html, count=1)
        return (out, "replaced")
    if _CSS_PATTERN_FALLBACK.search(html):
        out = _CSS_PATTERN_FALLBACK.sub(NQ_THEME_CSS_BLOCK, html, count=1)
        return (out, "replaced")

    # Placeholder absent: treat as "already" if NQ theme is present
    if _PLACEHOLDER not in html:
        if _CSS_ALREADY_1 in html or _CSS_ALREADY_2 in html:
            return (html, "already")
    return (html, "not_found")


def contract_to_instrument(contract: str) -> str:
    """Map contract symbol (e.g. NQU25, MGCZ24) to subtitle instrument (NQ, MGC, …)."""
    u = (contract or "").upper()
    if u.startswith("NQ"):
        return "NQ"
    if u.startswith("MGC"):
        return "MGC"
    if u.startswith("ES"):
        return "ES"
    if u.startswith("MES"):
        return "MES"
    if u.startswith("RTY"):
        return "RTY"
    if u.startswith("YM"):
        return "YM"
    if u.startswith("6E"):
        return "6E"
    if u.startswith("CL"):
        return "CL"
    return contract[:3] if len(contract) >= 3 else (contract or "?")

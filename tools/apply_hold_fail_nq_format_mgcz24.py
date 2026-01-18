#!/usr/bin/env python3
"""Apply NQ-format (full CSS, MGC|tf subtitle, insights-table, chart 400px, remove Downloads) to MGCZ24 hold_fail_rates. Fix title/h1: Mgcz24->MGCZ24, 1M->1m."""
import re
from pathlib import Path

BASE = Path(__file__).parent.parent
REPORTS_DIRS = [BASE / "docs" / "reports", BASE / "site" / "docs" / "reports"]
FOLDERS = ["MGCZ24_20240725-20241122_1m", "MGCZ24_20240725-20241122_5m", "MGCZ24_20240725-20241122_15m", "MGCZ24_20240725-20241122_30m"]

CSS = r'''    <style>
        * {
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
    </style>
</head>'''

SUB_INSTR = "            MGC | \n            RTH | \n            {tf} | \n            Built by TonySnow | ALPHA DRIP"

def main():
    for REPORTS in REPORTS_DIRS:
        if not REPORTS.exists():
            continue
        for folder in FOLDERS:
            m = re.search(r'_(\d+m)$', folder)
            tf = m.group(1) if m else "1m"
            base = f"MGCZ24_20240725-20241122_{tf}_hold_fail_rates"
            for sub in ["", "dashboards"]:
                p = (REPORTS / folder / "dashboards" / f"{base}.html") if sub else (REPORTS / folder / f"{base}.html")
                if not p.exists():
                    continue
                s = p.read_text(encoding="utf-8")
                # 1) CSS
                s = re.sub(r'    <style>\s*/\* Theme CSS will be inlined here \*/ \s*</style>\s*</head>', CSS, s, count=1)
                # 2) subtitle NQ -> MGC, 1m -> tf
                s = re.sub(r'<div class="subtitle">\s*NQ \| \s*RTH \| \s*\d+m \| \s*Built by TonySnow \| ALPHA DRIP\s*</div>',
                           f'<div class="subtitle">\n            MGC | \n            RTH | \n            {tf} | \n            Built by TonySnow | ALPHA DRIP\n        </div>', s, count=1)
                # 3) chart
                s = s.replace('style="height: 450px; width: 100%; margin: 0 auto;"', 'style="height: 400px;"')
                # 4) panel -> insights-table, table
                s = s.replace('<div class="panel">\n        <div class="insights-title">Data Preview</div>\n        <table class="data-table" id="dataTable">',
                              '<div class="insights-table">\n        <div class="insights-title">Data Preview</div>\n        <table id="dataTable">')
                # 5) remove Downloads block (match the CSV filename for this tf)
                s = re.sub(r'\s*</div>\s*\n\s*\n\s*\n\s*<div class="download-section">\s*<h3[^>]*>Downloads</h3>.*?<a href="[^"]*hold_fail_rates\.csv"[^>]*>.*?</a>\s*</div>\s*\n\s*\n\s*\n\s*<div class="panel">\s*<h3[^>]*>Notes</h3>',
                           '\n    </div>\n\n    <div class="panel">\n        <h3 style="color: var(--text-accent); margin-bottom: var(--spacing-sm);">Notes</h3>', s, flags=re.DOTALL)
                # 6) title/h1: Mgcz24 -> MGCZ24, 1M/5M/15M/30M -> 1m/5m/15m/30m (from .title() on stem)
                s = s.replace("Mgcz24", "MGCZ24")
                s = re.sub(r"\b(\d+)M\b", r"\1m", s)
                p.write_text(s, encoding="utf-8")
                print("Updated:", p.relative_to(BASE))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
update_hold_fail_rates_visual.py

Copies all hold_fail_rates.html files and updates them to match
the dashboard_all_events.html visual style.
Creates new files in a 'visual update' folder structure.
"""

import re
from pathlib import Path
import shutil

# Reports directory (where HTML files are hosted)
REPORTS_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports"
VISUAL_UPDATE_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports_visual_update"


def get_dashboard_css():
    """Return the CSS from dashboard_all_events.html"""
    return """        * {
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
        }"""


def update_hold_fail_rates_html(html_content, filename):
    """
    Update hold_fail_rates.html to match dashboard_all_events.html styling.
    """
    # Replace the style section with the dashboard CSS
    css = get_dashboard_css()
    
    # Replace the empty style tag with full CSS (for files that haven't been updated yet)
    html_content = re.sub(
        r'<style>\s*/\* Theme CSS will be inlined here \*/\s*</style>',
        f'<style>\n{css}\n    </style>',
        html_content,
        flags=re.DOTALL
    )
    
    # Also replace existing style sections (for files that have already been updated)
    # Match any style tag and replace with our CSS
    html_content = re.sub(
        r'<style>.*?</style>',
        f'<style>\n{css}\n    </style>',
        html_content,
        flags=re.DOTALL
    )
    
    # Update the table container from .panel to .insights-table for the data preview
    # Find the panel containing "Data Preview" and change it to insights-table
    html_content = re.sub(
        r'<div class="panel">\s*<div class="insights-title">Data Preview</div>',
        r'<div class="insights-table">\n        <div class="insights-title">Data Preview</div>',
        html_content,
        flags=re.DOTALL
    )
    
    # Ensure the table has proper styling (it should already have data-table class)
    # Update table class to ensure it matches dashboard style
    html_content = re.sub(
        r'<table class="data-table"',
        r'<table',
        html_content
    )
    
    return html_content


def process_hold_fail_rates_files():
    """
    Process all hold_fail_rates.html files and create updated versions.
    """
    if not REPORTS_DIR.exists():
        print(f"ERROR: Reports directory does not exist: {REPORTS_DIR}")
        return
    
    # Create visual update directory
    VISUAL_UPDATE_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Scanning for hold_fail_rates.html files in: {REPORTS_DIR}")
    print(f"Output directory: {VISUAL_UPDATE_DIR}")
    print()
    
    processed_count = 0
    copied_count = 0
    error_count = 0
    
    # Find all hold_fail_rates.html files recursively
    for html_file in REPORTS_DIR.rglob("*hold_fail_rates.html"):
        try:
            processed_count += 1
            relative_path = html_file.relative_to(REPORTS_DIR)
            print(f"Processing: {relative_path}")
            
            # Read the file
            with open(html_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Update the HTML content
            updated_content = update_hold_fail_rates_html(original_content, html_file.name)
            
            # Create the output path maintaining the same directory structure
            output_path = VISUAL_UPDATE_DIR / relative_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the updated content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            copied_count += 1
            print(f"  [OK] Created updated version at: {output_path.relative_to(VISUAL_UPDATE_DIR)}")
            
        except Exception as e:
            error_count += 1
            print(f"  [ERROR] {e}")
    
    print()
    print("=" * 60)
    print(f"Processing complete!")
    print(f"  Processed: {processed_count} files")
    print(f"  Created: {copied_count} files")
    print(f"  Errors: {error_count} files")
    print(f"  Output directory: {VISUAL_UPDATE_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    process_hold_fail_rates_files()

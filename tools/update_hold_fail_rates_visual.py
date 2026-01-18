#!/usr/bin/env python3
"""
update_hold_fail_rates_visual.py

Copies all hold_fail_rates.html files and updates them to match
the dashboard_all_events.html visual style.
Creates new files in a 'visual update' folder structure.

Uses nq_format_helpers.replace_placeholder_css_with_nq_theme
for CSS replacement (single shared implementation).
"""

import re
import sys
from pathlib import Path
import shutil

_tools = Path(__file__).resolve().parent
if str(_tools) not in sys.path:
    sys.path.insert(0, str(_tools))

from nq_format_helpers import NQ_THEME_CSS_INNER, replace_placeholder_css_with_nq_theme

# Reports directory (where HTML files are hosted)
REPORTS_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports"
VISUAL_UPDATE_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports_visual_update"


def update_hold_fail_rates_html(html_content, filename):
    """
    Update hold_fail_rates.html to match dashboard_all_events.html styling.
    CSS replace uses shared nq_format_helpers.replace_placeholder_css_with_nq_theme.
    """
    # 1) CSS: shared helper (placeholder or already-themed); fallback: any <style> block
    html_content, status = replace_placeholder_css_with_nq_theme(html_content)
    if status == "not_found":
        html_content = re.sub(
            r"<style>.*?</style>",
            f"<style>\n{NQ_THEME_CSS_INNER}\n    </style>",
            html_content,
            flags=re.DOTALL,
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

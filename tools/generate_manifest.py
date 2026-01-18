#!/usr/bin/env python3
"""
generate_manifest.py

Scans the reports directory and generates a manifest.json file that
organizes all reports by contract, timeframe, and date range.
"""

import json
import re
from pathlib import Path
from collections import defaultdict

# Reports directory (relative to this script)
# Check both docs/ and site/docs/ (for compatibility)
if (Path(__file__).parent.parent / "docs" / "reports").exists():
    REPORTS_DIR = Path(__file__).parent.parent / "docs" / "reports"
    MANIFEST_FILE = Path(__file__).parent.parent / "docs" / "manifest.json"
else:
    REPORTS_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports"
    MANIFEST_FILE = Path(__file__).parent.parent / "site" / "docs" / "manifest.json"

# Pattern to extract metadata from folder names
# Format: CONTRACT_YYYYMMDD-YYYYMMDD_TIMEFRAME
FOLDER_PATTERN = re.compile(r'^(?P<contract>[A-Z0-9]+)_(?P<start>\d{8})-(?P<end>\d{8})_(?P<tf>\d+m)$')

# Pattern to detect another contract's prefix in a filename (CONTRACT_YYYYMMDD-YYYYMMDD_1m_)
# Used to exclude wrongly-placed files from other contracts.
CONTRACT_PREFIX_IN_FILENAME = re.compile(r'^([A-Z0-9]+)_\d{8}-\d{8}_\d+m(?:_|\.)')


def file_belongs_to_folder(filename: str, folder_contract: str) -> bool:
    """
    Return True if this file belongs to the folder's contract.
    - If the filename has no contract prefix (e.g. daily_max_extensions.html), it belongs.
    - If the filename has a contract prefix (X_YYYYMMDD-YYYYMMDD_1m_... or .csv/.html),
      X must equal folder_contract; otherwise it was wrongly copied from another contract.
    """
    m = CONTRACT_PREFIX_IN_FILENAME.match(filename)
    if not m:
        return True  # short name or no prefix, belongs to this folder
    return m.group(1) == folder_contract


def parse_folder_name(folder_name):
    """
    Parse a folder name to extract contract, start date, end date, and timeframe.
    Returns a dict with keys: contract, start, end, tf, date_range
    Returns None if the folder doesn't match the pattern.
    """
    match = FOLDER_PATTERN.match(folder_name)
    if not match:
        return None
    
    data = match.groupdict()
    data['date_range'] = f"{data['start']}-{data['end']}"
    return data


def extract_timeframe_minutes(tf_str):
    """
    Extract numeric minutes from timeframe string (e.g., "15m" -> 15).
    Used for sorting timeframes.
    """
    match = re.match(r'(\d+)m', tf_str)
    return int(match.group(1)) if match else 0


def generate_manifest():
    """
    Scan reports directory and generate manifest.json.
    """
    if not REPORTS_DIR.exists():
        print(f"ERROR: Reports directory does not exist: {REPORTS_DIR}")
        print("Please run sync_reports.py first to copy reports.")
        return
    
    print(f"Scanning reports directory: {REPORTS_DIR}")
    
    # Structure: contract -> timeframe -> date_range -> {png, html, csv}
    manifest = defaultdict(lambda: defaultdict(lambda: {}))
    
    # Scan all folders in reports directory
    for folder_path in REPORTS_DIR.iterdir():
        if not folder_path.is_dir():
            continue
        
        folder_name = folder_path.name
        metadata = parse_folder_name(folder_name)
        
        if not metadata:
            print(f"Skipping folder (doesn't match pattern): {folder_name}")
            continue
        
        contract = metadata['contract']
        timeframe = metadata['tf']
        date_range = metadata['date_range']
        
        # Collect files in this folder and subfolders (especially dashboards/)
        png_files = []
        html_files = []
        csv_files = []
        
        # Scan root folder files (only include files that belong to this contract)
        for file_path in folder_path.iterdir():
            if not file_path.is_file():
                continue
            if not file_belongs_to_folder(file_path.name, contract):
                continue
            
            # Get relative path from docs/ directory
            # e.g., reports/NQU25_20250623-20250915_1m/image.png
            relative_path = file_path.relative_to(REPORTS_DIR.parent)
            relative_path_str = str(relative_path).replace('\\', '/')
            
            ext = file_path.suffix.lower()
            if ext == '.png':
                png_files.append(relative_path_str)
            elif ext == '.html':
                html_files.append(relative_path_str)
            elif ext == '.csv':
                csv_files.append(relative_path_str)
        
        # Also scan dashboards/ subfolder if it exists (only include files for this contract)
        dashboards_path = folder_path / 'dashboards'
        if dashboards_path.exists() and dashboards_path.is_dir():
            for file_path in dashboards_path.iterdir():
                if not file_path.is_file():
                    continue
                if not file_belongs_to_folder(file_path.name, contract):
                    continue
                
                # Get relative path from docs/ directory
                # e.g., reports/NQU25_20250623-20250915_1m/dashboards/dashboard.html
                relative_path = file_path.relative_to(REPORTS_DIR.parent)
                relative_path_str = str(relative_path).replace('\\', '/')
                
                ext = file_path.suffix.lower()
                if ext == '.png':
                    png_files.append(relative_path_str)
                elif ext == '.html':
                    html_files.append(relative_path_str)
                elif ext == '.csv':
                    csv_files.append(relative_path_str)
        
        # Sort file lists by filename
        png_files.sort()
        html_files.sort()
        csv_files.sort()
        
        # Store in manifest structure
        manifest[contract][timeframe][date_range] = {
            'png': png_files,
            'html': html_files,
            'csv': csv_files,
            'start_date': metadata['start'],
            'end_date': metadata['end']
        }
    
    # Convert to regular dict and sort
    # Sort contracts lexicographically
    sorted_contracts = sorted(manifest.keys())
    
    # Sort timeframes by numeric value (1m, 5m, 15m, 30m)
    sorted_manifest = {}
    for contract in sorted_contracts:
        sorted_manifest[contract] = {}
        timeframes = sorted(manifest[contract].keys(), key=extract_timeframe_minutes)
        
        for timeframe in timeframes:
            sorted_manifest[contract][timeframe] = {}
            # Sort date ranges by start date
            date_ranges = sorted(
                manifest[contract][timeframe].keys(),
                key=lambda dr: manifest[contract][timeframe][dr]['start_date']
            )
            
            for date_range in date_ranges:
                sorted_manifest[contract][timeframe][date_range] = manifest[contract][timeframe][date_range]
    
    # Write manifest to file
    manifest_file_path = MANIFEST_FILE
    manifest_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(manifest_file_path, 'w', encoding='utf-8') as f:
        json.dump(sorted_manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Manifest generated: {manifest_file_path}")
    print(f"  Contracts: {len(sorted_manifest)}")
    
    total_runs = sum(
        len(timeframe)
        for contract in sorted_manifest.values()
        for timeframe in contract.values()
    )
    print(f"  Total report runs: {total_runs}")
    print("=" * 60)


if __name__ == "__main__":
    generate_manifest()

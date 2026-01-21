#!/usr/bin/env python3
"""
sync_reports.py

Non-destructive script that copies VWAP report files from the source directory
to the website hosting directory. Only copies .png, .html, and .csv files.
Skips unchanged files by comparing size and modified time.
"""

import os
import shutil
from pathlib import Path
import re

# Source directory (where reports currently live)
SOURCE_DIR = Path(r"D:\alphadrip database\supabase-opti-database\LOCAL DATABASE\out\vwap_reports")

# Target directory (where we copy to)
# Changed to docs/reports (GitHub Pages serves from /docs, manifest scans docs/reports)
TARGET_DIR = Path(__file__).parent.parent / "docs" / "reports"

# Allowed file extensions
ALLOWED_EXTENSIONS = {'.png', '.html', '.csv'}

# Folder name pattern for valid report folders
# Format: CONTRACT_YYYYMMDD-YYYYMMDD_TIMEFRAME
REPORT_FOLDER_PATTERN = re.compile(r'^[A-Z0-9]+_\d{8}-\d{8}_\d+m$')

# Folders to skip
SKIP_FOLDERS = {'website hosting', 'OLD INVALID', 'VALID DATA', 'validation_dec', 'validation_sep'}


def should_copy_folder(folder_name):
    """
    Determine if a folder should be copied based on its name.
    Returns True if it matches the report folder pattern.
    """
    # Skip known non-report folders
    if folder_name in SKIP_FOLDERS:
        return False
    
    # Check if it matches the report folder pattern
    return bool(REPORT_FOLDER_PATTERN.match(folder_name))


def should_copy_file(file_path):
    """
    Determine if a file should be copied based on its extension.
    """
    return file_path.suffix.lower() in ALLOWED_EXTENSIONS


def files_match(source_file, target_file):
    """
    Compare two files by size and modified time.
    Returns True if they appear to be the same (no need to copy).
    """
    if not target_file.exists():
        return False
    
    try:
        source_stat = source_file.stat()
        target_stat = target_file.stat()
        
        # Compare size and modified time
        return (source_stat.st_size == target_stat.st_size and
                abs(source_stat.st_mtime - target_stat.st_mtime) < 1.0)  # Within 1 second
    except OSError:
        return False


def sync_reports():
    """
    Main sync function: copies report files from source to target.
    """
    if not SOURCE_DIR.exists():
        print(f"ERROR: Source directory does not exist: {SOURCE_DIR}")
        return
    
    # Create target directory if it doesn't exist
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Syncing reports from: {SOURCE_DIR}")
    print(f"Target directory: {TARGET_DIR}")
    print()
    
    copied_count = 0
    skipped_count = 0
    error_count = 0
    
    # Iterate through all items in source directory
    for item in SOURCE_DIR.iterdir():
        if not item.is_dir():
            continue
        
        folder_name = item.name
        
        # Check if this folder should be copied
        if not should_copy_folder(folder_name):
            print(f"Skipping folder (doesn't match pattern): {folder_name}")
            continue
        
        print(f"Processing folder: {folder_name}")
        
        # Create corresponding target folder
        target_folder = TARGET_DIR / folder_name
        target_folder.mkdir(exist_ok=True)
        
        # Process all files in the source folder (root level)
        for source_file in item.iterdir():
            if not source_file.is_file():
                continue
            
            # Check if file should be copied
            if not should_copy_file(source_file):
                continue
            
            target_file = target_folder / source_file.name
            
            # Check if file needs to be copied
            if files_match(source_file, target_file):
                skipped_count += 1
                print(f"  Skipped (unchanged): {source_file.name}")
            else:
                try:
                    shutil.copy2(source_file, target_file)
                    copied_count += 1
                    print(f"  Copied: {source_file.name}")
                except Exception as e:
                    error_count += 1
                    print(f"  ERROR copying {source_file.name}: {e}")
        
        # Process files in dashboards subfolder if it exists
        dashboards_folder = item / "dashboards"
        if dashboards_folder.exists() and dashboards_folder.is_dir():
            print(f"  Processing dashboards subfolder...")
            for source_file in dashboards_folder.iterdir():
                if not source_file.is_file():
                    continue
                
                # Only copy HTML files from dashboards folder
                if source_file.suffix.lower() != '.html':
                    continue
                
                # Copy to root of target folder (not in a subfolder)
                target_file = target_folder / source_file.name
                
                # Check if file needs to be copied
                if files_match(source_file, target_file):
                    skipped_count += 1
                    print(f"  Skipped (unchanged): dashboards/{source_file.name}")
                else:
                    try:
                        shutil.copy2(source_file, target_file)
                        copied_count += 1
                        print(f"  Copied: dashboards/{source_file.name}")
                    except Exception as e:
                        error_count += 1
                        print(f"  ERROR copying dashboards/{source_file.name}: {e}")
        
        print()
    
    print("=" * 60)
    print(f"Sync complete!")
    print(f"  Copied: {copied_count} files")
    print(f"  Skipped (unchanged): {skipped_count} files")
    print(f"  Errors: {error_count} files")
    print("=" * 60)


if __name__ == "__main__":
    sync_reports()

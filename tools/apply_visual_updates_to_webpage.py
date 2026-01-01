#!/usr/bin/env python3
"""
apply_visual_updates_to_webpage.py

Replaces the original hold_fail_rates.html files in the reports folder
with the updated versions from reports_visual_update.
This makes them visible on the main website.
"""

from pathlib import Path
import shutil

# Directories
REPORTS_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports"
VISUAL_UPDATE_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports_visual_update"


def apply_visual_updates():
    """
    Copy updated files from visual_update folder to main reports folder.
    """
    if not VISUAL_UPDATE_DIR.exists():
        print(f"ERROR: Visual update directory does not exist: {VISUAL_UPDATE_DIR}")
        print("Please run update_hold_fail_rates_visual.py first.")
        return
    
    if not REPORTS_DIR.exists():
        print(f"ERROR: Reports directory does not exist: {REPORTS_DIR}")
        return
    
    print(f"Copying updated files from: {VISUAL_UPDATE_DIR}")
    print(f"To: {REPORTS_DIR}")
    print()
    
    processed_count = 0
    copied_count = 0
    error_count = 0
    
    # Find all hold_fail_rates.html files in visual_update folder
    for updated_file in VISUAL_UPDATE_DIR.rglob("*hold_fail_rates.html"):
        try:
            processed_count += 1
            relative_path = updated_file.relative_to(VISUAL_UPDATE_DIR)
            target_path = REPORTS_DIR / relative_path
            
            print(f"Processing: {relative_path}")
            
            # Ensure target directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the updated file to replace the original
            shutil.copy2(updated_file, target_path)
            
            copied_count += 1
            print(f"  [OK] Replaced: {target_path.relative_to(REPORTS_DIR)}")
            
        except Exception as e:
            error_count += 1
            print(f"  [ERROR] {e}")
    
    print()
    print("=" * 60)
    print(f"Processing complete!")
    print(f"  Processed: {processed_count} files")
    print(f"  Replaced: {copied_count} files")
    print(f"  Errors: {error_count} files")
    print()
    print("The updated files are now live on the website!")
    print("=" * 60)


if __name__ == "__main__":
    apply_visual_updates()

#!/usr/bin/env python3
"""
remove_downloads_sections.py

Removes "Downloads" sections from all HTML report files.
Non-destructive: only modifies files in the website hosting directory.
"""

import re
from pathlib import Path

# Reports directory (where HTML files are hosted)
REPORTS_DIR = Path(__file__).parent.parent / "site" / "docs" / "reports"


def remove_downloads_section(html_content):
    """
    Remove Downloads section from HTML content.
    Returns modified content.
    """
    content = html_content
    
    # Pattern 1: Match the entire download-section div with all its content
    # This pattern matches from <div class="download-section"> to the closing </div>
    # It handles nested content and whitespace
    pattern1 = r'<div\s+class=["\']download-section["\'][^>]*>.*?</div>\s*'
    content = re.sub(pattern1, '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Pattern 2: More aggressive - match any div containing "Downloads" heading followed by download links
    # This catches variations in structure
    pattern2 = r'<div[^>]*>.*?<h3[^>]*>Downloads</h3>.*?</div>\s*'
    content = re.sub(pattern2, '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Pattern 3: Match standalone Downloads sections that might not have the class
    # Look for <h3>Downloads</h3> followed by download links until next section
    pattern3 = r'<h3[^>]*>Downloads</h3>.*?(?=<div\s+class=["\']panel["\']|<h3|<script|</body>)'
    content = re.sub(pattern3, '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove CSS for download-section and download-link
    # Remove .download-section CSS block (with any whitespace)
    css_pattern1 = r'\.download-section\s*\{[^}]*\}\s*'
    content = re.sub(css_pattern1, '', content, flags=re.DOTALL)
    
    # Remove .download-link CSS block
    css_pattern2 = r'\.download-link\s*\{[^}]*\}\s*'
    content = re.sub(css_pattern2, '', content, flags=re.DOTALL)
    
    # Remove .download-link:hover CSS block
    css_pattern3 = r'\.download-link:hover\s*\{[^}]*\}\s*'
    content = re.sub(css_pattern3, '', content, flags=re.DOTALL)
    
    # Remove comment "/* Links & Downloads */" if it exists
    content = re.sub(r'/\*\s*Links\s*&\s*Downloads\s*\*/\s*', '', content, flags=re.IGNORECASE)
    
    # Clean up any double newlines or excessive whitespace left behind
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    return content


def process_html_files():
    """
    Process all HTML files in the reports directory and remove Downloads sections.
    """
    if not REPORTS_DIR.exists():
        print(f"ERROR: Reports directory does not exist: {REPORTS_DIR}")
        return
    
    print(f"Scanning for HTML files in: {REPORTS_DIR}")
    print()
    
    processed_count = 0
    modified_count = 0
    error_count = 0
    
    # Find all HTML files recursively
    for html_file in REPORTS_DIR.rglob("*.html"):
        try:
            processed_count += 1
            print(f"Processing: {html_file.relative_to(REPORTS_DIR)}")
            
            # Read the file
            with open(html_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Check if file contains Downloads section (more comprehensive check)
            has_downloads = (
                'download-section' in original_content.lower() or 
                'Downloads</h3>' in original_content or
                '<h3[^>]*>Downloads</h3>' in original_content or
                'download-link' in original_content.lower()
            )
            
            if has_downloads:
                # Remove Downloads section
                modified_content = remove_downloads_section(original_content)
                
                # Verify removal was successful
                still_has_downloads = (
                    'download-section' in modified_content.lower() or 
                    'Downloads</h3>' in modified_content
                )
                
                # Only write if content changed and Downloads section was actually removed
                if modified_content != original_content and not still_has_downloads:
                    # Write back the modified content
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    modified_count += 1
                    print(f"  [OK] Removed Downloads section")
                elif still_has_downloads:
                    print(f"  [WARN] Downloads section found but removal may have failed")
                else:
                    print(f"  [SKIP] No Downloads section found")
            else:
                print(f"  [SKIP] No Downloads section found")
            
        except Exception as e:
            error_count += 1
            print(f"  [ERROR] {e}")
    
    print()
    print("=" * 60)
    print(f"Processing complete!")
    print(f"  Processed: {processed_count} files")
    print(f"  Modified: {modified_count} files")
    print(f"  Errors: {error_count} files")
    print("=" * 60)


if __name__ == "__main__":
    process_html_files()

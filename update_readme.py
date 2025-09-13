#!/usr/bin/env python3
"""
Script to update README.md with a list of HTML files in the repository.
"""

import os
import glob
import re
from datetime import datetime

def parse_existing_dates(content):
    """Parse existing dates from README content."""
    existing_dates = {}
    
    # Find the HTML files section
    html_section_start = "## HTML Files\n\n"
    if html_section_start not in content:
        return existing_dates
    
    start_idx = content.find(html_section_start)
    section_content = content[start_idx:]
    
    # Extract file dates using regex
    pattern = r"- \[([^\]]+\.html)\]\([^)]+\) - \*([^*]+)\*"
    matches = re.findall(pattern, section_content)
    
    for filename, date_str in matches:
        try:
            # Parse the existing date
            date_obj = datetime.strptime(date_str, "%B %d, %Y")
            existing_dates[filename] = date_obj
        except ValueError:
            continue
    
    return existing_dates

def get_html_files():
    """Get all HTML files in the root directory with their modification dates."""
    html_files = []
    
    for html_file in glob.glob("*.html"):
        if html_file == "404.html":  # Skip 404.html
            continue
            
        try:
            mtime = os.path.getmtime(html_file)
            mod_date = datetime.fromtimestamp(mtime)
            html_files.append((html_file, mod_date))
        except OSError:
            continue
    
    # Sort by modification date (newest first)
    html_files.sort(key=lambda x: x[1], reverse=True)
    return html_files

def update_readme():
    """Update README.md with the list of HTML files."""
    html_files = get_html_files()
    
    if not html_files:
        print("No HTML files found to add to README.")
        return
    
    # Read existing README
    try:
        with open("README.md", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "# Repository Files\n\n"
    
    # Parse existing dates from README
    existing_dates = parse_existing_dates(content)
    
    # Find the HTML files section or create it
    html_section_start = "## HTML Files\n\n"
    html_section_end = "\n## "
    
    # Remove existing HTML files section if it exists
    if html_section_start in content:
        start_idx = content.find(html_section_start)
        end_idx = content.find(html_section_end, start_idx + len(html_section_start))
        
        if end_idx == -1:
            # HTML section is at the end
            content = content[:start_idx]
        else:
            # HTML section is in the middle
            content = content[:start_idx] + content[end_idx:]
    
    # Generate new HTML files section
    html_list = []
    updated_files = 0
    
    for html_file, mod_date in html_files:
        # Check if file exists in README and compare dates
        if html_file in existing_dates:
            existing_date = existing_dates[html_file]
            # Only update if file modification time is newer than README date
            # Add a small tolerance (1 hour) to account for time zone differences
            time_diff = abs((mod_date - existing_date).total_seconds())
            if time_diff > 3600:  # More than 1 hour difference
                date_str = mod_date.strftime("%B %d, %Y")
                updated_files += 1
            else:
                # Use existing date to avoid unnecessary updates
                date_str = existing_date.strftime("%B %d, %Y")
        else:
            # New file, use current modification date
            date_str = mod_date.strftime("%B %d, %Y")
            updated_files += 1
        
        html_list.append(f"- [{html_file}]({html_file}) - *{date_str}*")
    
    html_section = html_section_start + "\n".join(html_list) + "\n\n"
    
    # Add the HTML section at the end
    content = content.rstrip() + "\n\n" + html_section
    
    # Write updated README
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"Updated README.md with {len(html_files)} HTML files ({updated_files} files had date changes).")

if __name__ == "__main__":
    update_readme()
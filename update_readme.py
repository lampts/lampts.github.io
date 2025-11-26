#!/usr/bin/env python3
"""
Script to update README.md with a list of HTML files in the repository.
Uses Git history to determine the true last modification date.
"""

import os
import glob
import subprocess
from datetime import datetime

def get_git_file_date(filepath):
    """Get the last commit date for a file from git history."""
    try:
        # git log -1 --format="%ad" --date=format:"%Y-%m-%d %H:%M:%S" -- <file>
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ad', '--date=format:%Y-%m-%d %H:%M:%S', '--', filepath],
            capture_output=True,
            text=True,
            check=True
        )
        date_str = result.stdout.strip()

        # Fallback: If git returns empty (e.g. shallow clone or new file not in history yet)
        if not date_str:
            return datetime.fromtimestamp(os.path.getmtime(filepath))

        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    except (subprocess.CalledProcessError, ValueError):
        # Fallback to filesystem time if git fails
        return datetime.fromtimestamp(os.path.getmtime(filepath))

def get_html_files():
    """Get all HTML files in the root directory with their git commit dates."""
    html_files = []

    for html_file in glob.glob("*.html"):
        if html_file == "404.html":  # Skip 404.html
            continue

        mod_date = get_git_file_date(html_file)
        html_files.append((html_file, mod_date))

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

    # Find the HTML files section or create it
    html_section_start = "## HTML Files\n\n"
    # Look for the next header (## ) to define the end of our section
    # Regex is safer here to ensure we don't accidentally cut the file wrong
    import re

    # Normalize content separation
    if html_section_start in content:
        start_idx = content.find(html_section_start)
        # Find next header after our section
        next_header_match = re.search(r'\n## ', content[start_idx + len(html_section_start):])

        if next_header_match:
            end_idx = start_idx + len(html_section_start) + next_header_match.start()
            # Keep the top part and the bottom part
            content_top = content[:start_idx]
            content_bottom = content[end_idx:]
            content = content_top + content_bottom
        else:
            # HTML section is at the end
            content = content[:start_idx]

    # Generate new HTML files section
    html_list = []

    for html_file, mod_date in html_files:
        date_str = mod_date.strftime("%B %d, %Y")
        # Format: - [filename.html](filename.html) - *Month DD, YYYY*
        html_list.append(f"- [{html_file}]({html_file}) - *{date_str}*")

    html_section = html_section_start + "\n".join(html_list) + "\n"

    # Ensure proper spacing and append the new section
    content = content.rstrip() + "\n\n" + html_section

    # Write updated README
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated README.md with {len(html_files)} HTML files based on Git history.")

if __name__ == "__main__":
    update_readme()

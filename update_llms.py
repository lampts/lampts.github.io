#!/usr/bin/env python3
"""
Regenerate the crawler-facing tool listings from the TOOLS array in tools/index.html.

- tools/index.html: static <a class="card"> links inside #grid, so crawlers that
  don't run JavaScript (GPTBot, ClaudeBot, PerplexityBot) still see every tool.
  The page's JS clears and re-renders the grid, so visitors see no difference.
- llms.txt: the "## Tools" and "## Notes" sections, between generated markers.

Run after adding a tool: python3 update_llms.py
"""

import glob
import html
import os
import re

SITE = "https://www.lampt.org"
TOOLS_INDEX = "tools/index.html"
LLMS = "llms.txt"

TOOL_RE = re.compile(
    r'\{\s*title:\s*"([^"]+)",\s*href:\s*"([^"]+)",\s*date:\s*"([^"]+)",\s*tag:\s*"([^"]+)"'
)


def read(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def meta_description(path):
    if not os.path.exists(path):
        return ""
    m = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', read(path), re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def page_title(path):
    m = re.search(r"<title>([^<]*)</title>", read(path), re.I)
    return html.unescape(m.group(1)).strip() if m else os.path.basename(path)


def local_path(href):
    p = href.lstrip("/")
    return p + "index.html" if p.endswith("/") or not p else p


def replace_between(text, start, end, body):
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pattern.search(text):
        raise SystemExit(f"markers not found: {start} … {end}")
    return pattern.sub(lambda _: f"{start}\n{body}\n{end}", text)


def main():
    tools = [dict(zip(("title", "href", "date", "tag"), t)) for t in TOOL_RE.findall(read(TOOLS_INDEX))]
    tools.sort(key=lambda t: t["date"], reverse=True)
    for t in tools:
        t["desc"] = meta_description(local_path(t["href"]))

    # 1. Static cards in tools/index.html (same markup the JS renders)
    cards = "\n".join(
        f'<a class="card" href="{t["href"]}"><div class="card-title">{html.escape(t["title"])}</div>'
        f'<div class="card-meta"><span class="card-date">{t["date"]}</span>'
        f'<span class="card-tag">{t["tag"]}</span></div></a>'
        for t in tools
    )
    page = replace_between(read(TOOLS_INDEX), "<!-- static-tools:start -->", "<!-- static-tools:end -->", cards)
    with open(TOOLS_INDEX, "w", encoding="utf-8") as f:
        f.write(page)

    # 2. llms.txt tool + TIL sections
    by_tag = {}
    for t in tools:
        by_tag.setdefault(t["tag"], []).append(t)
    lines = [f"## Tools ({len(tools)} standalone, single-file HTML apps; index: {SITE}/tools/)", ""]
    for tag in sorted(by_tag):
        lines.append(f"### {tag}")
        for t in by_tag[tag]:
            note = f": {t['desc']}" if t["desc"] else ""
            lines.append(f"- [{t['title']}]({SITE}{t['href']}){note} ({t['date']})")
        lines.append("")

    lines += ["## Notes (TIL explainers)", ""]
    for path in sorted(glob.glob("til/*.html")):
        desc = meta_description(path)
        lines.append(f"- [{page_title(path)}]({SITE}/{path})" + (f": {desc}" if desc else ""))

    llms = replace_between(read(LLMS), "<!-- generated:start -->", "<!-- generated:end -->", "\n".join(lines).rstrip())
    with open(LLMS, "w", encoding="utf-8") as f:
        f.write(llms)

    print(f"{len(tools)} tools, {sum(1 for t in tools if t['desc'])} with descriptions")


if __name__ == "__main__":
    main()

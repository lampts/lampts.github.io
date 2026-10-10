# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal website for Pham Thanh Lam (lampts.github.io / lampt.org). A Jekyll site built on the **al-folio** theme (README.md is the upstream al-folio README), plus a large collection of hand-written standalone HTML pages: a homepage, interactive tools, and TIL notes.

## Development Commands

```bash
# Docker (recommended) — serves on port 8080 with live reload
docker-compose up

# Standard Jekyll
bundle install
bundle exec jekyll serve --lsi        # dev server with live reload
bundle exec jekyll build --lsi        # production build

# Validate build (no test framework — Jekyll build is the validation step)
bundle exec jekyll build
```

Standalone HTML pages need no build. Open them directly in a browser, or serve the repo root with any static server.

## Deployment

- `.github/workflows/deploy.yml` runs on push to master/main. It builds with Ruby 3.2.1 and deploys `_site/` to the gh-pages branch.
- `.github/workflows/update-readme.yml` also runs on push to master. It runs `update_readme.py`, which regenerates the HTML file list in README.md from git dates, and commits the result back ("📄 Update README with HTML files list"). Expect to `git pull` before pushing again.

## Architecture

### Two kinds of content

1. **Jekyll-managed content**: standard al-folio pages that go through the build pipeline. They use `_layouts/`, `_includes/` and `_sass/`, and their content lives in `_pages/`, `_posts/`, `_news/`, `_projects/` and `_bibliography/`. The theme's sample posts are still mostly in place, so most active work happens in the standalone pages below.

2. **Standalone HTML pages**: self-contained files with inline CSS/JS, no front matter and no layout dependency. GitHub Pages serves them as-is.
   - `index.html` (root) is the hand-maintained lampt.org homepage. Note that `_pages/about.md` also claims `permalink: /`. The homepage hardcodes a tool count ("All N tools →") and a few featured tools, so update those when tools change.
   - `tools/`: the current home for new tools. `tools/index.html` is the tool directory: a `TOOLS` JS array of `{ title, href, date, tag }` entries that is sorted by date and also drives the meta/OG tool count. **Every new tool needs an entry appended to this array.** Tags in use include `ai`, `finance`, `viz`, `learning`, `fun`, `dev` and `writing`.
   - Root-level `*.html` files (e.g. `lamp.html`, `tvm_calculator.html`, `collatz.html`) are older tools. They are listed under the "root-level tools" section of the same `TOOLS` array.
   - `til/`: standalone "today I learned" explainer pages.
   - `code/`: scratch scripts and assets, not site pages.
   - `private/`: excluded from the Jekyll build in `_config.yml`.
   - `tools/sw.js` and `tools/manifest.json` are the PWA service worker and manifest for the Inkflow reader (`tao.html`), not for the whole tools directory.

When you add a tool, create one self-contained HTML file in `tools/` and add its `TOOLS` entry in `tools/index.html`. Commit both together as "Add <Tool name> …" (see the git log).

### Key configuration

- `_config.yml`: central config for site metadata, theme toggles (dark mode, math, masonry, etc.), plugin settings, library versions and the build `exclude` list.
- Jekyll Scholar is configured under `scholar:` in `_config.yml` and reads BibTeX from `_bibliography/papers.bib`.
- `llms.txt`: an LLM-readable profile summary of the site owner. Keep it consistent with the homepage when bio facts change.

### Layout chain

`default.html` wraps all other layouts (`about.html`, `post.html`, `page.html`, `distill.html`, `cv.html`, `bib.html`). Shared components (head, header, footer, scripts) are in `_includes/`.

### Plugin ecosystem

Key plugins: `jekyll-scholar` (academic publications), `jekyll-paginate-v2`, `jekyll-archives` (year/tag/category), `jekyll-diagrams` (requires mermaid.cli via npm), `jekyll-minifier` and `jekyll-toc`.

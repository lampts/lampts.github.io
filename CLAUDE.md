# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal academic website for Pham Thanh Lam (lampts.github.io / lampt.org), built with Jekyll using the **al-folio** theme. Combines a standard Jekyll blog/portfolio with standalone HTML tools.

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

## Deployment

GitHub Actions (`.github/workflows/deploy.yml`) triggers on push to master/main. Builds with Ruby 3.2.1 and deploys the `_site/` folder to gh-pages branch via `JamesIves/github-pages-deploy-action`.

## Architecture

### Two types of content

1. **Jekyll-managed content** — Standard al-folio theme pages that go through the Jekyll build pipeline. Uses layouts in `_layouts/`, includes from `_includes/`, styles from `_sass/`. Content lives in `_pages/`, `_posts/`, `_news/`, `_projects/`, `_bibliography/`.

2. **Standalone HTML tools** — ~30 self-contained HTML files in the repo root (e.g., `lamp.html`, `llm.html`, `tvm_calculator.html`, `collatz.html`, `qr.html`). These are fully standalone (inline CSS/JS, no Jekyll front matter, no layout dependency). They are served as-is by GitHub Pages. When creating new tools, follow this pattern — single-file HTML with everything inlined.

### Key configuration

- `_config.yml` — Central config for site metadata, theme toggles (dark mode, math, masonry, etc.), plugin settings, and library versions
- Jekyll Scholar configured in `_config.yml` under `scholar:` — reads BibTeX from `_bibliography/papers.bib`
- About page (`_pages/about.md`) is the site homepage (permalink: `/`)

### Layout chain

`default.html` → wraps all other layouts (`about.html`, `post.html`, `page.html`, `distill.html`, `cv.html`, `bib.html`). Shared components (head, header, footer, scripts) are in `_includes/`.

### Plugin ecosystem

Key plugins: `jekyll-scholar` (academic publications), `jekyll-paginate-v2`, `jekyll-archives` (year/tag/category), `jekyll-diagrams` (requires mermaid.cli via npm), `jekyll-minifier`, `jekyll-toc`.

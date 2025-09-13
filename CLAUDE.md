# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal academic website built with Jekyll using the al-folio theme. It serves as a portfolio and blog for Pham Thanh Lam, featuring:
- Personal about page with professional background
- Blog posts and news announcements
- Project showcases  
- Academic publications management via BibTeX
- Custom HTML tools and calculators

## Development Commands

### Local Development with Docker (Recommended)
```bash
# Using pre-built Docker image
docker-compose up

# Build and run custom Docker image
docker-compose -f docker-local.yml up

# Alternative script-based approach
./bin/dockerhub_run.sh
```

### Local Development (Standard Jekyll)
```bash
# Install dependencies
bundle install

# Serve locally with live reload
bundle exec jekyll serve --lsi

# Build for production
bundle exec jekyll build --lsi
```

### Testing and Validation
```bash
# Build the site (validates Jekyll compilation)
bundle exec jekyll build

# Check for broken links and validate HTML (if configured)
# No specific testing framework configured - rely on Jekyll build validation
```

## Architecture and Structure

### Core Jekyll Structure
- `_config.yml` - Main site configuration with personal info, theme settings, and plugin configs
- `_layouts/` - HTML templates (about, post, page, distill, etc.)
- `_includes/` - Reusable HTML components and scripts
- `_sass/` - Stylesheet sources and theme customization
- `_pages/` - Static pages like About
- `_posts/` - Blog posts in Markdown
- `_news/` - News/announcement items
- `_projects/` - Project showcase items

### Custom Content
- Root-level HTML files - Custom tools and calculators (lamp.html, llm.html, etc.)
- `assets/` - Images, CSS, JS, PDFs, and other static resources
- `_bibliography/` - Academic papers in BibTeX format
- `_data/` - YAML data files for CV, repositories, venues, etc.

### Key Features
- **Academic Publications**: Managed via Jekyll Scholar plugin with BibTeX
- **Math Support**: MathJax integration for mathematical expressions
- **Dark Mode**: Theme switching capability
- **Responsive Design**: Bootstrap-based responsive layouts
- **GitHub Integration**: Repository stats and trophy displays
- **Social Media**: Integrated social links and Open Graph meta tags

### Deployment
- **GitHub Pages**: Automatic deployment via GitHub Actions on push to master/main
- **Workflow**: `.github/workflows/deploy.yml` handles building and deployment
- **Build Process**: Ruby 3.2.1, bundle install, Jekyll build, deploy to gh-pages branch

### Content Management
- **Blog Posts**: Add Markdown files to `_posts/` with YAML front matter
- **Projects**: Add to `_projects/` directory
- **News**: Add to `_news/` for announcements
- **Publications**: Edit `_bibliography/papers.bib` for academic papers
- **CV Data**: Update YAML files in `_data/` directory

### Custom Tools
The site includes numerous standalone HTML tools (lamp.html, llm.html, calculator tools, etc.) that appear to be interactive utilities and demos, likely related to the owner's work in AI/ML and data science.

### Dependencies
- Jekyll with multiple plugins (scholar, diagrams, feed, etc.)
- Ruby gems managed via Bundler
- Bootstrap 4.6.1 for responsive design
- MathJax 3.2.0 for math rendering
- FontAwesome 5.15.4 for icons
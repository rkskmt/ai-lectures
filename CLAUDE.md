# CLAUDE.md

## Project Overview

Quarto-based AI lecture website ("AI Lectures"). Slide decks for machine learning topics, written in Japanese.

## Tech Stack

- **Quarto** website project with `clean-revealjs` slide format
- **Python 3** via Jupyter kernel for code cells
- **MathJax** for math rendering
- **Mermaid** for diagrams
- Extensions: `lightbox`

## Structure

- `_quarto.yml` — site config and navigation
- `_metadata.yaml` — shared slide format settings (revealjs theme, CSS, mermaid config)
- `*.qmd` — lecture content files
- `index.qmd` — top-level listing of lectures
- `imgs/` — image assets
- `_extensions/` — Quarto extensions

## Conventions

- Content is written in **Japanese**
- `##` がスライドの区切り（`---` は使わない）。`##` は section titles (bold + border-bottom)、`###` は subsection titles (blue background)
- Use Quarto callouts (`.callout-note`) for key concepts
- Code cells use `jupyter: python3`
- Image sizing via `.fig-small` (300px) and `.fig-medium` (400px) CSS classes

## JavaScript in .qmd

**Event listener priority:** Inline JS in `.qmd` files loses to Quarto/revealjs event handlers by default. To intercept keyboard events before revealjs, use capture phase and stop propagation:
```javascript
document.addEventListener('keydown', function(e) {
  e.preventDefault();
  e.stopImmediatePropagation();
  // ...
}, true);  // capture phase
```

## Build

```bash
quarto preview   # local dev server
quarto render    # build to _site/
```

## publish to github page
https://rkskmt.github.io/ip3200/

```bash
quarto publish gh-pages
```

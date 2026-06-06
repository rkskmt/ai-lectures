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

## Language

- Content is written in **Japanese**
- Code comments, commit messages, and Claude's reasoning should be in **English**

## Matplotlib

- **Whenever using matplotlib, `import japanize_matplotlib`** — even if the current plot has no Japanese text, for consistency.
- **Do not use `rcParams['font.family']`** for Japanese — it never works reliably. `japanize_matplotlib` is the only reliable approach.

## Conventions

- Content is written in **Japanese**
- `##` がスライドの区切り（`---` は使わない）。`##` は section titles (bold + border-bottom)、`###` は subsection titles (blue background)
- Use Quarto callouts (`.callout-note`) for key concepts
- Code cells use `jupyter: python3`
- Image sizing via `.fig-small` (300px) and `.fig-medium` (400px) CSS classes
- **When adding a new `.qmd`, always update both `index.qmd` and `_quarto.yml`.** `index.qmd` is the link list; `_quarto.yml` is the navbar. Missing either one leaves them out of sync.

## Build

```bash
quarto preview --port 4321   # local dev server (fixed port)
quarto render                # build to _site/
```

**Do not run `quarto preview` or `quarto render` yourself.** The user handles previewing and building.

## Style or functionality changes

**JavaScript robustness:** Inline JS in `_metadata.yaml` must be defensive. On slow networks, DOM elements or `Reveal` may not be ready when scripts run. Wrap operations in `try/catch` and check for existence (`if (!window.Reveal) return;`). Uncaught errors can break other scripts (e.g., MathJax) loaded on the same page.

**Event listener priority:** Inline JS in `.qmd` files loses to Quarto/revealjs event handlers by default. To intercept keyboard events before revealjs, use capture phase and stop propagation:
```javascript
document.addEventListener('keydown', function(e) {
  e.preventDefault();
  e.stopImmediatePropagation();
  // ...
}, true);  // capture phase
```

## Deploy

```bash
quarto publish gh-pages
```

https://rkskmt.github.io/ai-lectures/

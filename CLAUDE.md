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

## Teaching Philosophy

Use Python as the vehicle, but frame concepts as broadly as possible. Where a concept is universal (e.g., iteration, container, method), note that it exists across languages. Prefer language-agnostic expressions alongside Python-specific ones.

## Matplotlib

- **Whenever using matplotlib, `import japanize_matplotlib`** — even if the current plot has no Japanese text, for consistency.
- **Do not use `rcParams['font.family']`** for Japanese — it never works reliably. `japanize_matplotlib` is the only reliable approach.

## Conventions

- Content is written in **Japanese**
- `##` delimits slides (do not use `---`)
- `_metadata.yaml` applies `clean-revealjs` to all `.qmd` files
- **Do not add frontmatter to `index.qmd`.** Quarto **merges** (not overwrites) `format` from `_metadata.yaml` and the file, so adding `format: html` causes it to render in both formats and trigger a `rename` error. Raw HTML (e.g. `<details>/<summary>`) is fine — it needs no frontmatter.
- **Do not use `listing:` in `index.qmd` either.** Same reason — it requires `format: html`, which conflicts.
- `render: ["*.qmd"]` in `_quarto.yml` prevents `.md` files (e.g. CLAUDE.md) from being rendered
- **When adding a new `.qmd`, always update both `index.qmd` and `_quarto.yml`.** `index.qmd` is the link list; `_quarto.yml` is the navbar. Missing either one leaves them out of sync.
- **Never add numbers to slide section headers or `index.qmd` link text.** Numbered slides (e.g. `## １. ...`) and numbered links (e.g. `第N回`) break on reorder — every insert or swap requires renaming every entry after it. Use plain titles only (e.g. `## 汎化性能を測る`, `[評価と汎化](classification-evaluation.qmd)`). Same rule applies to `_quarto.yml` navbar `text:` labels.
- Use Quarto callouts (`.callout-note`) for key concepts
- Slide text should use **bullet points**, not prose sentences
- Code cells use `jupyter: python3`
- Image sizing via `.fig-small` (300px) and `.fig-medium` (400px) CSS classes
- **Highlight marker (`==text==`):** `hl.lua` filter turns `==text==` into a highlighted span (white text + cyan outline). For text with spaces use `[a b]{.hl}`.
- **MathJax `\vec{}` height fix:** `\vec{a}` and `\vec{b}` render at different heights because `b` has an ascender. Use `\vec{\vphantom{b}a}` to match the arrow height of shorter letters to `b`.

## Error Handling

- **No `getattr`** — use direct attribute access (`obj.attr`).
- **Never swallow failures.** Wrong type, missing value, missing package, or unexpected state must raise an error, not be hidden by `try/except`, `continue`, `pass`, a silent fallback/default, or `.get()` when the key must exist.
- Prefer an immediate crash with a stack trace. It points directly at the source of the problem; a swallowed failure lets corrupted state propagate and usually surfaces later as a harder-to-debug bug.
- If a lecture needs a dependency, add it to `environment.yml`. Do not add fallback code for a missing dependency.

## Build

```bash
quarto preview --port 4321   # local dev server (fixed port)
quarto render                # build to _site/
```

**Do not run `quarto preview` or `quarto render` yourself.** The user handles previewing and building.

## Style or functionality changes

Most tasks are content editing — the conventions above are all you need.

When changing CSS, theme, JavaScript, or `_metadata.yaml`: read **[doc/troubleshooting.md](doc/troubleshooting.md)** first. It covers stale preview/cache behavior and Pandoc code-block selectors.

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

## Reference Docs

- **[doc/troubleshooting.md](doc/troubleshooting.md)** — CSS/style changes: stale preview/cache behavior and Pandoc code-block selectors

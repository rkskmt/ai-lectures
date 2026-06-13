# CLAUDE.md

## Project Overview

Quarto-based AI lecture website ("AI Lectures"). Slide decks for machine learning topics, written in Japanese.

## Tech Stack

- **Quarto** website project with `revealjs` slide format (theme.scss + custom.css, no theme extension)
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
- **English/Japanese mix in slides — intentional, not a defect:**
  - Explanatory prose, annotations, and callouts: **Japanese**. Japanese data/column names stay Japanese where natural.
  - **Key technical terms get English alongside Japanese at first appearance** (e.g. 過学習（overfitting）, 固有値（eigenvalue）). This is a feature — students must learn the English. When auditing, **add the English where a term first appears without it** (this is worth a dedicated inspection pass).
  - **Standard English in matplotlib figures is fine — leave it.** Axis/label/title text that is itself a term a student should know (e.g. `Iteration Trajectory`, `inertia`, `Convergence Point`) is good exposure; do not Japanize it just for uniformity. Use Japanese in figures only when the text is *explanation* aimed at understanding, not a term.

## Teaching Philosophy

Use Python as the vehicle, but frame concepts as broadly as possible. Where a concept is universal (e.g., iteration, container, method), note that it exists across languages. Prefer language-agnostic expressions alongside Python-specific ones.

## Matplotlib

- **Whenever using matplotlib, `import japanize_matplotlib`** — even if the current plot has no Japanese text, for consistency.
- **Do not use `rcParams['font.family']`** for Japanese — it never works reliably. `japanize_matplotlib` is the only reliable approach.

## Conventions

- Content is written in **Japanese**
- `##` delimits slides (do not use `---`)
- `_metadata.yaml` applies `revealjs` (theme: default + theme.scss, plus custom.css and slide-ui.js via include-in-header) to all `.qmd` files
- **Do not add frontmatter to `index.qmd`.** Quarto **merges** (not overwrites) `format` from `_metadata.yaml` and the file, so adding `format: html` causes it to render in both formats and trigger a `rename` error. Raw HTML (e.g. `<details>/<summary>`) is fine — it needs no frontmatter.
- **Do not use `listing:` in `index.qmd` either.** Same reason — it requires `format: html`, which conflicts.
- `render: ["*.qmd"]` in `_quarto.yml` prevents `.md` files (e.g. CLAUDE.md) from being rendered
- **When adding a new `.qmd`, add it to `index.qmd`.** It is the site's only navigation: every page renders as revealjs slides, so the Quarto website navbar is never displayed — do not maintain a `navbar` in `_quarto.yml` (verified 2026-06: no navbar element appears in any built page).
- **`search-ui.js` provides site-wide full-text search**: a 検索 button + modal on every deck (loaded via `_metadata.yaml` include-in-header, listed in `_quarto.yml` resources) and the inline box on `index.qmd` (`#search-input`/`#search-results`). It reads Quarto's generated `search.json` and deep-links to slides via `#/slide-id` — no per-lecture maintenance.
- **Never add numbers to slide section headers or `index.qmd` link text.** Numbered slides (e.g. `## １. ...`) and numbered links (e.g. `第N回`) break on reorder — every insert or swap requires renaming every entry after it. Use plain titles only (e.g. `## 汎化性能を測る`, `[過学習と汎化](classification-evaluation.qmd)`).
- Use Quarto callouts (`.callout-note`) for key concepts
- Slide text should use **bullet points**, not prose sentences
- Code cells use `jupyter: python3`
- **Assume students run Python in VSCode as normal `.py` scripts, not notebooks.** Code examples must be copy-pasteable into a Python file and still show the intended output.
- **Do not use notebook-only display style** such as a bare `df`, `df.head()`, `df.shape`, `series`, or expression as the final line when the goal is to show output. Use `print(...)` for textual/tabular output (e.g. `print(df.head())`, `print(df.shape)`). Use plotting calls like `plt.show()` when the goal is a figure.
- For large tables or arrays, show only a small, intentional preview such as `print(df.head())`; do not dump all rows unless the full output is pedagogically necessary.
- Image sizing via `.fig-small` (300px) and `.fig-medium` (400px) CSS classes
- **Highlight marker (`==text==`):** `hl.lua` filter turns `==text==` into a highlighted span (white text + cyan outline). For text with spaces use `[a b]{.hl}`.
- **MathJax `\vec{}` height fix:** `\vec{a}` and `\vec{b}` render at different heights because `b` has an ascender. Use `\vec{\vphantom{b}a}` to match the arrow height of shorter letters to `b`.

## Error Handling

- **No `getattr`** — use direct attribute access (`obj.attr`).
- **Never swallow failures.** Wrong type, missing value, missing package, or unexpected state must raise an error, not be hidden by `try/except`, `continue`, `pass`, a silent fallback/default, or `.get()` when the key must exist.
- Prefer an immediate crash with a stack trace. It points directly at the source of the problem; a swallowed failure lets corrupted state propagate and usually surfaces later as a harder-to-debug bug.
- If a lecture needs a dependency, add it to this project's `environment.yml` and make sure the actual `ai` Conda environment is updated too. Do not add fallback code for a missing dependency, and do not install packages only into a parent or unrelated environment.

## Build

```bash
quarto preview --port 4321   # local dev server (fixed port)
quarto render                # build to _site/
```

**Heavy render:** `mnist-project.qmd` downloads MNIST (~12MB, cached in gitignored `data/`) and trains an MLP for 3 epochs on CPU — expect a few minutes for that file. `pytorch-intro.qmd` and `nn-numpy.qmd` each train for a few seconds.

**Do not run `quarto preview` or `quarto render` yourself.** The user handles previewing and building.

## Self-contained, reproducible builds

Each repo must build from a **fresh clone** on any machine — students build it locally, and the author restores it on a new laptop — with nothing more than `conda env create -f environment.yml` + `quarto render`. Do **not** rely on globally-installed tools or on running `quarto add` after cloning.

- **Commit `_extensions/`** — Quarto extensions are vendored, not regenerated. Never gitignore `_extensions/`, or a fresh clone fails to build. (This bit us: a stray `_extensions/` line in `.gitignore` had been keeping the lightbox and d2 extensions out of git.)
- **Declare every build-time tool in `environment.yml`** — e.g. the `d2` CLI (used by the quarto-d2 diagram filter) is a `conda-forge` dependency, not a global install.

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
- **[doc/engaging-lecture-design.md](doc/engaging-lecture-design.md)** — lecture design playbook (cold open, quiz-then-reveal, one-dataset-per-section). **Read before writing or restructuring any lecture.**
- **[doc/course-arc.md](doc/course-arc.md)** — the course-wide narrative arc and the spec for each not-yet-written lecture. Keep it updated when lectures are added or reordered.

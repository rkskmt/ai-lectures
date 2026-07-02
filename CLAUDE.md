# CLAUDE.md

## Project Overview

Quarto-based AI lecture website ("AI Lectures"). Slide decks for machine learning topics, written in Japanese.

## Tech Stack

- **Quarto** website project; slides use the vendored **cleanslidekit-revealjs** extension (theme.scss + custom.css + UI JS + Lua filters, in `_extensions/rkskmt/cleanslidekit/`)
- **Python 3** via Jupyter kernel for code cells
- **MathJax** for math rendering
- **D2** (quarto-d2) for diagrams
- Extensions: `cleanslidekit`, `d2`, `lightbox` (all vendored)

## Structure

- `_quarto.yml` — site config and resources
- `_metadata.yaml` — shared slide format settings (`cleanslidekit-revealjs` format + `d2`/`lightbox` filters)
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

- `##` delimits slides (do not use `---`)
- `_metadata.yaml` applies the `cleanslidekit-revealjs` format (+ `d2`/`lightbox` filters) to all `.qmd` files; theme, CSS, and UI JS ship from `_extensions/rkskmt/cleanslidekit/`
- **Do not add frontmatter to `index.qmd`.** Quarto **merges** (not overwrites) `format` from `_metadata.yaml` and the file, so adding `format: html` causes it to render in both formats and trigger a `rename` error. Raw HTML (e.g. `<details>/<summary>`) is fine — it needs no frontmatter.
- **Do not use `listing:` in `index.qmd` either.** Same reason — it requires `format: html`, which conflicts.
- `render: ["*.qmd"]` in `_quarto.yml` prevents `.md` files (e.g. CLAUDE.md) from being rendered
- **When adding a new `.qmd`, add it to `index.qmd`.** It is the site's only navigation: every page renders as revealjs slides, so the Quarto website navbar is never displayed — do not maintain a `navbar` in `_quarto.yml` (verified 2026-06: no navbar element appears in any built page).
- **`search-ui.js` provides site-wide full-text search**: a 検索 button + modal on every deck (shipped by the cleanslidekit extension) and the inline box on `index.qmd` (`#search-input`/`#search-results`). It reads Quarto's generated `search.json` and deep-links to slides via `#/slide-id` — no per-lecture maintenance.
- **Never add numbers to slide section headers or `index.qmd` link text.** Numbered slides (e.g. `## １. ...`) and numbered links (e.g. `第N回`) break on reorder — every insert or swap requires renaming every entry after it. Use plain titles only (e.g. `## 汎化性能を測る`, `[過学習と汎化](classification-evaluation.qmd)`).
- Use Quarto callouts (`.callout-note`) for key concepts
- Slide text should use **bullet points**, not prose sentences. **Exception: exercise/task statements.** A 演習 uses the exam-problem register — directive and concise beats polite filler, as long as it doesn't turn harsh:
   - **Problem statement**: one prose sentence in **命令形** (`…を自分のコードで確かめよ`, `…を実装せよ`). Name the concrete action (`CSVで読み込み`), not vague framing (`〜を使って`).
   - **Steps**: a numbered list in **体言止め** — drop trailing する/出す (`columns で列名を確認`, `平均を比較`). Setup (data download) is **step 0** so the whole list aligns.
   - **Required outputs are explicit**: state them in parentheses (`（差分値も表示）`) instead of leaving what to print implicit.
   - Do NOT cram instructions into bullets or arrow chains (`まず予想 → 何度ちがう？ → 自分で書く`), and don't spoon-feed what students can discover with a taught tool.
- **Every sentence on a slide must be written for the student — author-side circumstances are never slide content.** Litmus test: *does the student gain anything from reading this line?* Banned categories (each has been found and scrubbed in a real audit of the sibling IP3200 repo):
   - **Authoring/build decisions**: 「（この節だけでも実行できるよう、読み込みから用意）」「本スライドは `"directory"` を使っている — 教室のWi-Fiが切れても動くように」
   - **Curriculum decisions** — especially naming untaught material only to exclude it: 「`.plot.bar()` は今回は使わない」「だから3Dはこの回で扱った」
   - **Lecture-structure narration / pedagogical-effect claims**: 「今回は「◯◯」の回」「〜が体感できる」 "this builds intuition for △△"
   - Meta-information may stay only if reframed as a fact useful to the student: 「ここまで触ってきた動くグラフも、こうして保存したHTMLの埋め込み」 is fine; 「実は本スライドは以下のように埋め込んでいる」 is not.
   Teaching intent belongs in conversation, design notes, or `doc/` — never in the deck.
- **Never require untaught syntax.** Exercises (演習) must be solvable with only what earlier slides have introduced — a one-line preview in a callout is fine, quizzing on it is not. Related consistency checks: introduce a feature on its **first** use (not silently one slide early), and back-references must be literally true (「前ページのコード」 only if it *is* the previous page; otherwise 「さっきのコード」).
- Code cells use `jupyter: python3`
- **Assume students run Python in VSCode as normal `.py` scripts, not notebooks.** Code examples must be copy-pasteable into a Python file and still show the intended output.
- **Echoed executed cells (`echo: true`) must be self-contained** — include their own `import` and data loading. Quarto runs all cells in one kernel, so a cell missing an import renders fine but breaks for the student who copies just that cell. Hidden authoring cells (`echo: false`) may share kernel state freely.
- **`eval: false` cells (解答例) are never executed at render — run them manually before shipping** (including network-dependent solutions). Give every 演習 slide a `code-fold` 解答例.
- **Any data file a code cell reads must have a download link in the slide body.** Students run the copied code on their own machine, so a bare `pd.read_csv("data/foo.csv")` / `np.loadtxt("data/foo.csv")` fails unless they can obtain `foo.csv`. Put `[foo.csv](data/foo.csv)` in the slide text and tell them to place it in their `data/` folder. Never show runnable student code that reads a data file without a download link for that file. (Exception: hidden `echo: false` figure cells may read committed CSVs without a link — students use the live/download code shown in the `code-fold` block instead.)
- **Never fabricate figure data.** A chart presented as the result of a dataset, API, or training run must be computed from that real data — no `np.linspace` + noise stand-ins. For network sources, fetch once, commit the CSV under `data/`, load it in a hidden cell, and show the real acquisition code in a `code-fold`. Interpretation bullets must describe features actually present in the data — verify every number/claim against the file before writing it.
- **Do not use notebook-only display style** such as a bare `df`, `df.head()`, `df.shape`, `series`, or expression as the final line when the goal is to show output. Use `print(...)` for textual/tabular output (e.g. `print(df.head())`, `print(df.shape)`). Use plotting calls like `plt.show()` when the goal is a figure.
- For large tables or arrays, show only a small, intentional preview such as `print(df.head())`; do not dump all rows unless the full output is pedagogically necessary (a 20-row dump pushes captions/callouts below the fold).
- **One slide = one idea.** If bullets + code + output + note don't fit the 720px slide, split the slide at the conceptual seam rather than shrinking the content. Some scroll on code+figure slides is idiomatic in this course; a caption or callout stranded far below the fold is not.
- **String literals in student-visible code use double quotes** (`"数学I"`, `{"User-Agent": "..."}`). Inside f-string braces keep single quotes for Python <3.12 compatibility (`f"{d['title']}"`); genuine Python repr output shows singles — leave real output as-is.
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

When changing CSS, theme, JavaScript, or `_metadata.yaml`: read **[doc/troubleshooting.md](doc/troubleshooting.md)** first. It covers which `custom.css` copy to edit (the extension one — the root copy is overwritten on render), the Pandoc vs reveal CSS layers, and cache-clearing steps.

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

- **[doc/troubleshooting.md](doc/troubleshooting.md)** — CSS/style changes: which custom.css to edit, Pandoc vs reveal layers, cache issues
- **[doc/engaging-lecture-design.md](doc/engaging-lecture-design.md)** — lecture design playbook (cold open, quiz-then-reveal, one-dataset-per-section). **Read before writing or restructuring any lecture.**
- **[doc/course-arc.md](doc/course-arc.md)** — the course-wide narrative arc and the spec for each not-yet-written lecture. Keep it updated when lectures are added or reordered.

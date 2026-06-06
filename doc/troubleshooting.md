# Troubleshooting

## CSS changes and stale preview

Changes to `_metadata.yaml` or embedded CSS/JavaScript may not appear in an
already-running `quarto preview`.

Clear both Quarto output/cache directories and restart preview:

```bash
rm -rf _site .quarto && quarto preview --port 4321
```

## CSS in `_metadata.yaml` — Pandoc vs revealjs

CSS in `_metadata.yaml` `include-in-header` affects two different layers:

- Pandoc-generated code block HTML and line-number styles
- revealjs/clean-revealjs slide layout and typography

For Pandoc-generated code blocks, prefer bare selectors with `!important`.
These are the important selectors:

| What | Selector |
|---|---|
| Line number counter | `pre.numberSource code > span > a:first-child::before` |
| Span positioning for line numbers | `pre.numberSource code > span` |
| Pre margin/padding for line numbers | `pre.numberSource` |
| Language class on pre | `pre.shell`, `pre.python`, etc. |
| Syntax highlight spans | `code span.kw`, `code span.im`, etc. |

When a CSS change does not appear, assume stale cache first and restart preview
with the cache-clearing command above.

# Quarto スライド 画像・引用 記法

両プロジェクト（`IP3200/`、`ai/`）共通の記法。

## セットアップ

各プロジェクトの `_metadata.yaml` に CSS と Lua フィルター（`cite-image.lua`）が設定済み。

---

## 1. 部分画像 + 引用オーバーレイ

```markdown
::: {.fig-cite src="imgs/image.png" height="400px"}

::: {.cite}
出典: <https://example.com>
:::
:::
```

- `src` — 画像パス（`imgs/` 相対）
- `height` — div の高さ（省略時 `60%`）
- 画像は `background-size: contain` で縦横比を保って収まる
- `.cite` が右下にオーバーレイ表示される

---

## 2. 全画面スライド + 引用オーバーレイ

```markdown
## {.bg-cover src="imgs/image.png"}

::: {.cite}
出典: <https://example.com>
:::
```

- スライドの `<section>` 要素を背景画像で塗りつぶす（レターボックス外には影響しない）
- `background-size: cover` で全面を埋める
- スライドタイトル（h2）は自動的に非表示になる（`.no-header` が付与される）

---

## 3. `.cite` 単体

`position: absolute` なので、`position: relative` な親要素の右下に表示される。

- `.fig-cite` の中 → 画像右下
- `.bg-cover` スライド直下 → スライド右下
- 他の `position: relative` な要素の中でも使える

---

## 4. その他の CSS クラス

| クラス | 効果 |
|---|---|
| `.fig-small` | 画像の最大高さを 300px に制限 |
| `.fig-medium` | 画像の最大高さを 400px に制限 |
| `.no-header` | スライドの h2 を非表示 |

---

## ファイル構成

```
プロジェクト/
├── cite-image.lua      # Lua フィルター（.fig-cite / .bg-cover → style 展開）
├── _metadata.yaml      # CSS 定義 + フィルター登録
├── _quarto.yml         # resources: ["imgs/**"] でimgsを_siteへコピー
└── imgs/               # 画像置き場
```

> **注意**: CSS background-image に使う画像は `<img>` タグ経由でないと Quarto が自動コピーしない。
> `_quarto.yml` の `resources: ["imgs/**"]` で全画像をコピーするよう設定済み。

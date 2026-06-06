# AI Lectures

機械学習・AIに関するQuartoスライド。

## セットアップ

### 必要なもの

- [Quarto](https://quarto.org/docs/get-started/) (>= 1.8)
- conda (Miniconda / Anaconda)

### ワンコマンドセットアップ

```bash
python setup.py
conda activate ai
```

`setup.py` が以下をまとめて行う：
- `environment.yml` に基づく conda 環境 `ai` の作成・更新
- `QUARTO_PYTHON` 自動設定の activate フック
- MathJax 2 のダウンロード（`libs/mathjax/`）

MathJax だけ再取得したい場合：

```bash
python setup.py --mathjax-only
```

### ローカルプレビュー

```bash
quarto preview --port 4321
```

ブラウザで `http://localhost:4321` が開く。ファイルを保存するとホットリロードされる。

### ビルド・デプロイ

```bash
quarto render            # _site/ に出力
quarto publish gh-pages  # GitHub Pages へデプロイ
```

## ファイル構成

```
_quarto.yml       サイト設定・ナビゲーション
_metadata.yaml    スライド共通設定（テーマ・CSS・フィルタ）
environment.yml   conda 環境定義
index.qmd         トップページ（リンク一覧）
*.qmd             各回のスライド
imgs/             画像ファイル
hl.lua            ==text== ハイライト用 Lua フィルタ
fw-colon.lua      全角コロン「：」の表示調整 Lua フィルタ
cite-image.lua    画像引用表示用 Lua フィルタ
doc/              執筆ガイド・トラブルシュート
_extensions/      Quarto 拡張（clean-revealjs テーマ等）
```

## スライドの書き方

### 基本ルール

- スライド区切りは `##`（`---` は使わない）
- 本文はバレットポイントで書く（地の文は避ける）
- 重要概念は Quarto callout（`.callout-note`, `.callout-tip`, `.callout-warning`）を使う

### 新しいスライドを追加する

1. `xxx.qmd` を作成
2. `index.qmd` にリンクを追加
3. `_quarto.yml` の `navbar` にも追加

3つ揃えないとナビゲーションがずれるので注意。

### インラインコード（バッククォート）

本文中の `` `code` `` は **太字・青（`#005cc5`）・等幅** で表示される。  
コードブロックのシンタックスハイライトと同系色。

```markdown
NumPy では `@` が内積の演算子
```

### ハイライトマーカー（`==text==`）

`hl.lua` フィルタにより、`==text==` と書くと縁取り付きのハイライト表示になる。  
バッククォートのインラインコードとは別のスタイル（白文字＋シアン縁取り）。

```markdown
NumPy では ==@== が内積の演算子
```

**制約:**

- 中身に空白は含められない（`==` と `==` の間に空白があるとマッチしない）
- スペースを含む場合は `[a @ b]{.hl}` と書く

### Matplotlib で日本語

```python
import japanize_matplotlib  # これだけでOK
```

`rcParams['font.family']` は使わない（動作が不安定）。

### 数式の `\vec{}` の高さ揃え

`\vec{a}` と `\vec{b}` で矢印の高さが揃わない問題の対処：

```latex
\vec{\vphantom{b}a}   ← b と高さが揃う
```

## 画像・引用記法

### 部分画像 + 引用オーバーレイ

```markdown
::: {.fig-cite src="imgs/image.png" height="400px"}

::: {.cite}
出典: <https://example.com>
:::

:::
```

### 全画面スライド + 引用オーバーレイ

```markdown
## スライドタイトル {.bg-cover src="imgs/image.png"}

::: {.cite}
出典: <https://example.com>
:::
```

### コンテンツボックス

```markdown
::: {.content-box}
内容
:::

::: {.content-box .pos-br}
右下に配置
:::

::: {.content-box .pos-cl}
中央・左寄せ
:::
```

### その他の CSS クラス

| クラス | 効果 |
|---|---|
| `.fig-small` | 画像の最大高さを 300px に制限 |
| `.fig-medium` | 画像の最大高さを 400px に制限 |
| `.no-header` | スライドの h2 を非表示 |
| `.fig-fullscreen` | 画像を全画面表示 |

## 参考ドキュメント

- [doc/troubleshooting.md](doc/troubleshooting.md) — CSS変更時のキャッシュ・コードブロック selector の注意

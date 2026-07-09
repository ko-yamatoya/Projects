# Projects リポジトリの運用ルール

公開リポジトリ。「プロンプト一本でこんなのが作れる」を人に見せるためのデモ置き場。

- **1デモ = 1サブフォルダ**（例: `places-map/`、`organoid-lab-website/`）。
  独立リポジトリは作らない（明示的な指示がある場合のみ例外）。
- 各デモは `index.html` を入り口にし、GitHub Pages で
  `https://ko-yamatoya.github.io/Projects/<フォルダ名>/` として公開される。
  外部CDN依存を避け、単一HTMLで自己完結させると出先でも壊れない。
- 新しいデモを作ったら README.md の一覧に1行追加する。
- 公開リポジトリなので個人情報・APIキー・内輪ネタは置かない。
- git add は対象パス限定（`git add -A` 禁止）。

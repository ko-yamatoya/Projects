# solo-trip — 経県ゲーム / 一人旅ダッシュボード

行った県を経県値で塗り分けた日本地図＋一人旅プランの公開ページ。
飲みの場で「未踏の県を潰していくゲーム」として見せる用。

**公開URL**: https://ko-yamatoya.github.io/Projects/solo-trip/

## できること
- 経県値（居住/宿泊/訪問/接地/通過/未踏）で塗った日本地図。県タップで状態とアクセスを表示。
- スコア（経県値 107/235・未踏19・踏んだ28）とプログレスバー。
- **🎲 次どこ行く？** ボタン＝未踏県からランダムに1つ光らせる（盛り上がり用）。
- **未踏だけ光らせる** トグル。
- 提案済みの一人旅プランを、土地の雰囲気に沿ったアクセント色のカードで表示。
- ライト／ダーク両対応・スマホ最適化・外部CDN非依存の単一ページ（出先でも壊れない）。

## ファイル
| ファイル | 役割 |
|---|---|
| `index.html` | **生成物**。直接編集しない（`build.py` が作る） |
| `_template.html` | ページの本体（CSS/JS）。デザイン変更はここ |
| `japan.svg` | 日本地図SVG（geolonia/japanese-prefectures, MIT） |
| `build.py` | `_template.html` に `japan.svg` を差し込んで `index.html` を生成 |
| `data.js` | **経県値データ**。正本は Life リポジトリ `travel/solo/keikenchi.md`。あちらを更新したらここも同期 |
| `plans.js` | **プランの継ぎ目**。solo-trip スキルが提案のたびに1件追記する |

## 更新のしかた
- **経県値が変わった**（旅から帰った）→ `data.js` の該当県 score と `total/mikkou` を直す。build 不要（`index.html` が `data.js` を読むだけ）。
- **プランを追加**→ `plans.js` の `SOLO_PLANS` に1件 push。build 不要。
- **地図やデザインを変えた**→ `_template.html` を編集して `python3 build.py`。

いずれも `git add` は対象パス限定でコミット＆push すれば GitHub Pages に反映される。

> データ源の正本は Life リポジトリ側（`travel/solo/keikenchi.md`・`travel/solo/plans/`）。
> このページはそれを見せるための鏡なので、正本を変えたらここへ手で同期する運用。

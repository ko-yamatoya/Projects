# yaritai-list — やりたいことリスト

やりたいことを書き留めて、**お金との関係（お金を出してでも / そこまでは出さない / お金はかからない）**で仕分けして、
達成を記録する。単一の `index.html`（ビルド不要・外部CDNなし）。データはブラウザの IndexedDB。

**公開URL: <https://ko-yamatoya.github.io/Projects/yaritai-list/>**

> データはこのリポジトリには入らない。ブラウザの中にだけ持ち、JSONで書き出し／取り込みする。

## できること

| | |
|---|---|
| クイック追加 | タイトルだけ書いて Enter。詳しいことは後から |
| 一覧 | お金の区分とカテゴリをチップ表示（未設定も識別できる）。検索・絞り込み（カテゴリは複数選択）・並べ替え・グルーピング |
| 達成チェック | 丸をタップ、または**右スワイプ**。達成日は自動、振り返りと満足度（1〜5）も残せる |
| 仕分けモード | お金の区分が未設定のものを1件ずつカード表示。3択をタップして1タップで次へ |
| 推移 | 月別の追加・達成、お金の区分とカテゴリの構成比の移り変わり。どのグラフにも「表で見る」つき |
| 分析 | 取り込んだ分析（Markdown）を新しい順に表示 |
| 達成タイムライン | 達成したものを月ごとに |
| 今日なにする？ | 未達成からランダムに1件 |
| 公開モード | メモ・金額・振り返りを隠す（スクショを人に見せるとき用） |
| 取り込み / 書き出し | JSONで往復。取り込みは件数をプレビューしてから確定 |
| PWA | ホーム画面に追加してオフラインでも動く。ライト／ダーク両対応 |

## キーボード

`n` 追加 ／ `/` 検索 ／ `r` 今日なにする？ ／ `l` `t` `c` `g` `d` 各ビュー ／
仕分け中の `1` `2` `3`（お金の区分）・`s` スキップ・`u` 戻す ／
`p` 公開モード ／ `⌘+Enter` 保存 ／ `Esc` 閉じる

URLで開き方を指定できる: `?theme=dark` `?pub=1` `?log=analyses` `#trend`

## データの形

```jsonc
{
  "schemaVersion": 1,
  "exportedAt": "ISO8601",
  "items": [{
    "id": "uuid", "title": "…", "category": "…", "memo": "",
    "money": "pay|hold|none|null",      // 出してでも / そこまでは出さない / かからない。null=未設定
    "wtp": "1k|10k|…|1m+|null",         // 旧データ。画面では使わないが消さずに持つ
    "when": "", "nextStep": "",
    "done": false, "doneAt": null, "reflection": "", "satisfaction": null,
    "source": "initial|app",
    "createdAt": "…", "updatedAt": "…", "deletedAt": null,
    "history": [{ "at": "…", "field": "money|category|done", "from": null, "to": "pay" }]
  }],
  "analyses": [{ "id": "…", "createdAt": "…", "periodFrom": "…", "periodTo": "…", "summary": "# Markdown" }]
}
```

### マージ規則

- `id` で突き合わせ、`updatedAt` が新しい方を採用
- `history` は両方を統合して重複排除
- `deletedAt` がある項目は復活させない（物理削除はしない）
- `analyses` は `id` で和集合

書き出したJSONをローカルの管理フォルダ側のスクリプトで同じ規則にマージすると、
アプリ ⇄ ローカル の往復ができる。両側で規則が一致していることが前提。

## 検証

`?selftest=1` を付けて開くと、スキーマ正規化・マージ規則・集計・描画・IndexedDB永続化・
仕分けUI・公開モードを本物のブラウザで通す（82項目）。結果はページ末尾と `document.title` に出る。
実行前に手元のデータを退避し、終了時に書き戻すので壊さない。

```bash
cd ..            # Projects/ 直下
python3 -m http.server 8765
open "http://localhost:8765/yaritai-list/?selftest=1"
```

## 中身

```
index.html            すべて（CSS/JSを同梱）
selftest.js           ?selftest=1 のときだけ読まれる検証スイート
manifest.webmanifest  PWA
sw.js                 オフライン（ナビゲーションはネット優先／静的資材はキャッシュ優先）
icon.svg / icon-*.png アイコン
```

グラフは自前SVG。配色はコントラスト・色覚多様性の数値検証を通したパレットを使い、
色だけに意味を持たせないよう凡例と「表で見る」を必ず添えている。
カテゴリの色は一覧のチップと構成比グラフで同じ割り当て（件数上位7つ＋その他は無彩色）。

# kanji-note — 幹事ノート

スポーツの集まり（バスケ・バレーなど）の幹事さん用アプリ。
**日付×種目ごと**に、出欠・ご飯の参加・メニュー番号の注文・参加費の集金・名札（ガムテープ）をまとめて管理する。
単一の `index.html`（ビルド不要・外部CDNなし）。デザインは iOS の標準アプリ風。

- **公開URL: <https://ko-yamatoya.github.io/Projects/kanji-note/>**
- **お試し表示（架空のデータ・保存されない）: <https://ko-yamatoya.github.io/Projects/kanji-note/?demo=1>**

> データはこのリポジトリにもサーバーにも入らない。使う人のスマホのブラウザ（IndexedDB）の中だけにある。

## できること

| 画面 | 内容 |
|---|---|
| 予定 | 一覧／カレンダー。種目でしぼる。これからの予定は出欠・ご飯・集金の数つき |
| 日程 › 参加者 | 「参加・未定・休み」を1タップ。未回答・定員オーバーがひと目でわかる。名前を押すと1人分をまとめて入力 |
| 日程 › ご飯 | 行く／行かない、ご飯だけ参加、メニュー番号で注文（電話アプリ風のキーパッド・いつもの注文）、本人確認のチェック、お店に送る文／電話で読み上げる画面／だれが何を頼んだか。お店に伝えたあとの変更を知らせる |
| 日程 › 集金 | 参加費（学生などの区分・個別の金額）、ご飯代（割り勘・一律・注文の値段）、受け取り方、支出（コート代など）と収支 |
| 日程 › 名札 | ガムテープに書く名前（ニックネーム）と「作った」チェック。まだの人の名前リスト |
| メンバー | まとめて貼り付けで登録、★固定メンバー（種目ごと）、名札の名前、料金区分、いつもの注文、参加回数・最後に来た日・未払い |
| お金 | 手元にあるはずのお金、まだもらっていないお金（受け取ったら1タップ）、月ごとの収支、その他のお金 |
| データ | 手伝いの人への受け渡し・受け取り・バックアップの**手順つき** |
| 設定 | 文字の大きさ（3段階）、画面の色、種目ごとのいつもの設定、お店とメニュー（貼り付けで登録） |

LINE用の文（募集・出欠まとめ・集金のお願い・お店への注文・名札リスト）は自動で作り、コピー／LINEで送る／共有。

## 手伝いの人との受け渡し（入力は1人、チェックは別の人）

1. 幹事: 日程の画面の「手伝いの人に渡す」→「LINEで送る」
2. 手伝う人: 届いたリンクを押すだけ（`?openExternalBrowser=1` でLINEの中ではなく普通のブラウザで開く）
3. 手伝う人: 集金・メニュー確認・名札などをチェック →「幹事に返す」→「LINEで送る」
4. 幹事: 届いたメッセージを長押し→コピー→「データ」→「貼り付けて受け取る」

- データは圧縮してリンクの `#p=…`（フラグメント）に入れる。フラグメントはサーバーに送られない
- 取り込みは**項目のまとまりごとに新しい方を残す**（出欠／ご飯／注文／料金／集金／ご飯代／名札／メモ／名簿から外す）。
  幹事が出欠を、手伝いが集金を同時に触っても、互いの入力を消さない。同じものを2回受け取っても変わらない
- メンバーの「メモ」（アレルギーなど）は渡さない。受け取った側のメモも上書きしない
- iPhone はホーム画面のアプリと Safari で保存場所が別。幹事はアプリの中の「貼り付けて受け取る」を使う（リンクを押すとSafariが開くため）

## バックアップ

「データ」→「バックアップを保存」で JSON ファイルを共有シート（ファイルに保存・LINEの自分用トークなど）へ。
戻すときは「バックアップから戻す」→「合わせる」または「置き換える」（機種変更）。
最後のバックアップから14日たつと、予定画面にお知らせが出る。

## データの形

```jsonc
// バックアップ（kind: backup）・受け渡し（kind: handoff / return）共通
{ "app": "kanji-note", "kind": "backup", "v": 1, "at": "ISO8601", "from": "幹事名",
  "sports":  [{ "id", "name", "emoji", "color", "start", "end", "place", "capacity",
               "tiers": [{ "id", "label", "amount" }], "dinner", "menu", "tape", "shopId", "dinnerTime",
               "expenses": [{ "id", "label", "amount" }], "seed": "pending|yes|off", "updatedAt", "deletedAt" }],
  "members": [{ "id", "name", "kana", "tape", "fixed": ["sportId"], "tier", "usual": [{ "no", "qty" }], "memo", "archived", "updatedAt", "deletedAt" }],
  "shops":   [{ "id", "name", "phone", "memo", "menu": [{ "no", "name", "price" }], "updatedAt", "deletedAt" }],
  "events":  [{ "id", "date", "sportId", "title", "start", "end", "place", "capacity", "tiers", "dinner", "menu", "tape",
               "shopId", "dinnerTime", "dinnerFee": { "mode": "none|split|fixed|menu", "total", "fixed", "round" },
               "expenses", "memo", "sent": { "at", "count", "tally": { "番号": 数 } }, "hdrAt", "updatedAt", "deletedAt",
               "entries": [{ "memberId", "status": "yes|maybe|no|''", "dinner": true|false|null,
                             "orders": [{ "no", "qty" }], "orderNote", "orderOk", "tierId", "feeOverride",
                             "paid", "paidAt", "payMethod", "dinnerPaid", "dinnerPaidAt", "tapeDone", "memo", "removed",
                             "ts": { "status|dinner|orders|fee|pay|dpay|tape|memo|removed": "ISO8601" } }] }],
  "extras":  [{ "id", "date", "kind": "in|out", "label", "amount" }],
  "settings": { "hostName", "payNote", "openingBalance", "lastBackupAt", "defaultPayMethod" } }
```

取り込むときは全項目を型・長さ・許可リストで検査してから使う（`norm*` 関数）。削除は `deletedAt` を付ける（元に戻せる）。

## 検証

`?selftest=1` で、検証専用の別DB（`kanji-note-selftest`）を使って 178 項目を本物のブラウザで通す
（文字の整え方・集計・LINE用の文・受け渡しのマージ・圧縮コード・保存・画面の操作・画面幅のはみ出し）。結果は `document.title` とページ末尾。

```bash
cd ..                      # Projects/ 直下
python3 -m http.server 8765
open "http://localhost:8765/kanji-note/?selftest=1"
# スマホ幅で確かめる（ヘッドレスChromeは窓の最小幅が500pxなので iframe で幅を固定する）
open "http://localhost:8765/kanji-note/tools/frame.html?w=360&h=800&q=selftest%3D1"
```

画面の確認用に `?demo=1&selftest=scene&scene=<名前>` で特定の画面を開いて止まる
（home / people / dinner / money / tape / person / numpad / shoptext / editor / members / moneyview / data / settings / handoff / import / cal / welcome / dark-people / xl-people）。

## 中身

```
index.html            すべて（CSS/JSを同梱）
selftest.js           ?selftest=… のときだけ読まれる検証スイート
tools/frame.html      スマホ幅のiframeでアプリを開く検証用ページ
manifest.webmanifest  PWA（ホーム画面に追加）
sw.js                 オフライン（ページはネット優先／アイコンはキャッシュ優先）
icon.svg / icon-*.png アイコン
```

## できないこと（いまの割り切り）

- リアルタイムの同期はしない（受け渡しはLINEでのメッセージのやりとり）。同期が必要になったら、
  受け渡しのパッケージ（`buildPkg` / `mergePkg`）をそのまま送受信する仕組みを足せば、マージ規則は流用できる
- LINEの送信ボタンはスマホのLINEアプリでのみ動く（PCのLINEは非対応）。そのときは「コピー」を使う

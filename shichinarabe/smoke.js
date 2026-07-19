/* DOMスタブでapp.jsを読み込み、1チーム戦をフル入力して例外なく回るか検証。
 * 実行: cd folder && jsc -e "load('smoke.js');" */

// ---- 最小DOMスタブ ----
var store = {};
localStorage = {
  getItem: function (k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
  setItem: function (k, v) { store[k] = v; }
};
window = globalThis;

function El() { this._html = ''; }
Object.defineProperty(El.prototype, 'innerHTML', {
  get: function () { return this._html; },
  set: function (v) { this._html = v; }
});
El.prototype.addEventListener = function () {};

var els = {};
var clickHandlers = [], changeHandlers = [];
document = {
  getElementById: function (id) { if (!els[id]) els[id] = new El(); return els[id]; },
  addEventListener: function (type, fn) {
    if (type === 'click') clickHandlers.push(fn);
    else if (type === 'change') changeHandlers.push(fn);
  },
  querySelectorAll: function () { return []; },
  createElement: function () { return { click: function () {}, href: '', download: '' }; }
};

// ---- 合成イベント ----
function target(attrs, value) {
  var t = {
    value: value,
    getAttribute: function (k) { return attrs[k] != null ? String(attrs[k]) : null; },
    closest: function (sel) {
      if (sel === '[data-action]') return t;
      // data-action="delete-round" 等の一致判定
      var m = sel.match(/\[data-action="([^"]+)"\]/);
      if (m) return attrs['data-action'] === m[1] ? t : null;
      return null;
    }
  };
  return t;
}
function fireClick(attrs) { var e = { target: target(attrs), stopPropagation: function () {} }; clickHandlers.forEach(function (h) { h(e); }); }
function fireChange(attrs, value) { var e = { target: target(attrs, value) }; changeHandlers.forEach(function (h) { h(e); }); }

// ---- 実行 ----
var fails = 0;
function assert(cond, label) { if (!cond) { print('✗ ' + label); fails++; } else { print('✓ ' + label); } }
function html() { return els['rounds'] ? els['rounds'].innerHTML : ''; }

// app.js は confirm を delete 系で使うのでスタブ
confirm = function () { return true; };
alert = function () {};

load('calc.js');
load('app.js'); // 末尾で初期 render() が走る

assert(html().indexOf('新しいチーム戦') >= 0, '初期レンダリングOK（空状態）');
assert((els['totals'].innerHTML || '').indexOf('総合ランキング') >= 0, '総合ランキング枠OK');

// チーム戦を1つ追加
fireClick({ 'data-action': 'add-round' });
assert(html().indexOf('チーム戦 1回目') >= 0, 'チーム戦追加OK');

// 追加された round の id を取り出す
var rid = (html().match(/data-round="(r\d+)"/) || [])[1];
assert(!!rid, 'round id 取得: ' + rid);

// 名簿デフォルト名
var P = [];
for (var i = 1; i <= 11; i++) P.push('プレイヤー' + i);

// チーム編成: ペア5 + ソロ1
// チーム0..4 = ペア(a,b), チーム5 = ソロ(a)
var teamPlan = [
  { ti: 0, a: P[0], b: P[1] }, { ti: 1, a: P[2], b: P[3] },
  { ti: 2, a: P[4], b: P[5] }, { ti: 3, a: P[6], b: P[7] },
  { ti: 4, a: P[8], b: P[9] }, { ti: 5, a: P[10] }
];
teamPlan.forEach(function (t) {
  fireChange({ 'data-action': 'set-team', 'data-round': rid, 'data-ti': t.ti, 'data-side': 'a' }, t.a);
  if (t.b != null) fireChange({ 'data-action': 'set-team', 'data-round': rid, 'data-ti': t.ti, 'data-side': 'b' }, t.b);
});
assert(html().indexOf('編成OK') >= 0, '編成バリデーション通過');

// A/B グループの順位入力（chipを上位から順にタップ）
var Aorder = [P[0], P[2], P[4], P[6], P[8], P[10]]; // 各ペアのa + ソロ
var Border = [P[1], P[3], P[5], P[7], P[9]];        // 各ペアのb
Aorder.forEach(function (n) { fireClick({ 'data-action': 'rank-add', 'data-round': rid, 'data-match': 'A', 'data-name': n }); });
Border.forEach(function (n) { fireClick({ 'data-action': 'rank-add', 'data-round': rid, 'data-match': 'B', 'data-name': n }); });

// winners = A top3 + B top3 / losers = A bottom3 + B bottom2
var winners = [P[0], P[2], P[4], P[1], P[3], P[5]];
var losers = [P[6], P[8], P[10], P[7], P[9]];
winners.forEach(function (n) { fireClick({ 'data-action': 'rank-add', 'data-round': rid, 'data-match': 'winners', 'data-name': n }); });
losers.forEach(function (n) { fireClick({ 'data-action': 'rank-add', 'data-round': rid, 'data-match': 'losers', 'data-name': n }); });

// winners 最下位(P[5]) をジョーカー1枚ドボンに
fireChange({ 'data-action': 'toggle-dobon', 'data-round': rid, 'data-match': 'winners', 'data-name': P[5] }, 'on');
// checkbox の change は checked を見る → target に checked を持たせる
(function () {
  var e = { target: { value: '', checked: true, getAttribute: function (k) { return ({ 'data-action': 'toggle-dobon', 'data-round': rid, 'data-match': 'winners', 'data-name': P[5] })[k] || null; }, closest: function () { return this.target || this; } } };
  e.target.closest = function () { return e.target; };
  changeHandlers.forEach(function (h) { h(e); });
})();
// ジョーカー枚数=1
fireChange({ 'data-action': 'set-joker', 'data-round': rid, 'data-match': 'winners', 'data-name': P[5] }, '1');

var out = html();
assert(out.indexOf('4/4 試合') >= 0, '4試合すべて完了ステータス');
assert(out.indexOf('このチーム戦の収支') >= 0, '収支テーブル描画');
assert(out.indexOf('NaN') < 0, '金額に NaN が出ていない');
assert(out.indexOf('💥') >= 0, 'ドボン明細が表示された');
assert((els['totals'].innerHTML || '').indexOf('NaN') < 0, '総合ランキングにも NaN なし');

// 人数減シナリオ: 追加チーム戦でチームを1つ削除し全ソロ化しても例外が出ないか
fireClick({ 'data-action': 'add-round' });
var rid2 = (html().match(new RegExp('data-round="(r\\d+)"[^]*チーム戦 2回目')) || [])[1] ||
  (function () { var m = html().match(/data-round="(r\d+)"/g) || []; return (m[m.length - 1] || '').replace(/[^r\d]/g, ''); })();
assert(!!rid2, '2つ目の round id 取得');

// 設定モーダル: 開く→賞金編集欄→既定に戻す→保存 が例外なく回るか
fireClick({ 'data-action': 'open-settings' });
assert((els['modal-root'].innerHTML || '').indexOf('Winners 賞金') >= 0, '設定に賞金編集欄あり');
assert((els['modal-root'].innerHTML || '').indexOf('data-set="w"') >= 0, 'winners単価が入力欄');
assert((els['modal-root'].innerHTML || '').indexOf('data-set="l"') >= 0, 'losers単価が入力欄');
fireClick({ 'data-action': 'reset-settings' });
fireClick({ 'data-action': 'save-settings' });
assert((els['modal-root'].innerHTML || '') === '', '設定保存でモーダルが閉じる');

print(fails === 0 ? '\nSMOKE PASS' : '\n' + fails + ' SMOKE FAIL');

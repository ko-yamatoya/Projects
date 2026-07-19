/* 計算ロジック検証。
 *   Node : node test.js
 *   jsc  : cd folder && jsc -e "load('calc.js'); load('test.js');"
 */
if (typeof console === 'undefined') {
  console = { log: function () { print(Array.prototype.join.call(arguments, ' ')); },
              error: function () { print(Array.prototype.join.call(arguments, ' ')); } };
}
var C = (typeof require === 'function') ? require('./calc.js') : SevensCalc;

var fails = 0;
function eq(actual, expected, label) {
  var a = Math.round(actual * 100) / 100;
  var e = Math.round(expected * 100) / 100;
  if (a !== e) { console.error('✗ ' + label + ' → 期待 ' + e + ' / 実際 ' + a); fails++; }
  else { console.log('✓ ' + label + ' = ' + a); }
}

// 5ペア + ソロ
var teams = [
  { members: ['A1', 'B1'] },
  { members: ['A2', 'B2'] },
  { members: ['A3', 'B3'] },
  { members: ['A4', 'B4'] },
  { members: ['A5', 'B5'] },
  { members: ['S'] }
];

var round = {
  teams: teams,
  matches: {
    // A: 1..6位。top3=A1,A2,A3 → winners / bottom3=A4,A5,S → losers。Sがパスドボン(最下位)
    A: { order: ['A1', 'A2', 'A3', 'A4', 'A5', 'S'], dobon: { S: 0 } },
    // B: 1..5位。top3=B1,B2,B3 / bottom2=B4,B5
    B: { order: ['B1', 'B2', 'B3', 'B4', 'B5'], dobon: {} },
    // winners(6): B3がパスドボン(最下位)
    winners: { order: ['A1', 'B1', 'A2', 'B2', 'A3', 'B3'], dobon: { B3: 0 } },
    // losers(5)
    losers: { order: ['A4', 'A5', 'S', 'B4', 'B5'], dobon: {} }
  }
};

var r = C.computeRound(round, C.defaultSettings());

// 折半前の順位賞金
eq(r.ranking.A1, 500, 'A1 順位賞金');
eq(r.ranking.B1, 400, 'B1 順位賞金');
eq(r.ranking.S, -300, 'S 順位賞金');
eq(r.ranking.B5, -500, 'B5 順位賞金');

// ペア折半後
eq(r.teamShare.A1, 450, 'ペア1 折半 (500+400)/2');
eq(r.teamShare.B1, 450, 'ペア1 折半 相方');
eq(r.teamShare.A3, 50, 'ペア3 折半 (100+0)/2');
eq(r.teamShare.A4, -250, 'ペア4 折半 (-100-400)/2');
eq(r.teamShare.A5, -350, 'ペア5 折半 (-200-500)/2');
eq(r.teamShare.S, -300, 'ソロ S はそのまま');

// ドボン: A試合でSがパスドボン→1位A1へ+200 / winnersでB3がパスドボン→1位A1へ+200
eq(r.dobon.A1, 400, 'A1 ドボン賞金 (200+200)');
eq(r.dobon.S, -200, 'S パスドボン支払い');
eq(r.dobon.B3, -200, 'B3 パスドボン支払い');

// ジョーカードボン: 基本200 + 1枚200。Zが2枚ドボン=200+200*2=600、1位Xが総取り
var jm = C.dobonMoneyForMatch(C.toResults({ order: ['X', 'Y', 'Z'], dobon: { Z: 2 } }), C.defaultSettings());
eq(jm.delta.Z, -600, 'ジョーカー2枚ドボン = -(200 + 200*2)');
eq(jm.delta.X, 600, '1位がジョーカードボン総取り (+600)');
eq(jm.pot, 600, 'ドボンpot = 600');
// 複数ドボン混在: パス(200) + ジョーカー1枚(400) = 600 を1位へ
var jm2 = C.dobonMoneyForMatch(C.toResults({ order: ['X', 'Y', 'Z'], dobon: { Y: 0, Z: 1 } }), C.defaultSettings());
eq(jm2.delta.Y, -200, 'Y パスドボン -200');
eq(jm2.delta.Z, -400, 'Z ジョーカー1枚 -400');
eq(jm2.delta.X, 600, 'X 総取り +600');

// 合計
eq(r.total.A1, 850, 'A1 合計 (450+400)');
eq(r.total.S, -500, 'S 合計 (-300-200)');
eq(r.total.B3, -150, 'B3 合計 (50-200)');

// ゼロサム検証（全員合計は0になるはず）
var sum = r.names.reduce(function (acc, n) { return acc + r.total[n]; }, 0);
eq(sum, 0, 'チーム戦の全員合計はゼロサム');

// 進出メンバー
var prog = C.computeProgression(round.matches.A, round.matches.B);
eq(prog.winners.length, 6, 'winners 6人');
eq(prog.losers.length, 5, 'losers 5人');
console.log('winners =', prog.winners.join(','));
console.log('losers  =', prog.losers.join(','));

// --- 人数が減ったとき（両端固定の検証） ---
var s = C.defaultSettings();
// winners は「トップから」。3人グループ → 500,400,300
eq(C.winnersPrizeForRank(1, s), 500, 'winners 1位 = 500（トップ固定）');
eq(C.winnersPrizeForRank(3, s), 300, 'winners 3位 = 300');
// losers は「ボトムから」。3人グループ → 上から -300,-400,-500（ボトム-500固定）
eq(C.losersPrizeForRank(1, 3, s), -300, 'losers(3人) 1位 = -300');
eq(C.losersPrizeForRank(2, 3, s), -400, 'losers(3人) 2位 = -400');
eq(C.losersPrizeForRank(3, 3, s), -500, 'losers(3人) 最下位 = -500（ボトム固定）');
// 5人グループなら従来通り
eq(C.losersPrizeForRank(1, 5, s), -100, 'losers(5人) 1位 = -100');
eq(C.losersPrizeForRank(5, 5, s), -500, 'losers(5人) 5位 = -500');

// 進出カットの可変（Aから2人・Bから1人がwinners）
var prog2 = C.computeProgression(
  { order: ['a1', 'a2', 'a3', 'a4'] },
  { order: ['b1', 'b2', 'b3'] }, 2, 1);
eq(prog2.winners.length, 3, 'cut指定 winners=3 (2+1)');
eq(prog2.losers.length, 4, 'cut指定 losers=4 (2+2)');

console.log(fails === 0 ? '\nALL PASS' : '\n' + fails + ' FAIL');
if (typeof process !== 'undefined' && process.exit) process.exit(fails === 0 ? 0 : 1);

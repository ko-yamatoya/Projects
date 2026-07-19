/*
 * 七並べ対決 記録アプリ — 収支計算ロジック（正本）
 * ブラウザ（index.html）と Node のテスト（test.js）で共有する純関数群。
 *
 * ルール要約:
 *  - 1チーム戦 = 4試合（A / B / winners / losers）
 *  - A(6人) の top3 と B(5人) の top3 が winners(6人)
 *  - A の bottom3 と B の bottom2 が losers(5人)
 *  - 順位賞金は winners / losers 試合でのみ発生
 *      winners: 1位→6位 = winnersPrizes[0..5]（既定 500,400,300,200,100,0）
 *      losers : 1位→5位 = losersPrizes[0..4]（既定 -100,-200,-300,-400,-500）
 *  - ペア（2人）は「順位賞金の合計を折半」。ソロ(1人)は自分の賞金そのまま。
 *  - ドボン: ペア無関係の個人清算。ドボンした人は各自 -dobonPenalty（既定200）を払い、
 *            その試合の1位が全額もらう。全4試合で発生しうる。
 *  - ドボン複数のときの順位（先にドボン=最下位）は入力側で順序に反映させる想定。
 */
(function (global) {
  'use strict';

  var CONFIG = {
    pairsCount: 5,          // ペア数
    sizes: { A: 6, B: 5, winners: 6, losers: 5 },
    matchKeys: ['A', 'B', 'winners', 'losers']
  };

  function defaultSettings() {
    return {
      // 固定（UIからは編集しない）
      winnersPrizes: [500, 400, 300, 200, 100, 0], // 1位..6位
      losersPrizes: [-100, -200, -300, -400, -500], // 1位..5位（ボトムほど大きなマイナス）
      // ドボン: 基本額 + ジョーカー1枚あたり加算
      dobonBase: 200,
      dobonPerJoker: 200
    };
  }

  // match = { order: [name, ...], dobon: { name: jokerCount } }  → [{name, rank, dobon, jokers}]
  //   dobon はキーの有無でドボン判定（値0=パスドボン, 値n=ジョーカーn枚ドボン）
  function toResults(match) {
    if (!match || !Array.isArray(match.order)) return [];
    var d = match.dobon || {};
    return match.order.map(function (name, i) {
      var isDobon = Object.prototype.hasOwnProperty.call(d, name);
      return { name: name, rank: i + 1, dobon: isDobon, jokers: isDobon ? (d[name] || 0) : 0 };
    });
  }

  function dobonPenaltyFor(jokers, settings) {
    return settings.dobonBase + settings.dobonPerJoker * (jokers || 0);
  }

  // 順位ごとの賞金。人数が減っても「トップ+500」「ボトム-500」を両端で固定する。
  function winnersPrizeForRank(rank, settings) {
    var arr = settings.winnersPrizes;
    return arr[rank - 1] != null ? arr[rank - 1] : 0; // トップ基準。溢れたら0
  }
  function losersPrizeForRank(rank, groupSize, settings) {
    var arr = settings.losersPrizes;
    var idx = arr.length - groupSize + (rank - 1); // ボトム基準に揃える
    if (idx < 0) idx = 0;
    if (idx > arr.length - 1) idx = arr.length - 1;
    return arr[idx];
  }

  // A/B の順位から winners / losers の顔ぶれを決める。
  //   cutA … A上位何人がwinnersへ / cutB … B上位何人がwinnersへ（既定 3・3）
  function computeProgression(aMatch, bMatch, cutA, cutB) {
    var a = ((aMatch && aMatch.order) || []).filter(Boolean);
    var b = ((bMatch && bMatch.order) || []).filter(Boolean);
    if (cutA == null) cutA = 3;
    if (cutB == null) cutB = 3;
    return {
      winners: a.slice(0, cutA).concat(b.slice(0, cutB)),
      losers: a.slice(cutA).concat(b.slice(cutB))
    };
  }

  // 1試合分のドボン清算
  function dobonMoneyForMatch(results, settings) {
    var delta = {};
    results.forEach(function (r) { delta[r.name] = 0; });
    var dobonners = results.filter(function (r) { return r.dobon; });
    if (!dobonners.length) {
      return { delta: delta, pot: 0, winner: null, dobonners: [] };
    }
    var pot = 0;
    var detail = dobonners.map(function (r) {
      var pen = dobonPenaltyFor(r.jokers, settings);
      delta[r.name] -= pen;
      pot += pen;
      return { name: r.name, jokers: r.jokers, penalty: pen };
    });
    var first = results.slice().sort(function (x, y) { return x.rank - y.rank; })[0];
    if (first) delta[first.name] = (delta[first.name] || 0) + pot;
    return { delta: delta, pot: pot, winner: first ? first.name : null, dobonners: detail };
  }

  /*
   * round = {
   *   teams: [{ members: [name,...] }, ...],   // 5ペア + 1ソロ
   *   matches: { A, B, winners, losers }        // それぞれ {order, dobon}
   * }
   * 戻り値: { names, ranking, teamShare, dobon, dobonDetail, total }
   *   ranking   … 折半前の順位賞金（個人）
   *   teamShare … ペア折半後の順位賞金
   *   dobon     … ドボン純額（個人）
   *   total     … teamShare + dobon
   */
  function computeRound(round, settings) {
    var s = settings || defaultSettings();
    var teams = round.teams || [];
    var names = [];
    teams.forEach(function (t) {
      (t.members || []).forEach(function (n) {
        if (n && names.indexOf(n) < 0) names.push(n);
      });
    });
    var zero = function () { var o = {}; names.forEach(function (n) { o[n] = 0; }); return o; };
    var matches = round.matches || {};

    // 1. 順位賞金（winners / losers のみ）
    var ranking = zero();
    var wRes = toResults(matches.winners);
    wRes.forEach(function (r) {
      if (ranking[r.name] != null) ranking[r.name] += winnersPrizeForRank(r.rank, s);
    });
    var lRes = toResults(matches.losers);
    lRes.forEach(function (r) {
      if (ranking[r.name] != null) ranking[r.name] += losersPrizeForRank(r.rank, lRes.length, s);
    });

    // 2. ペア折半
    var teamShare = zero();
    teams.forEach(function (t) {
      var mem = (t.members || []).filter(Boolean);
      if (!mem.length) return;
      var total = mem.reduce(function (sum, n) { return sum + (ranking[n] || 0); }, 0);
      var share = total / mem.length;
      mem.forEach(function (n) { teamShare[n] = share; });
    });

    // 3. ドボン（全4試合・個人清算）
    var dobon = zero();
    var dobonDetail = {};
    CONFIG.matchKeys.forEach(function (key) {
      var info = dobonMoneyForMatch(toResults(matches[key]), s);
      dobonDetail[key] = info;
      Object.keys(info.delta).forEach(function (n) {
        if (dobon[n] == null) dobon[n] = 0;
        dobon[n] += info.delta[n];
      });
    });

    // 4. 合計
    var total = zero();
    names.forEach(function (n) { total[n] = (teamShare[n] || 0) + (dobon[n] || 0); });

    return {
      names: names,
      ranking: ranking,
      teamShare: teamShare,
      dobon: dobon,
      dobonDetail: dobonDetail,
      total: total
    };
  }

  var api = {
    CONFIG: CONFIG,
    defaultSettings: defaultSettings,
    toResults: toResults,
    computeProgression: computeProgression,
    winnersPrizeForRank: winnersPrizeForRank,
    losersPrizeForRank: losersPrizeForRank,
    dobonPenaltyFor: dobonPenaltyFor,
    dobonMoneyForMatch: dobonMoneyForMatch,
    computeRound: computeRound
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  global.SevensCalc = api;
})(typeof window !== 'undefined' ? window : globalThis);

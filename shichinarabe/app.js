/* 七並べ対決 記録アプリ — UI / 状態管理 */
(function () {
  'use strict';

  var CALC = window.SevensCalc;
  var STORAGE_KEY = 'sevens_state_v3';
  var MATCH_LABELS = { A: 'A グループ', B: 'B グループ', winners: 'Winners', losers: 'Losers' };
  var MATCH_ORDER = ['A', 'B', 'winners', 'losers'];

  // ---- 状態 ---------------------------------------------------------------
  var state = load();

  function defaultRoster() {
    var a = [];
    for (var i = 1; i <= 11; i++) a.push('プレイヤー' + i);
    return a;
  }

  function defaultState() {
    return {
      settings: CALC.defaultSettings(),
      roster: defaultRoster(),
      rounds: [],
      ui: { openRoundId: null, tab: {} }
    };
  }

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultState();
      var s = JSON.parse(raw);
      s.settings = Object.assign(CALC.defaultSettings(), s.settings || {});
      if (!Array.isArray(s.roster) || s.roster.length !== 11) s.roster = defaultRoster();
      s.rounds = (s.rounds || []).map(migrateRound);
      s.ui = s.ui || { openRoundId: null, tab: {} };
      s.ui.tab = s.ui.tab || {};
      return s;
    } catch (e) {
      return defaultState();
    }
  }

  // 旧形式(pairs/solo)を新形式(teams配列)へ
  function migrateRound(r) {
    if (!r.teams) {
      var teams = (r.pairs || []).map(function (p) { return { type: 'pair', a: p.a, b: p.b }; });
      if (r.solo != null) teams.push({ type: 'solo', a: r.solo, b: '' });
      r.teams = teams;
      delete r.pairs; delete r.solo;
    }
    if (r.cutA == null) r.cutA = 3;
    if (r.cutB == null) r.cutB = 3;
    return r;
  }

  function save() { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
  function uid() { return 'r' + Date.now() + Math.floor(Math.random() * 1000); }

  function newRound() {
    var teams = [];
    for (var i = 0; i < 5; i++) teams.push({ type: 'pair', a: '', b: '' });
    teams.push({ type: 'solo', a: '', b: '' });
    return {
      id: uid(),
      teams: teams,
      cutA: 3,
      cutB: 3,
      matches: {
        A: { order: [], dobon: {} },
        B: { order: [], dobon: {} },
        winners: { order: [], dobon: {} },
        losers: { order: [], dobon: {} }
      }
    };
  }

  // ---- 派生 ---------------------------------------------------------------
  function activeNames(round) {
    var arr = [];
    round.teams.forEach(function (t) {
      if (t.a) arr.push(t.a);
      if (t.type === 'pair' && t.b) arr.push(t.b);
    });
    return arr;
  }

  function teamValidity(round) {
    var arr = activeNames(round);
    // 空きスロット（選択待ち）を数える
    var blanks = 0;
    round.teams.forEach(function (t) {
      if (!t.a) blanks++;
      if (t.type === 'pair' && !t.b) blanks++;
    });
    var counts = {};
    arr.forEach(function (x) { counts[x] = (counts[x] || 0) + 1; });
    var dups = Object.keys(counts).filter(function (k) { return counts[k] > 1; });
    var g = groupParticipants(round);
    return {
      ok: blanks === 0 && dups.length === 0 && g.A.length >= 1 && g.B.length >= 0 && arr.length >= 2,
      blanks: blanks, dups: dups
    };
  }

  function teamsForCalc(round) {
    return round.teams.map(function (t) {
      return { members: t.type === 'pair' ? [t.a, t.b] : [t.a] };
    });
  }

  function groupParticipants(round) {
    var A = [], B = [];
    round.teams.forEach(function (t) {
      if (t.a) A.push(t.a);
      if (t.type === 'pair' && t.b) B.push(t.b);
    });
    return { A: A, B: B };
  }

  function effCut(round) {
    var g = groupParticipants(round);
    return {
      cutA: Math.max(0, Math.min(round.cutA == null ? 3 : round.cutA, g.A.length)),
      cutB: Math.max(0, Math.min(round.cutB == null ? 3 : round.cutB, g.B.length))
    };
  }

  function abReady(round) {
    return matchComplete(round, 'A') && matchComplete(round, 'B');
  }

  function expectedParticipants(round, key) {
    if (key === 'A' || key === 'B') return groupParticipants(round)[key];
    if (!abReady(round)) return [];
    var c = effCut(round);
    var prog = CALC.computeProgression(round.matches.A, round.matches.B, c.cutA, c.cutB);
    return key === 'winners' ? prog.winners : prog.losers;
  }

  function matchComplete(round, key) {
    var exp = (key === 'A' || key === 'B') ? groupParticipants(round)[key] : null;
    if (exp == null) {
      // winners/losers は A,B 完成が前提
      if (!abReady(round)) return false;
      exp = expectedParticipants(round, key);
    }
    if (!exp.length) return false;
    var m = round.matches[key];
    if (!m || m.order.length !== exp.length) return false;
    for (var i = 0; i < exp.length; i++) if (exp.indexOf(m.order[i]) < 0) return false;
    return true;
  }

  // 上流変更で不整合になった順位入力を掃除
  function sanitizeMatches(round) {
    MATCH_ORDER.forEach(function (key) {
      var exp = expectedParticipants(round, key);
      var m = round.matches[key];
      m.order = m.order.filter(function (n) { return exp.indexOf(n) >= 0; });
      var nd = {};
      Object.keys(m.dobon || {}).forEach(function (n) {
        if (m.order.indexOf(n) >= 0) nd[n] = m.dobon[n] || 0;
      });
      m.dobon = nd;
    });
  }

  function roundResult(round) {
    return CALC.computeRound({ teams: teamsForCalc(round), matches: round.matches }, state.settings);
  }

  function grandTotals() {
    var totals = {};
    state.roster.forEach(function (n) { totals[n] = 0; });
    state.rounds.forEach(function (round) {
      if (!teamValidity(round).ok) return;
      var r = roundResult(round);
      r.names.forEach(function (n) {
        if (totals[n] == null) totals[n] = 0;
        totals[n] += r.total[n];
      });
    });
    return totals;
  }

  // ---- 表示ヘルパー -------------------------------------------------------
  function fmtMoney(v) {
    if (v == null || isNaN(v)) return '—';
    var r = Math.round(v * 100) / 100;
    if (r === 0) return '±0';
    return (r > 0 ? '+' : '−') + Math.abs(r).toLocaleString('ja-JP');
  }
  function moneyClass(v) { return v > 0 ? 'pos' : (v < 0 ? 'neg' : 'zero'); }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // ---- レンダリング -------------------------------------------------------
  function render() { renderRounds(); renderTotals(); save(); }

  function selectHtml(current, attrs) {
    var opts = ['<option value="">—</option>'];
    state.roster.forEach(function (n) {
      opts.push('<option value="' + esc(n) + '"' + (n === current ? ' selected' : '') + '>' + esc(n) + '</option>');
    });
    return '<select ' + attrs + '>' + opts.join('') + '</select>';
  }

  function renderTeamSetup(round) {
    var v = teamValidity(round);
    var g = groupParticipants(round);
    var c = effCut(round);

    var rows = round.teams.map(function (t, i) {
      var isPair = t.type === 'pair';
      var seg = '<div class="seg">' +
        '<button class="seg-btn' + (isPair ? ' active' : '') + '" data-action="set-teamtype" data-round="' + round.id + '" data-ti="' + i + '" data-type="pair">ペア</button>' +
        '<button class="seg-btn' + (!isPair ? ' active' : '') + '" data-action="set-teamtype" data-round="' + round.id + '" data-ti="' + i + '" data-type="solo">ソロ</button>' +
        '</div>';
      var selA = '<div class="tsel"><span class="grp-tag grp-a">A</span>' +
        selectHtml(t.a, 'data-action="set-team" data-round="' + round.id + '" data-ti="' + i + '" data-side="a"') + '</div>';
      var selB = isPair
        ? '<div class="tsel"><span class="grp-tag grp-b">B</span>' +
        selectHtml(t.b, 'data-action="set-team" data-round="' + round.id + '" data-ti="' + i + '" data-side="b"') + '</div>'
        : '<div class="tsel muted">（1人チーム）</div>';
      return '<div class="team-row">' +
        '<div class="team-head"><span class="team-label">チーム' + (i + 1) + '</span>' + seg +
        (round.teams.length > 1 ? '<button class="del-btn small" data-action="del-team" data-round="' + round.id + '" data-ti="' + i + '" title="このチームを削除">✕</button>' : '') +
        '</div><div class="team-selects">' + selA + selB + '</div></div>';
    }).join('');

    var warn;
    if (!v.ok) {
      var msgs = [];
      if (v.blanks) msgs.push('未選択 ' + v.blanks + ' 箇所');
      if (v.dups.length) msgs.push('重複: ' + v.dups.map(esc).join('、'));
      warn = '<div class="warn">⚠ 割り当てを完成させてください（' + (msgs.join(' / ') || '人数不足') + '）</div>';
    } else {
      warn = '<div class="ok-note">✓ 編成OK（Aグループ ' + g.A.length + '人 / Bグループ ' + g.B.length + '人）</div>';
    }

    var winCount = c.cutA + c.cutB;
    var loseCount = (g.A.length - c.cutA) + (g.B.length - c.cutB);
    var cut = '<div class="cut-row">' +
      '<span>Winners進出：Aから上位</span>' +
      '<input type="number" min="0" max="' + g.A.length + '" value="' + c.cutA + '" data-action="set-cut" data-round="' + round.id + '" data-cut="A">' +
      '<span>人 ／ Bから上位</span>' +
      '<input type="number" min="0" max="' + g.B.length + '" value="' + c.cutB + '" data-action="set-cut" data-round="' + round.id + '" data-cut="B">' +
      '<span>人</span>' +
      '<span class="cut-sum">→ Winners ' + winCount + '人 / Losers ' + loseCount + '人</span>' +
      '</div>';

    return '<div class="block">' +
      '<h4>チーム編成</h4>' +
      '<p class="hint">各チームはペア/ソロを切替可。左(A)がAグループ、右(B)がBグループへ。ペアは順位賞金を折半します。</p>' +
      rows +
      '<div class="add-team"><button class="mini" data-action="add-team" data-round="' + round.id + '" data-type="pair">＋ペア</button>' +
      '<button class="mini" data-action="add-team" data-round="' + round.id + '" data-type="solo">＋ソロ</button></div>' +
      cut + warn + '</div>';
  }

  function renderMatchPanel(round, key) {
    var exp = expectedParticipants(round, key);
    var m = round.matches[key];

    if (!exp.length) {
      var need = (key === 'A' || key === 'B')
        ? 'チーム編成を完成させてください。'
        : 'A・B両グループの順位を最後まで入力すると、ここに進出メンバーが表示されます。';
      return '<div class="match-body empty">' + need + '</div>';
    }

    var ranked = m.order.slice();
    var pool = exp.filter(function (n) { return ranked.indexOf(n) < 0; });

    var rankedHtml = ranked.map(function (n, i) {
      var rank = i + 1;
      var prize = null;
      if (key === 'winners') prize = CALC.winnersPrizeForRank(rank, state.settings);
      else if (key === 'losers') prize = CALC.losersPrizeForRank(rank, exp.length, state.settings);
      var prizeTag = prize != null ? '<span class="prize ' + moneyClass(prize) + '">' + fmtMoney(prize) + '</span>' : '';

      var isDobon = m.dobon && Object.prototype.hasOwnProperty.call(m.dobon, n);
      var jokers = isDobon ? (m.dobon[n] || 0) : 0;
      var jokerSel = '', penTag = '';
      if (isDobon) {
        var opts = [0, 1, 2].map(function (j) {
          return '<option value="' + j + '"' + (j === jokers ? ' selected' : '') + '>🃏' + j + '</option>';
        }).join('');
        jokerSel = '<select class="joker-sel" data-action="set-joker" data-round="' + round.id +
          '" data-match="' + key + '" data-name="' + esc(n) + '" title="ジョーカー枚数">' + opts + '</select>';
        penTag = '<span class="prize neg">' + fmtMoney(-CALC.dobonPenaltyFor(jokers, state.settings)) + '</span>';
      }
      return '<li class="rank-row' + (isDobon ? ' is-dobon' : '') + '">' +
        '<span class="rank-no">' + rank + '</span>' +
        '<span class="rank-name">' + esc(n) + '</span>' + prizeTag +
        '<label class="dobon-check"><input type="checkbox" data-action="toggle-dobon" data-round="' + round.id +
        '" data-match="' + key + '" data-name="' + esc(n) + '"' + (isDobon ? ' checked' : '') + '> ドボン</label>' +
        jokerSel + penTag + '</li>';
    }).join('');

    var poolHtml = pool.map(function (n) {
      return '<button class="chip" data-action="rank-add" data-round="' + round.id +
        '" data-match="' + key + '" data-name="' + esc(n) + '">' + esc(n) + '</button>';
    }).join('');

    var controls = '<div class="match-controls">' +
      (ranked.length ? '<button class="mini" data-action="rank-undo" data-round="' + round.id + '" data-match="' + key + '">← 1つ戻す</button>' : '') +
      (ranked.length ? '<button class="mini" data-action="rank-reset" data-round="' + round.id + '" data-match="' + key + '">リセット</button>' : '') +
      '</div>';

    var poolBlock = pool.length
      ? '<div class="pool"><div class="pool-label">上位から順にタップ（' + (ranked.length + 1) + '位）</div>' + poolHtml + '</div>'
      : '<div class="pool done">✓ 全員の順位を入力しました</div>';

    return '<div class="match-body">' +
      (ranked.length ? '<ol class="rank-list">' + rankedHtml + '</ol>' : '') +
      poolBlock + controls + '</div>';
  }

  function renderRoundMoney(round) {
    if (!teamValidity(round).ok) {
      return '<div class="block"><h4>このチーム戦の収支</h4><p class="muted">チーム編成が未完成です。</p></div>';
    }
    var r = roundResult(round);
    var c = effCut(round);
    var prog = abReady(round)
      ? CALC.computeProgression(round.matches.A, round.matches.B, c.cutA, c.cutB)
      : { winners: [], losers: [] };

    function whereTag(n) {
      if (prog.winners.indexOf(n) >= 0) return '<span class="grp-tag grp-win">W</span>';
      if (prog.losers.indexOf(n) >= 0) return '<span class="grp-tag grp-lose">L</span>';
      return '';
    }

    var rows = r.names.map(function (n) { return { n: n, total: r.total[n] }; })
      .sort(function (a, b) { return b.total - a.total; })
      .map(function (o) {
        var n = o.n;
        return '<tr>' +
          '<td>' + esc(n) + ' ' + whereTag(n) + '</td>' +
          '<td class="num ' + moneyClass(r.ranking[n]) + '">' + fmtMoney(r.ranking[n]) + '</td>' +
          '<td class="num ' + moneyClass(r.teamShare[n]) + '">' + fmtMoney(r.teamShare[n]) + '</td>' +
          '<td class="num ' + moneyClass(r.dobon[n]) + '">' + fmtMoney(r.dobon[n]) + '</td>' +
          '<td class="num strong ' + moneyClass(r.total[n]) + '">' + fmtMoney(r.total[n]) + '</td>' +
          '</tr>';
      }).join('');

    var dobonNotes = [];
    MATCH_ORDER.forEach(function (key) {
      var d = r.dobonDetail[key];
      if (d && d.dobonners.length) {
        var who = d.dobonners.map(function (x) {
          return esc(x.name) + (x.jokers ? '(🃏' + x.jokers + ')' : '') + ' ' + fmtMoney(-x.penalty);
        }).join('、');
        dobonNotes.push('💥 ' + MATCH_LABELS[key] + '：' + who + ' → ' + esc(d.winner) + ' が ' + fmtMoney(d.pot) + ' 獲得');
      }
    });

    return '<div class="block money-block">' +
      '<h4>このチーム戦の収支</h4>' +
      '<div class="table-wrap"><table class="money-table">' +
      '<thead><tr><th>名前</th><th>順位賞金</th><th>折半後</th><th>ドボン</th><th>合計</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>' +
      (dobonNotes.length ? '<div class="dobon-notes">' + dobonNotes.map(function (x) { return '<div>' + x + '</div>'; }).join('') + '</div>' : '') +
      '</div>';
  }

  function renderRound(round, index) {
    var open = state.ui.openRoundId === round.id;
    var tab = state.ui.tab[round.id] || 'A';
    var v = teamValidity(round);

    var tabsBtns = MATCH_ORDER.map(function (key) {
      var done = matchComplete(round, key);
      return '<button class="tab' + (tab === key ? ' active' : '') + ' tab-' + key + '" ' +
        'data-action="match-tab" data-round="' + round.id + '" data-match="' + key + '">' +
        MATCH_LABELS[key] + (done ? ' ✓' : '') + '</button>';
    }).join('');

    var body = open ? (
      renderTeamSetup(round) +
      '<div class="block"><h4>試合の順位・ドボン入力</h4>' +
      '<div class="tabs">' + tabsBtns + '</div>' + renderMatchPanel(round, tab) + '</div>' +
      renderRoundMoney(round)
    ) : '';

    var doneCount = MATCH_ORDER.filter(function (k) { return matchComplete(round, k); }).length;
    var statusChip = v.ok
      ? '<span class="status-chip">' + doneCount + '/4 試合</span>'
      : '<span class="status-chip warn-chip">編成未完</span>';

    return '<div class="round-card' + (open ? ' open' : '') + '">' +
      '<div class="round-head" data-action="toggle-round" data-round="' + round.id + '">' +
      '<div class="round-title">チーム戦 ' + (index + 1) + '回目</div>' + statusChip +
      '<button class="del-btn" data-action="delete-round" data-round="' + round.id + '" title="削除">✕</button>' +
      '<span class="chevron">' + (open ? '▲' : '▼') + '</span></div>' + body + '</div>';
  }

  function renderRounds() {
    var el = document.getElementById('rounds');
    var cards = state.rounds.map(renderRound).join('');
    el.innerHTML =
      '<div class="section-head"><h2>対戦記録</h2>' +
      '<button class="primary" data-action="add-round">＋ 新しいチーム戦</button></div>' +
      (state.rounds.length ? cards : '<div class="empty-note">まだ記録がありません。「＋ 新しいチーム戦」から始めましょう。</div>');
  }

  function renderTotals() {
    var el = document.getElementById('totals');
    var totals = grandTotals();
    var rows = state.roster.map(function (n) { return { n: n, v: totals[n] || 0 }; })
      .sort(function (a, b) { return b.v - a.v; });
    var sum = rows.reduce(function (acc, o) { return acc + o.v; }, 0);

    var body = rows.map(function (o, i) {
      var medal = i === 0 ? '🥇' : (i === 1 ? '🥈' : (i === 2 ? '🥉' : (i + 1) + ''));
      return '<tr>' +
        '<td class="rank-cell">' + medal + '</td><td>' + esc(o.n) + '</td>' +
        '<td class="num strong ' + moneyClass(o.v) + '">' + fmtMoney(o.v) + '<span class="yen">円</span></td></tr>';
    }).join('');

    el.innerHTML =
      '<div class="section-head"><h2>総合ランキング（全チーム戦 合計）</h2></div>' +
      '<div class="table-wrap"><table class="total-table"><tbody>' + body + '</tbody></table></div>' +
      '<div class="sum-note">全員の合計（参考）: ' + fmtMoney(sum) + '</div>';
  }

  // ---- モーダル -----------------------------------------------------------
  function openModal(html) {
    document.getElementById('modal-root').innerHTML =
      '<div class="modal-backdrop" data-action="close-modal"></div><div class="modal">' + html + '</div>';
  }
  function closeModal() { document.getElementById('modal-root').innerHTML = ''; }

  function renderSettingsModal() {
    var s = state.settings;
    var wref = s.winnersPrizes.map(function (v, i) { return '<span class="ref-chip">' + (i + 1) + '位 ' + fmtMoney(v) + '</span>'; }).join('');
    var lref = s.losersPrizes.map(function (v, i) { return '<span class="ref-chip">' + (i + 1) + '位 ' + fmtMoney(v) + '</span>'; }).join('');
    openModal(
      '<div class="modal-head"><h3>設定</h3><button class="del-btn" data-action="close-modal">✕</button></div>' +
      '<div class="modal-body">' +
      '<h4>Winners 賞金（固定・トップ基準）</h4><div class="ref-row">' + wref + '</div>' +
      '<h4>Losers 賞金（固定・ボトム基準）</h4><div class="ref-row">' + lref + '</div>' +
      '<p class="hint">人数が減っても「トップ+500」「ボトム−500」は保たれます。</p>' +
      '<h4>ドボン（可変）</h4><div class="num-grid">' +
      '<label>基本額<input type="number" step="50" data-set="base" value="' + s.dobonBase + '"></label>' +
      '<label>ジョーカー1枚あたり<input type="number" step="50" data-set="pj" value="' + s.dobonPerJoker + '"></label>' +
      '</div><p class="hint">ドボンした人は「基本額＋ジョーカー枚数×加算」を払い、その試合の1位が総取り。</p>' +
      '</div>' +
      '<div class="modal-foot"><button class="primary" data-action="save-settings">保存</button></div>'
    );
  }

  function saveSettings() {
    document.querySelectorAll('.modal input[data-set]').forEach(function (inp) {
      var val = parseFloat(inp.value);
      if (isNaN(val)) return;
      var t = inp.getAttribute('data-set');
      if (t === 'base') state.settings.dobonBase = val;
      else if (t === 'pj') state.settings.dobonPerJoker = val;
    });
    closeModal(); render();
  }

  function renderRosterModal() {
    var inputs = state.roster.map(function (n, i) {
      return '<label>' + (i + 1) + '<input type="text" data-roster-i="' + i + '" value="' + esc(n) + '"></label>';
    }).join('');
    openModal(
      '<div class="modal-head"><h3>名簿（11人）</h3><button class="del-btn" data-action="close-modal">✕</button></div>' +
      '<div class="modal-body"><p class="hint">名前はこの端末のブラウザ内だけに保存されます（GitHubには送られません）。</p>' +
      '<div class="roster-grid">' + inputs + '</div></div>' +
      '<div class="modal-foot"><button class="primary" data-action="save-roster">保存</button></div>'
    );
  }

  function saveRoster() {
    var next = state.roster.slice();
    document.querySelectorAll('.modal input[data-roster-i]').forEach(function (inp) {
      var name = inp.value.trim();
      if (name) next[+inp.getAttribute('data-roster-i')] = name;
    });
    var changed = {};
    state.roster.forEach(function (o, i) { if (o !== next[i]) changed[o] = next[i]; });
    state.roster = next;
    if (Object.keys(changed).length) {
      state.rounds.forEach(function (round) {
        round.teams.forEach(function (t) {
          if (changed[t.a]) t.a = changed[t.a];
          if (changed[t.b]) t.b = changed[t.b];
        });
        MATCH_ORDER.forEach(function (key) {
          var m = round.matches[key];
          m.order = m.order.map(function (n) { return changed[n] || n; });
          var nd = {};
          Object.keys(m.dobon || {}).forEach(function (n) { nd[changed[n] || n] = m.dobon[n]; });
          m.dobon = nd;
        });
      });
    }
    closeModal(); render();
  }

  function renderDataModal() {
    openModal(
      '<div class="modal-head"><h3>データ管理</h3><button class="del-btn" data-action="close-modal">✕</button></div>' +
      '<div class="modal-body"><p class="hint">記録はこの端末のブラウザに保存されます。端末をまたぐときは書き出し/読み込みを使ってください。</p>' +
      '<div class="data-btns">' +
      '<button class="secondary" data-action="export-data">📤 書き出し(JSON)</button>' +
      '<label class="secondary file-label">📥 読み込み(JSON)<input type="file" accept="application/json" data-action="import-data" hidden></label>' +
      '</div><hr><button class="danger" data-action="reset-all">全データ削除</button></div>'
    );
  }

  function exportData() {
    var blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    var d = new Date();
    a.href = url;
    a.download = 'shichinarabe-' + d.getFullYear() + ('0' + (d.getMonth() + 1)).slice(-2) + ('0' + d.getDate()).slice(-2) + '.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  function importData(file) {
    var reader = new FileReader();
    reader.onload = function () {
      try {
        var s = JSON.parse(reader.result);
        state = Object.assign(defaultState(), s);
        state.settings = Object.assign(CALC.defaultSettings(), state.settings || {});
        state.rounds = (state.rounds || []).map(migrateRound);
        state.ui = state.ui || { openRoundId: null, tab: {} };
        state.ui.tab = state.ui.tab || {};
        closeModal(); render();
        alert('読み込みました。');
      } catch (e) { alert('読み込みに失敗しました: ' + e.message); }
    };
    reader.readAsText(file);
  }

  // ---- イベント -----------------------------------------------------------
  function findRound(id) { return state.rounds.find(function (r) { return r.id === id; }); }

  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-action]');
    if (!t) return;
    var action = t.getAttribute('data-action');
    var round = findRound(t.getAttribute('data-round'));

    switch (action) {
      case 'add-round': {
        var r = newRound();
        state.rounds.push(r);
        state.ui.openRoundId = r.id;
        render(); break;
      }
      case 'toggle-round':
        if (e.target.closest('[data-action="delete-round"]')) return;
        state.ui.openRoundId = state.ui.openRoundId === round.id ? null : round.id;
        render(); break;
      case 'delete-round':
        e.stopPropagation();
        if (confirm('このチーム戦を削除しますか？')) {
          state.rounds = state.rounds.filter(function (r) { return r.id !== round.id; });
          render();
        }
        break;
      case 'add-team':
        round.teams.push(t.getAttribute('data-type') === 'solo'
          ? { type: 'solo', a: '', b: '' } : { type: 'pair', a: '', b: '' });
        sanitizeMatches(round); render(); break;
      case 'del-team':
        round.teams.splice(+t.getAttribute('data-ti'), 1);
        sanitizeMatches(round); render(); break;
      case 'set-teamtype': {
        var team = round.teams[+t.getAttribute('data-ti')];
        team.type = t.getAttribute('data-type');
        if (team.type === 'solo') team.b = '';
        sanitizeMatches(round); render(); break;
      }
      case 'match-tab':
        state.ui.tab[round.id] = t.getAttribute('data-match');
        render(); break;
      case 'rank-add': {
        var k = t.getAttribute('data-match'), name = t.getAttribute('data-name');
        if (round.matches[k].order.indexOf(name) < 0) round.matches[k].order.push(name);
        sanitizeMatches(round); render(); break;
      }
      case 'rank-undo': {
        var k2 = t.getAttribute('data-match');
        var last = round.matches[k2].order.pop();
        if (last && round.matches[k2].dobon) delete round.matches[k2].dobon[last];
        sanitizeMatches(round); render(); break;
      }
      case 'rank-reset':
        round.matches[t.getAttribute('data-match')] = { order: [], dobon: {} };
        sanitizeMatches(round); render(); break;
      case 'open-settings': renderSettingsModal(); break;
      case 'save-settings': saveSettings(); break;
      case 'open-roster': renderRosterModal(); break;
      case 'save-roster': saveRoster(); break;
      case 'open-data': renderDataModal(); break;
      case 'export-data': exportData(); break;
      case 'reset-all':
        if (confirm('全データを削除します。よろしいですか？')) { state = defaultState(); closeModal(); render(); }
        break;
      case 'close-modal': closeModal(); break;
    }
  });

  document.addEventListener('change', function (e) {
    var t = e.target.closest('[data-action]');
    if (!t) return;
    var action = t.getAttribute('data-action');
    var round = findRound(t.getAttribute('data-round'));

    if (action === 'set-team') {
      round.teams[+t.getAttribute('data-ti')][t.getAttribute('data-side')] = t.value;
      sanitizeMatches(round); render();
    } else if (action === 'set-cut') {
      var val = parseInt(t.value, 10); if (isNaN(val) || val < 0) val = 0;
      if (t.getAttribute('data-cut') === 'A') round.cutA = val; else round.cutB = val;
      sanitizeMatches(round); render();
    } else if (action === 'toggle-dobon') {
      var k = t.getAttribute('data-match'), name = t.getAttribute('data-name');
      if (!round.matches[k].dobon) round.matches[k].dobon = {};
      if (t.checked) round.matches[k].dobon[name] = 0; else delete round.matches[k].dobon[name];
      render();
    } else if (action === 'set-joker') {
      var k2 = t.getAttribute('data-match'), nm = t.getAttribute('data-name');
      if (!round.matches[k2].dobon) round.matches[k2].dobon = {};
      round.matches[k2].dobon[nm] = parseInt(t.value, 10) || 0;
      render();
    } else if (action === 'import-data') {
      if (t.files && t.files[0]) importData(t.files[0]);
    }
  });

  document.getElementById('btn-settings').addEventListener('click', renderSettingsModal);
  document.getElementById('btn-roster').addEventListener('click', renderRosterModal);
  document.getElementById('btn-data').addEventListener('click', renderDataModal);

  render();
})();

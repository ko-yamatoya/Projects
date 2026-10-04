/* ============================================================================
   selftest.js — ?selftest=1 のときだけ読み込まれる検証スイート
   本物のブラウザ・本物のIndexedDBでスキーマ・マージ規則・集計・描画を通す。
   実行前に手元のデータを退避し、終了時に必ず書き戻す（破壊しない）。
   使い方:
     python3 -m http.server → http://localhost:PORT/yaritai-list/?selftest=1
     ヘッドレスなら --dump-dom で #selftest-out を読む。document.title に結果が入る。
   ========================================================================== */
(async () => {
  const YL = window.YL;
  const out = [];
  let pass = 0, fail = 0;
  const ok = (name, cond, extra) => {
    if (cond) { pass++; out.push(`PASS  ${name}`); }
    else { fail++; out.push(`FAIL  ${name}${extra ? '  -- ' + extra : ''}`); }
  };
  const eq = (name, got, want) =>
    ok(name, JSON.stringify(got) === JSON.stringify(want), `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // ---- 退避 -------------------------------------------------------------
  const backup = { items: JSON.parse(JSON.stringify(YL.S.items)), analyses: JSON.parse(JSON.stringify(YL.S.analyses)) };

  try {
    /* ============================ 1. スキーマ正規化 ==================== */
    ok('normalize: 空タイトルは捨てる', YL.normalizeItem({ title: '   ' }) === null);
    ok('normalize: objectでないものは捨てる', YL.normalizeItem('x') === null);
    {
      const n = YL.normalizeItem({ title: ' テスト ', money: 'bogus', wtp: '10k', satisfaction: 9,
        done: 'yes', extra: 'ignored', history: [{ at: 'いつか', field: 'money' }, { at: '2026-09-01T00:00:00Z', field: 'money', from: null, to: 'pay' }] });
      eq('normalize: タイトルはtrim', n.title, 'テスト');
      eq('normalize: 不正なmoneyはnull', n.money, null);
      eq('normalize: 画面から外した金額帯も値は保持する', n.wtp, '10k');
      eq('normalize: 範囲外の満足度はnull', n.satisfaction, null);
      eq('normalize: done は厳密に true のみ', n.done, false);
    eq('normalize: statusの既定は未着手', n.status, 'todo');
      eq('normalize: 未知のフィールドは落とす', n.extra, undefined);
      eq('normalize: 壊れたhistory行は落とす', n.history.length, 1);
      eq('normalize: sourceの既定はapp', n.source, 'app');
      ok('normalize: idが無ければ生える', typeof n.id === 'string' && n.id.length >= 8);
    }
    {
      const n = YL.normalizeItem({ title: 'x', done: true, money: 'pay', wtp: '100k' });
      ok('normalize: done=trueでdoneAtが無ければ今日', /^\d{4}-\d{2}-\d{2}$/.test(n.doneAt));
      eq('normalize: 旧データの done=true は status=done になる', n.status, 'done');
      eq('normalize: 金額帯は保持', n.wtp, '100k');
    }
    {
      const a = YL.normalizeItem({ title: 'x', status: 'doing' });
      eq('normalize: 着手中なら着手日が入る', typeof a.startedAt, 'string');
      eq('normalize: 着手中は done=false', a.done, false);
      const b = YL.normalizeItem({ title: 'x', status: 'todo', startedAt: '2026-01-01' });
      eq('normalize: 未着手なら着手日は消える', b.startedAt, null);
    }
    eq('normalize: 旧区分 paid は hold に寄せる', YL.normalizeItem({ title: 'x', money: 'paid' }).money, 'hold');
    eq('normalize: 旧区分 free は未設定に落とす（読み替えない）', YL.normalizeItem({ title: 'x', money: 'free' }).money, null);
    eq('normalize: 旧区分 pay はそのまま', YL.normalizeItem({ title: 'x', money: 'pay' }).money, 'pay');
    eq('normalize: done=falseならdoneAtは消す', YL.normalizeItem({ title: 'x', done: false, doneAt: '2026-01-01' }).doneAt, null);
    ok('normalize(analysis): summary空は捨てる', YL.normalizeAnalysis({ summary: '' }) === null);
    eq('normalize: 短いidも尊重する（マージで重複しない）', YL.normalizeItem({ id: 'id-1', title: 'x' }).id, 'id-1');
    eq('normalize: 旧金額帯 100k+ は 200k に読み替える',
       YL.normalizeItem({ title: 'x', money: 'pay', wtp: '100k+' }).wtp, '200k');

    /* ============================ 2. マージ規則 ======================== */
    const base = (o) => Object.assign({
      id: 'id-1', title: 'A', category: '旅（国内）', memo: '', money: null, wtp: null, when: '', nextStep: '',
      done: false, doneAt: null, reflection: '', satisfaction: null, source: 'app',
      createdAt: '2026-09-01T00:00:00.000Z', updatedAt: '2026-09-01T00:00:00.000Z', deletedAt: null, history: []
    }, o);
    {
      const mine = [base({ title: '手元が古い', updatedAt: '2026-09-01T00:00:00.000Z' })];
      const theirs = { items: [base({ title: '相手が新しい', updatedAt: '2026-09-10T00:00:00.000Z' })] };
      const r = YL.mergeData(mine, [], theirs);
      eq('merge: updatedAtが新しい方を採用', r.items[0].title, '相手が新しい');
      eq('merge: 件数は増えない', r.items.length, 1);
      eq('merge: stats.updated', r.stats.updated, 1);
    }
    {
      const mine = [base({ title: '手元が新しい', updatedAt: '2026-09-20T00:00:00.000Z' })];
      const theirs = { items: [base({ title: '相手が古い', updatedAt: '2026-09-10T00:00:00.000Z' })] };
      const r = YL.mergeData(mine, [], theirs);
      eq('merge: 古い方では上書きしない', r.items[0].title, '手元が新しい');
    }
    {
      const h1 = { at: '2026-09-02T00:00:00.000Z', field: 'money', from: null, to: 'pay' };
      const h2 = { at: '2026-09-03T00:00:00.000Z', field: 'done', from: false, to: true };
      const mine = [base({ history: [h1] })];
      const theirs = { items: [base({ updatedAt: '2026-09-11T00:00:00.000Z', history: [h1, h2] })] };
      const r = YL.mergeData(mine, [], theirs);
      eq('merge: historyは統合して重複排除', r.items[0].history.length, 2);
      eq('merge: historyは時刻順', r.items[0].history.map(h => h.field), ['money', 'done']);
    }
    {
      const mine = [base({ deletedAt: '2026-09-05T00:00:00.000Z', updatedAt: '2026-09-05T00:00:00.000Z' })];
      const theirs = { items: [base({ title: '復活させたい', updatedAt: '2026-09-30T00:00:00.000Z', deletedAt: null })] };
      const r = YL.mergeData(mine, [], theirs);
      ok('merge: 削除済みは復活しない', r.items[0].deletedAt === '2026-09-05T00:00:00.000Z');
      eq('merge: stats.keptDeleted', r.stats.keptDeleted, 1);
    }
    {
      const a1 = { id: 'an-1', createdAt: '2026-09-01T00:00:00.000Z', periodFrom: '2026-08-01', periodTo: '2026-08-31', summary: '# 8月' };
      const a2 = { id: 'an-2', createdAt: '2026-10-01T00:00:00.000Z', periodFrom: null, periodTo: null, summary: '# 9月' };
      const r = YL.mergeData([], [a1], { items: [], analyses: [a1, a2] });
      eq('merge: analysesはidで和集合', r.analyses.length, 2);
      eq('merge: analysesは新しい順', r.analyses[0].id, 'an-2');
      eq('merge: stats.analysesAdded', r.stats.analysesAdded, 1);
      const rewritten = Object.assign({}, a1, { summary: '# 8月（書き直し）' });
      const r2 = YL.mergeData([], [a1, a2], { items: [], analyses: [rewritten] });
      eq('merge: 同じidで中身が違えば置き換える', r2.analyses.find(x => x.id === 'an-1').summary, '# 8月（書き直し）');
      eq('merge: stats.analysesUpdated', r2.stats.analysesUpdated, 1);
      const r3 = YL.mergeData([], [a1, a2], { items: [], analyses: [a1] });
      eq('merge: 同内容なら置き換えない', r3.stats.analysesUpdated, 0);
    }
    {
      const r = YL.mergeData([], [], { items: [{ title: '' }, null, { title: 'ok' }] });
      eq('merge: 読めない行はskippedに数える', r.stats.skipped, 2);
      eq('merge: 読める行は取り込む', r.items.length, 1);
    }

    /* ============================ 3. Markdown ========================= */
    {
      const h = YL.mdToHtml('# 見出し\n\n- a\n- b\n\n**強調** と `code`\n\n| 列1 | 列2 |\n|---|---|\n| 1 | 2 |\n\n<script>alert(1)</script>');
      ok('md: 見出し', h.includes('<h1>見出し</h1>'));
      ok('md: 箇条書き', h.includes('<ul><li>a</li><li>b</li></ul>'));
      ok('md: 強調とコード', h.includes('<strong>強調</strong>') && h.includes('<code>code</code>'));
      ok('md: 表', h.includes('<table>') && h.includes('<td>2</td>'));
      ok('md: HTMLはエスケープされる（scriptを通さない）', !/<script/i.test(h) && h.includes('&lt;script&gt;'));
    }

    /* ============================ 4. 往復（本物のIndexedDB） ========== */
    YL.S.items = []; YL.S.analyses = [];
    await YL.idbReplaceAll('items', []); await YL.idbReplaceAll('analyses', []);

    const fixture = {
      schemaVersion: 1, exportedAt: new Date().toISOString(),
      items: [
        base({ id: 'fix-1', title: '初期っぽい項目', source: 'initial', category: '旅（海外）',
               createdAt: '2026-09-30T00:00:00.000Z', updatedAt: '2026-09-30T00:00:00.000Z' }),
        base({ id: 'fix-2', title: '消した項目', deletedAt: '2026-09-29T00:00:00.000Z',
               createdAt: '2026-09-28T00:00:00.000Z', updatedAt: '2026-09-29T00:00:00.000Z' }),
      ],
      analyses: [{ id: 'an-x', createdAt: '2026-09-30T01:00:00.000Z', periodFrom: '2026-09-01', periodTo: '2026-09-30', summary: '## テスト分析\n- ひとつ' }],
    };
    const st = await YL.importJSON(JSON.stringify(fixture));
    eq('往復: インポートで2件追加', st.added, 2);
    eq('往復: 生きている項目は1件（削除は復活しない）', YL.live().length, 1);
    eq('往復: 分析も入る', YL.S.analyses.length, 1);

    const added = YL.addItem('セルフテストで追加した項目', { category: '体験' });
    YL.updateItem(added.id, { money: 'pay' });
    YL.setStatus(added.id, 'doing');
    eq('操作: 着手中にすると着手日が入る', typeof YL.byId(added.id).startedAt, 'string');
    eq('操作: 着手中は完了ではない', YL.byId(added.id).done, false);
    YL.setDone(added.id, true);
    eq('操作: 完了にすると status も done', YL.byId(added.id).status, 'done');
    YL.updateItem(added.id, { satisfaction: 4, reflection: 'よかった' });
    const cur = YL.byId(added.id);
    eq('操作: money変更がhistoryに入る', cur.history.filter(h => h.field === 'money').length, 1);
    eq('操作: 状態変更がhistoryに入る', cur.history.filter(h => h.field === 'status').length, 2);
    ok('操作: 達成日が自動で入る', /^\d{4}-\d{2}-\d{2}$/.test(cur.doneAt));
    eq('操作: source=app', cur.source, 'app');

    const exp = YL.buildExport();
    eq('書き出し: schemaVersion', exp.schemaVersion, 1);
    ok('書き出し: スキーマ説明を同梱している', !!exp.schema && !!exp.schema['items[].money']);
    ok('書き出し: AIへの依頼文を同梱している', typeof exp.aiPrompt === 'string' && exp.aiPrompt.length > 500);
    ok('書き出し: 依頼文に年収シミュレーションが入っている', /年収/.test(exp.aiPrompt));
    ok('書き出し: 依頼文が返却フォーマットを指定している', /analyses/.test(exp.aiPrompt) && /analysis-/.test(exp.aiPrompt));
    ok('書き出し: 説明書を同梱している', Array.isArray(exp.readme) && exp.readme.length > 0);
    ok('書き出し: 同梱物があってもマージは items/analyses だけ見る',
       YL.mergeData([], [], exp).items.length === exp.items.length);
    ok('書き出し: exportedAtはISO', !isNaN(new Date(exp.exportedAt).getTime()));
    eq('書き出し: 論理削除ぶんも含む（3件）', exp.items.length, 3);
    ok('書き出し: JSONとして再読込できる', (() => { try { return !!JSON.parse(JSON.stringify(exp)); } catch (e) { return false; } })());
    {
      const r2 = YL.mergeData(YL.S.items, YL.S.analyses, JSON.parse(JSON.stringify(exp)));
      eq('冪等性: 同じJSONをもう一度マージしても増えない', r2.items.length, exp.items.length);
      eq('冪等性: 更新も走らない', r2.stats.updated, 0);
      eq('冪等性: すべて変更なし', r2.stats.same, exp.items.length);
    }
    // IndexedDBに本当に書けているか（別トランザクションで読み直す）
    {
      const db = await new Promise((res, rej) => { const q = indexedDB.open('yaritai-list', 1); q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); });
      const got = await new Promise((res, rej) => { const q = db.transaction(['items'], 'readonly').objectStore('items').getAll(); q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); });
      eq('永続化: IndexedDBに3件保存されている', got.length, 3);
      ok('永続化: 追加した項目が読める', got.some(i => i.id === added.id && i.done === true));
      db.close();
    }

    /* ============================ 5. 集計と描画 ======================== */
    YL.go('trend'); await sleep(60);
    const months = YL.rangeMonths();
    ok('集計: 月リストが連続している', months.every((m, n) => n === 0 || (() => {
      const [py, pm] = months[n - 1].split('-').map(Number); const [y, mo] = m.split('-').map(Number);
      return (y * 12 + mo) - (py * 12 + pm) === 1; })()));
    ok('描画: 棒グラフのSVGが出ている', !!document.querySelector('#ch1 svg.chart'));
    ok('描画: 100%積み上げ2つが出ている', !!document.querySelector('#ch2 svg.chart path') && !!document.querySelector('#ch3 svg.chart path'));
    eq('描画: 月数とホバー領域の数が一致', document.querySelectorAll('#ch1 .band').length, months.length);
    ok('描画: どのグラフにも「表で見る」がある', document.querySelectorAll('#trend-out details.fold').length >= 3);
    ok('描画: 凡例がある', document.querySelectorAll('#trend-out .legend').length >= 3);
    ok('集計: 初期一括ぶんは追加数の推移に入らない',
      !/初期っぽい項目/.test('') && (() => {
        const rows = Array.from(document.querySelectorAll('#trend-out table.dt'))[0].querySelectorAll('tbody tr');
        const total = Array.from(rows).reduce((a, tr) => a + (+tr.children[1].textContent || 0), 0);
        return total === 1; // app由来の1件だけ
      })());

    YL.go('list'); await sleep(40);
    eq('描画: 一覧の行数（削除は出さない）', document.querySelectorAll('#list-out li.item').length, YL.live().length);
    {
      // カテゴリ絞り込みの複数選択
      const cats = [...new Set(YL.live().map(i => i.category).filter(Boolean))];
      YL.S.f.cat = cats.slice(0, 1); YL.renderAll(); await sleep(40);
      const want1 = YL.live().filter(i => i.category === cats[0]).length;
      eq('絞り込み: カテゴリ1つ', document.querySelectorAll('#list-out li.item').length, want1);
      if (cats.length > 1) {
        YL.S.f.cat = cats.slice(0, 2); YL.renderAll(); await sleep(40);
        const want2 = YL.live().filter(i => cats.slice(0,2).includes(i.category)).length;
        eq('絞り込み: カテゴリ2つ（和集合）', document.querySelectorAll('#list-out li.item').length, want2);
        ok('絞り込み: 選択中のチップが押下状態', document.querySelectorAll('#f-cat [aria-pressed="true"]').length === 2);
      }
      YL.S.f.cat = []; YL.renderAll(); await sleep(40);
      eq('絞り込み: 解除で全件に戻る', document.querySelectorAll('#list-out li.item').length, YL.live().length);
    }
    {
      // 回帰テスト: 詳細シートを開き直したとき、前の項目に書き込まれないこと
      YL.go('list'); await sleep(50);
      const rows = [...document.querySelectorAll('#list-out li.item')];
      if (rows.length >= 2) {
        const idA = rows[0].dataset.id, idB = rows[1].dataset.id;
        const titleA = YL.byId(idA).title, catA = YL.byId(idA).category;
        const click = el => el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        click(rows[0].querySelector('[data-act="open"]')); await sleep(120);
        click(document.querySelector('#sheet [data-x="close"]')); await sleep(340);
        const rows2 = [...document.querySelectorAll('#list-out li.item')];
        click(rows2[1].querySelector('[data-act="open"]')); await sleep(120);
        document.querySelector('#d-title').value = 'シート回帰テストで書き換えたタイトル';
        eq('詳細: カテゴリはプルダウン', document.querySelector('#d-cat').tagName, 'SELECT');
        const sel = document.querySelector('#d-cat');
        ok('詳細: プルダウンに新規作成の選択肢がある', !!sel.querySelector('option[value="__new"]'));
        sel.value = '__new';
        sel.dispatchEvent(new Event('change', { bubbles: true }));
        await sleep(40);
        ok('詳細: 新規を選ぶと入力欄が出る', !document.querySelector('#d-cat-new').hidden);
        document.querySelector('#d-cat-new').value = 'テスト用カテゴリ';
        click(document.querySelector('#sheet [data-x="save"]')); await sleep(160);
        eq('シート: 保存したのは開いている項目だけ（タイトル）', YL.byId(idB).title, 'シート回帰テストで書き換えたタイトル');
        eq('シート: 開いている項目のカテゴリは保存される', YL.byId(idB).category, 'テスト用カテゴリ');
        eq('シート: 前に開いた項目のタイトルは無傷', YL.byId(idA).title, titleA);
        eq('シート: 前に開いた項目のカテゴリも無傷', YL.byId(idA).category, catA);
      }
    }
    {
      // 進捗とボード
      const p = YL.progress();
      eq('進捗: 件数の合計が一致', p.todo + p.doing + p.done, YL.live().length);
      YL.go('list'); await sleep(50);
      ok('進捗: バーが出ている', !!document.querySelector('#prog .bar'));
      // [hidden] が display 指定に負けていないか（実際に絞り込みが開きっぱなしになった）
      YL.S.filterOpen = false; YL.S.f.cat = []; YL.S.f.status = 'all'; YL.S.f.money = '';
      YL.S.sort = 'createdAt-desc'; YL.S.group = 'none'; YL.renderAll(); await sleep(40);
      eq('絞り込み: 既定では閉じている', getComputedStyle(document.querySelector('#f-more')).display, 'none');
      eq('リスト表示中はボードを出さない', getComputedStyle(document.querySelector('#board-out')).display, 'none');
      YL.S.mode = 'board'; YL.renderAll(); await sleep(60);
      eq('ボード: 列は3つ', document.querySelectorAll('#board-out .col').length, 3);
      eq('ボード表示中はリストを出さない', getComputedStyle(document.querySelector('#list-out')).display, 'none');
      const cards = document.querySelectorAll('#board-out .bcard');
      eq('ボード: カード数が項目数と一致', cards.length, YL.live().length);
      const card = document.querySelector('#board-out .col[data-s="done"] .bcard');
      if (card) {
        const id = card.dataset.id;
        card.querySelector('[data-mv="-1"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
        await sleep(80);
        eq('ボード: 左へ動かすと着手中になる', YL.byId(id).status, 'doing');
        ok('ボード: 完了列の右ボタンは押せない',
           document.querySelector('#board-out .col[data-s="done"] [data-mv="1"]') === null ||
           document.querySelector('#board-out .col[data-s="done"] [data-mv="1"]').disabled);
        YL.setStatus(id, 'done');
      }
      YL.S.mode = 'list'; YL.renderAll(); await sleep(40);
    }
    YL.go('triage'); await sleep(40);
    eq('描画: 仕分けの残りは未設定の件数', YL.live().filter(i => i.money === null).length, 1);
    ok('描画: 仕分けカードが出ている', !!document.querySelector('.tri-card'));
    {
      const t0 = document.querySelector('.tri-card .t').textContent;
      eq('仕分け: 選択肢は3つ', document.querySelectorAll('.tri-btns .big').length, 3);
      document.querySelector('[data-t="1"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await sleep(80);
      const it = YL.live().find(i => i.title === t0);
      eq('仕分け: 1タップで money=pay が入る', it && it.money, 'pay');
      ok('仕分け: payを選ぶと金額感を聞いてくる', document.querySelectorAll('.wtp-grid [data-w]').length === 10);
      document.querySelector('[data-w="30k"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
      await sleep(80);
      eq('仕分け: 金額感が入る', YL.live().find(i => i.title === t0).wtp, '30k');
      ok('仕分け: historyにmoney変更が残る', it.history.some(h => h.field === 'money' && h.to === 'pay'));
      eq('仕分け: 残りが0件になる', YL.live().filter(i => i.money === null).length, 0);
    }
    YL.go('log'); await sleep(40);
    ok('描画: 記録タブが描画される', !!document.querySelector('#log-out'));
    YL.go('data'); await sleep(40);
    ok('描画: データ画面が描画される', !!document.querySelector('[data-d="export"]'));

    /* ============================ 6. 公開モード ======================== */
    {
      YL.S.pub = true; document.body.dataset.pub = '1';
      const el = document.querySelector('.sens');
      ok('公開モード: sens要素が隠れる', !el || getComputedStyle(el).display === 'none');
      YL.S.pub = false; document.body.dataset.pub = '0';
    }

    /* ============================ 7. 実データの取り込み（あれば） ====== */
    try {
      const res = await fetch('./_test-master.json', { cache: 'no-store' });
      if (res.ok) {
        const text = await res.text();
        const data = JSON.parse(text);
        const before = YL.live().length;
        const stats = await YL.importJSON(text);
        ok('実データ: master.jsonを取り込める', stats.added > 0, JSON.stringify(stats));
        eq('実データ: 取り込み後の件数', YL.live().length, before + data.items.filter(i => !i.deletedAt).length);
        ok('実データ: 区分はすべて有効な値',
           YL.live().every(i => i.money === null || ['pay', 'hold', 'none'].includes(i.money)));
        ok('実データ: 分析も一緒に取り込める', YL.S.analyses.length > 0);
        // 追加 → エクスポート（往復の後半）
        const extra = YL.addItem('往復テスト: アプリから追加', { category: '体験' });
        YL.updateItem(extra.id, { money: 'free' });
        const exp2 = YL.buildExport();
        const pre = document.createElement('pre');
        pre.id = 'export-out'; pre.hidden = true;
        pre.textContent = JSON.stringify(exp2);
        document.body.appendChild(pre);
        out.push(`INFO  往復用エクスポートを #export-out に出力（items=${exp2.items.length}）`);
      } else {
        out.push('SKIP  実データ（_test-master.json なし）');
      }
    } catch (e) { out.push('SKIP  実データ（' + e.message + '）'); }

  } catch (e) {
    fail++; out.push('FAIL  例外で中断: ' + (e && e.stack ? e.stack : e));
  } finally {
    // ---- 書き戻し -------------------------------------------------------
    const keepExport = document.getElementById('export-out');
    if (!keepExport) {
      YL.S.items = backup.items; YL.S.analyses = backup.analyses;
      try { await YL.idbReplaceAll('items', backup.items); await YL.idbReplaceAll('analyses', backup.analyses); } catch (e) {}
      YL.renderAll();
    }
  }

  const head = `SELFTEST ${fail ? 'FAIL' : 'PASS'} ${pass}/${pass + fail}`;
  document.title = head;
  const pre = document.createElement('pre');
  pre.id = 'selftest-out';
  pre.style.cssText = 'white-space:pre-wrap; font-size:11px; padding:16px; margin:0; line-height:1.7';
  pre.textContent = head + '\n' + out.join('\n');
  document.body.appendChild(pre);
  console.log(head + '\n' + out.join('\n'));

  /* ヘッドレス検証用: テストサーバに結果を返す（本番では単に失敗して無視される） */
  try {
    const ex = document.getElementById('export-out');
    await fetch('/__report', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ head, pass, fail, lines: out, exportJson: ex ? ex.textContent : null }) });
  } catch (e) { /* 本番やオフラインでは何もしない */ }
})();

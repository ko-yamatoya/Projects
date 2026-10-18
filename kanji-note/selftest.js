/* ============================================================================
   selftest.js — ?selftest=1 のときだけ読み込まれる検証スイート
   本物のブラウザ・本物のIndexedDB（検証専用の別DB "kanji-note-selftest"）で、
   入力の正規化・集計・LINE用の文・受け渡しの取り込み（項目ごとのマージ）・
   保存・画面の操作を通す。ふだんのデータには触らない。

   使い方:
     cd Projects && python3 -m http.server 8765
     open "http://localhost:8765/kanji-note/?selftest=1"
   ヘッドレスなら --dump-dom で #selftest-out を読む。document.title に結果が入る。

   画面確認用: ?demo=1&selftest=scene&scene=<名前> で、お試しデータの特定の画面を開いて止まる。
   ========================================================================== */
(async () => {
  const K = window.KN, S = K.S;
  const sp = new URLSearchParams(location.search);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const click = el => { if (!el) throw new Error('element not found'); el.click(); };
  const setVal = (el, v, type = 'input') => { el.value = v; el.dispatchEvent(new Event(type, { bubbles: true })); };
  const go = async hash => { location.hash = hash; await sleep(60); };

  /* ======================================================== scenes（スクショ用） */
  if (sp.get('selftest') === 'scene'){
    const scene = sp.get('scene') || 'home';
    const ev = () => K.S.events.find(e => e.id === 'e-next');
    if (scene === 'welcome'){ for (const k of ['sports','members','shops','events','extras']) S[k] = []; K.renderAll(); }
    if (scene === 'cal'){ K.prefs.homeMode = 'cal'; S.ui.calDay = ev().date; K.renderAll(); }
    if (scene.startsWith('dark')){ K.prefs.theme = 'dark'; K.applyPrefs(); }
    if (scene.startsWith('xl')){ K.prefs.font = 'xl'; K.applyPrefs(); }
    const evScenes = { people: '', person: '', addpeople: '', handoff: '', 'dark-people': '', 'xl-people': '', dinner: '/dinner', numpad: '/dinner', shoptext: '/dinner', phone: '/dinner', money: '/money', tape: '/tape', 'dark-dinner': '/dinner' };
    if (scene in evScenes) await go('#/e/e-next' + evScenes[scene]);
    if (scene === 'members') await go('#/members');
    if (scene === 'moneyview') await go('#/money');
    if (scene === 'data') await go('#/data');
    if (scene === 'settings') await go('#/settings');
    if (scene === 'person') K.openSheet('person', { evId: 'e-next', mid: 'm08' });
    if (scene === 'numpad') K.openSheet('numpad', { evId: 'e-next', mid: 'm09', no: '3', qty: 1, text: false });
    if (scene === 'shoptext') K.ACT.text({ dataset: { kind: 'shop' } });
    if (scene === 'phone') K.openSheet('phone', { evId: 'e-next' });
    if (scene === 'addpeople') K.ACT.addPeople({ dataset: {} });
    if (scene === 'editor') K.ACT.newEvent({ dataset: {} });
    if (scene === 'handoff'){ K.ACT.handoff({ dataset: { kind: 'handoff', id: 'e-next' } }); await sleep(300); }
    if (scene === 'import'){ await K.receiveCode(await K.buildHandoffText('return', ['e-next'])); }
    if (sp.get('scroll')) window.scrollTo(0, +sp.get('scroll'));
    if (sp.get('sscroll')){ await sleep(50); const b = $('.sheet-b'); if (b) b.scrollTop = +sp.get('sscroll'); }
    await sleep(150);
    document.title = 'SCENE READY ' + scene;
    return;
  }

  /* ======================================================== テスト本体 */
  const out = []; let pass = 0, fail = 0;
  const ok = (name, cond, extra) => { if (cond){ pass++; out.push('PASS  ' + name); } else { fail++; out.push('FAIL  ' + name + (extra ? '  -- ' + extra : '')); } };
  const eq = (name, got, want) => ok(name, JSON.stringify(got) === JSON.stringify(want), `got ${JSON.stringify(got)} want ${JSON.stringify(want)}`);
  const has = (name, text, part) => ok(name, typeof text === 'string' && text.includes(part), `「${part}」が見つからない: ${String(text).slice(0, 300)}`);
  const throwsAsync = async (name, fn, msg) => { try { await fn(); ok(name, false, 'throwしなかった'); } catch (e) { ok(name, !msg || e.message === msg, 'message=' + e.message); } };
  const noOverflow = name => {
    const w = document.documentElement.scrollWidth, v = window.innerWidth;
    ok('はみ出しなし: ' + name, w <= v + 1, `scrollWidth ${w} > innerWidth ${v}`);
    const sh = $('.sheet'); if (sh) ok('シートのはみ出しなし: ' + name, sh.scrollWidth <= sh.clientWidth + 1, `${sh.scrollWidth} > ${sh.clientWidth}`);
  };
  const origConfirm = window.confirm; window.confirm = () => true;
  const errors = [];
  window.addEventListener('error', e => errors.push(e.message));
  window.addEventListener('unhandledrejection', e => errors.push(String(e.reason)));

  try {
    ok('検証用の別DBを使っている', K.dbOK === true);
    /* 前回の残りを消す */
    for (const k of ['sports','members','shops','events','extras']) S[k] = [];
    S.settings = K.normSettings({}); await K.saveAll();

    /* ================================================== 1. 文字・数字の整え方 */
    eq('全角数字を半角に', K.toHalf('３番'), '3番');
    eq('番号: No.３ → 3', K.normNo('No.３'), '3');
    eq('番号: 12番 → 12', K.normNo('12番'), '12');
    eq('番号: 英字は大文字', K.normNo(' a1 '), 'A1');
    eq('金額: 1,200円 → 1200', K.toInt('1,200円'), 1200);
    eq('金額: 全角 → 数字', K.toInt('５００'), 500);
    eq('金額: 文字は null', K.toInt('abc'), null);
    eq('金額: 空は null', K.toInt(''), null);
    eq('金額: マイナスは0に', K.toInt(-5), 0);
    eq('名前の貼り付け: 改行・さん・記号・番号', K.parseNames('田中\n佐藤さん\n・鈴木 一郎\n1. 高橋\n\n田中'), ['田中', '佐藤', '鈴木 一郎', '高橋']);
    eq('名前の貼り付け: 読点区切り', K.parseNames('田中、佐藤,鈴木'), ['田中', '佐藤', '鈴木']);
    eq('名前の貼り付け: 1行スペース区切り', K.parseNames('田中 佐藤 鈴木'), ['田中', '佐藤', '鈴木']);
    {
      const m = K.parseMenu('1 から揚げ定食 950\n11 生ビール ¥550\nA1 枝豆\n3番 チキン南蛮 1,000円\nでたらめ');
      eq('メニュー貼り付け: 4行読める', m.map(x => x.no), ['1', '11', 'A1', '3']);
      eq('メニュー貼り付け: 値段', m.map(x => x.price), [950, 550, null, 1000]);
      eq('メニュー貼り付け: 名前', m[3].name, 'チキン南蛮');
    }
    eq('いつもの注文: 3 11×2 A1', K.parseOrders('3 11×2 a1'), [{ no: '3', qty: 1 }, { no: '11', qty: 2 }, { no: 'A1', qty: 1 }]);
    eq('いつもの注文: 3x2', K.parseOrders('3x2'), [{ no: '3', qty: 2 }]);
    eq('同じ番号はまとめる', K.normOrders([{ no: '3', qty: 1 }, { no: '３', qty: 2 }]), [{ no: '3', qty: 3 }]);
    eq('次の土曜', K.nextWeekday('2026-10-18', 6), '2026-10-24');
    eq('日付の表示', K.fmtDate('2026-10-24'), '10月24日(土)');
    eq('切り上げ', K.ceilTo(1950, 100), 2000);
    ok('ありえない日付は不可', !K.validDate('2026-02-30') && K.validDate('2026-02-28'));

    /* ================================================== 2. 取り込み時の門番 */
    ok('日程: 日付が不正なら捨てる', K.normEvent({ date: '2026-13-01' }) === null);
    {
      const ev = K.normEvent({ date: '2026-10-24', entries: [{ memberId: 'a' }, { memberId: 'a' }, { memberId: '<b>' }] });
      eq('日程: 参加費の既定', ev.tiers.length, 1);
      eq('日程: ご飯代の既定は集めない', ev.dinnerFee.mode, 'none');
      eq('日程: 同じ人の重複と不正なIDを落とす', ev.entries.map(e => e.memberId), ['a']);
    }
    ok('メンバー: 空の名前は捨てる', K.normMember({ name: '   ' }) === null);
    eq('メンバー: 全角英字・全角空白を整える', K.normMember({ name: 'ＴＡＫＡ　太郎' }).name, 'TAKA 太郎');
    eq('お店: 番号の重複を落として番号順', K.normShop({ name: 'x', menu: [{ no: '10' }, { no: '2', name: 'a' }, { no: '2', name: 'b' }] }).menu.map(x => x.no + x.name), ['2a', '10']);
    eq('支払っていなければ受取日時は消す', K.normEntry({ memberId: 'a', paid: false, paidAt: '2026-10-01T00:00:00.000Z' }).paidAt, null);
    eq('知らない項目は落とす', K.normSport({ name: 'x', evil: 1 }).evil, undefined);
    eq('絵文字は決まった中から', K.normSport({ name: 'x', emoji: '<img>' }).emoji, '🏅');

    /* ================================================== 3. 集計（お試しデータ） */
    K.loadSample();
    const evN = S.events.find(e => e.id === 'e-next'), ev1 = S.events.find(e => e.id === 'e-past1'), ev2 = S.events.find(e => e.id === 'e-past2');
    {
      const s = K.summary(evN);
      eq('出欠の数（参加・未定・未回答・休み）', [s.yes, s.maybe, s.none, s.no], [9, 2, 1, 2]);
      eq('ご飯の数（行く・ご飯だけ・返事まだ）', [s.dinner, s.dinnerOnly, s.dinnerAsk], [8, 1, 1]);
      eq('注文の数（品数・注文まだ・確認済み）', [s.items, s.noOrder, s.orderOk], [9, 2, 2]);
      eq('参加費（予定・受取・人数）', [s.feeDue, s.feeGot, s.feePeople, s.feePaid], [4300, 1000, 9, 2]);
      eq('この日の収支', s.balance, -3000);
    }
    {
      const t = K.tally(evN);
      eq('注文の集計: 番号順（11は7のあと）', t.rows.map(r => r.no), ['1', '2', '3', '4', '5', '7', '11']);
      eq('注文の集計: 生ビール3つ', t.rows.find(r => r.no === '11').qty, 3);
      eq('注文の集計: 合計金額', t.total, 7250);
    }
    has('お店への文: 品と数', K.shopText(evN), '11番 生ビール ×3');
    has('お店への文: 合計', K.shopText(evN), '合計 9品');
    has('お店への文: 人数', K.shopText(evN), '8名でお願いいたします');
    has('お店への文: 注文まだの人', K.shopText(evN), '※ほかに2名は当日注文');
    has('お店への文: メモ', K.shopText(evN), 'ご飯少なめ');
    has('募集の文: 見出し', K.announceText(evN), '【🏀 バスケ】');
    has('募集の文: 料金区分', K.announceText(evN), '参加費 一般 500円／学生 300円');
    has('募集の文: お店', K.announceText(evN), 'ご飯に行きます（サンプル食堂 21:30〜）');
    has('出欠まとめ: 参加と定員', K.attendText(evN), '✅ 参加 9人（定員18人）');
    has('出欠まとめ: 返事がない人', K.attendText(evN), '⏳ まだ返事がない人 1人');
    has('だれが何を: 人ごと', K.whoText(evN), '中村 大輔×2');
    has('集金のお願い: 人数', K.unpaidText(evN), 'まだの方（7人）');
    has('集金のお願い: ひとこと', K.unpaidText(evN), 'PayPayでもOKです');
    has('名札リスト', K.tapeText(evN), '・タロウ（田中 太郎）');
    {
      const s2 = K.summary(ev2);
      eq('割り勘: 1人あたり', K.dinnerFeeOf(ev2, ev2.entries[0]), 2600);
      eq('割り勘: 合計と受取', [s2.dDue, s2.dGot], [15600, 15600]);
      eq('参加費の未払い1人', [s2.feePeople, s2.feePaid], [10, 9]);
      eq('注文の値段で計算', K.dinnerFeeOf(ev1, ev1.entries[0]), 1500);
    }
    {
      const up = K.unpaidAll();
      eq('未払い一覧は過去の日程だけ', up.map(x => [x.ev.id, x.e.memberId, x.amount]), [['e-past2', 'm13', 400]]);
      eq('手元のお金（はじめ＋今日までの収支＋前払い−ボール代）', K.ledger().cash, 8900);
      eq('参加回数と最後に来た日', [K.statOf('m02').count, K.statOf('m02').last], [2, ev2.date]);
      eq('次の日程の候補は1週間後', K.suggestDate('s-bask'), K.addDays(evN.date, 7));
    }
    {
      evN.sent = { at: new Date().toISOString(), count: 8, tally: K.tallyMap(evN) };
      ok('お店に伝えた直後は変更なし', K.sentDiff(evN).changed === false);
      const e = evN.entries.find(x => x.memberId === 'm09');
      e.orders = [{ no: '6', qty: 1 }];
      const d = K.sentDiff(evN);
      ok('伝えたあとの変更を見つける', d.changed && d.changes.some(c => c.no === '6' && c.from === 0 && c.to === 1));
      e.orders = []; evN.sent = null;
    }

    /* ================================================== 4. 受け渡し（項目ごとのマージ） */
    {
      const later = n => new Date(Date.now() + n * 1000).toISOString();
      const pkg = K.buildPkg('handoff', ['e-next']);
      ok('渡すデータにメンバーのメモは入れない', pkg.members.every(m => m.memo === '') && pkg.members.some(m => m.id === 'm03'));
      eq('渡すデータに入るのは関係する人だけ', pkg.members.length, evN.entries.length);
      const helper = JSON.parse(JSON.stringify(pkg)); helper.kind = 'return'; helper.from = '手伝い';
      const hev = helper.events[0];
      const he = id => hev.entries.find(e => e.memberId === id);
      Object.assign(he('m02'), { paid: true, paidAt: later(60), payMethod: '現金' }); he('m02').ts.pay = later(60);
      Object.assign(he('m14'), { paid: true }); he('m14').ts.pay = later(60);
      helper.members.push({ id: 'walkin1', name: '飛び入り 太郎', updatedAt: later(60), createdAt: later(60) });
      hev.entries.push({ memberId: 'walkin1', status: 'yes', paid: true, paidAt: later(60), ts: { status: later(60), pay: later(60) } });
      const hm3 = helper.members.find(m => m.id === 'm03'); hm3.tape = 'イチ'; hm3.updatedAt = later(60);
      /* 幹事側も同時に別のことをしている */
      const m04 = evN.entries.find(e => e.memberId === 'm04'); m04.status = 'yes'; m04.ts.status = later(30);
      const m14 = evN.entries.find(e => e.memberId === 'm14'); m14.paid = false; m14.paidAt = null; m14.ts.pay = later(120);
      const st = K.mergePkg(helper);
      ok('手伝いの集金チェックが反映される', evN.entries.find(e => e.memberId === 'm02').paid === true);
      ok('幹事の出欠の変更は消えない', m04.status === 'yes');
      ok('同じ項目は新しい方（幹事の取り消し）が残る', m14.paid === false);
      ok('飛び入りの人が追加される', !!S.members.find(m => m.id === 'walkin1') && !!evN.entries.find(e => e.memberId === 'walkin1'));
      ok('名札の名前は反映、メモは手元のまま', S.members.find(m => m.id === 'm03').tape === 'イチ' && S.members.find(m => m.id === 'm03').memo === 'えびアレルギー');
      has('取り込みの報告に集金が出る', K.mergeReport(st), '集金');
      const st2 = K.mergePkg(helper);
      has('同じものを2回受け取っても変わらない', K.mergeReport(st2), 'すでに最新');
      /* 日程の見出し（場所など）は hdrAt が新しい方 */
      const h2 = JSON.parse(JSON.stringify(helper)); h2.events[0].place = '第二体育館'; h2.events[0].hdrAt = later(200);
      K.mergePkg(h2); eq('日程の内容は新しい方', evN.place, '第二体育館');
      const h3 = JSON.parse(JSON.stringify(helper)); h3.events[0].place = '古い体育館'; h3.events[0].hdrAt = '2000-01-01T00:00:00.000Z';
      K.mergePkg(h3); eq('古い内容では上書きしない', evN.place, '第二体育館');
      /* 手伝いの人の空のスマホに渡す */
      const saved = {}; for (const k of ['sports','members','shops','events','extras']){ saved[k] = S[k]; S[k] = []; }
      const st3 = K.mergePkg(pkg);
      const got = S.events.find(e => e.id === 'e-next');
      ok('空のスマホに日程が入る', !!got && got.entries.length === evN.entries.length - 1);
      eq('受け取った日程には送り主が残る', got && got.origin && got.origin.from, '幹事');
      ok('種目とお店も一緒に入る', S.sports.length === 1 && S.shops.length === 1 && st3.added.events === 1);
      for (const k of Object.keys(saved)) S[k] = saved[k];
      /* 削除も伝わる */
      const h4 = JSON.parse(JSON.stringify(helper)); h4.events[0].deletedAt = later(300); h4.events[0].hdrAt = later(300);
      K.mergePkg(h4); ok('削除が伝わる', !!evN.deletedAt);
      evN.deletedAt = null; evN.hdrAt = later(400);
      /* バックアップで置き換え */
      const bk = K.buildBackup(), n = S.events.length;
      K.mergePkg(bk, { replace: true }); eq('バックアップで置き換え', S.events.length, n);
    }

    /* ================================================== 5. リンク・コードにする */
    {
      const pkg = K.buildPkg('handoff', ['e-next']);
      const code = await K.encodePkg(pkg);
      ok('圧縮したコードになる', code.startsWith('KN1z'), code.slice(0, 6));
      const back = await K.decodeAny(code);
      eq('コードから元に戻る', JSON.stringify(back), JSON.stringify(pkg));
      const msg = await K.buildHandoffText('handoff', ['e-next']);
      has('メッセージにリンクが入る', msg, '?openExternalBrowser=1#p=KN1');
      eq('メッセージ全体を貼っても読める', (await K.decodeAny('こんにちは\n' + msg + '\nよろしく')).events[0].id, 'e-next');
      ok('LINEで送れる長さ（1万文字未満）', msg.length < 10000, 'length=' + msg.length);
      eq('バックアップのファイル（JSON）も読める', (await K.decodeAny(JSON.stringify(K.buildBackup()))).kind, 'backup');
      await throwsAsync('関係ない文はエラー', () => K.decodeAny('こんにちは'), 'no-code');
      await throwsAsync('ほかのアプリのJSONはエラー', () => K.decodeAny('{"app":"other"}'), 'not-ours');
      await throwsAsync('壊れたコードはエラー', () => K.decodeAny('KN1zAAAAAAAAAAAAAAAA'));
      const sm = K.pkgSummary(pkg);
      eq('受け取り画面の要約', [sm.kind, sm.events.length, sm.events[0].yes, sm.events[0].exists], ['handoff', 1, K.summary(S.events.find(e => e.id === 'e-next')).yes, true]);
    }

    /* ================================================== 6. 保存（IndexedDB） */
    {
      await K.saveAll();
      const counts = ['sports','members','shops','events','extras'].map(k => S[k].length);
      for (const k of ['sports','members','shops','events','extras']) S[k] = [];
      await K.loadAll();
      eq('保存して読み直すと同じ件数', ['sports','members','shops','events','extras'].map(k => S[k].length), counts);
      eq('日程の中身も戻る', S.events.find(e => e.id === 'e-next').entries.length, 15);
    }

    /* ================================================== 7. 画面の操作（最初から） */
    for (const k of ['sports','members','shops','events','extras']) S[k] = [];
    S.settings = K.normSettings({}); await K.saveAll();
    await go('#/'); K.renderAll(); await sleep(30);
    ok('はじめての画面', !!$('.hero') && $('main').textContent.includes('幹事をしているスポーツは？'));
    noOverflow('はじめての画面');
    click($('[data-act="wPick"][data-v="バスケ"]')); await sleep(20);
    setVal($('[data-input="wFee"][data-k="バスケ"]'), '600');
    click($('[data-act="wSet"][data-k="バスケ"][data-f="menu"]')); await sleep(20);
    click($('[data-act="wSet"][data-k="バスケ"][data-f="tape"]')); await sleep(20);
    click($('[data-act="wStart"]')); await sleep(30);
    const sport = S.sports[0];
    eq('種目ができる（参加費・注文・名札）', [S.sports.length, sport && sport.tiers[0].amount, sport && sport.menu, sport && sport.tape], [1, 600, true, true]);
    ok('はじめの一歩が出る', $('main').textContent.includes('はじめの一歩'));

    K.ACT.memberBulk(); await sleep(20);
    setVal($('[data-input="mbText"]'), '田中 太郎\n佐藤 花子\n鈴木 一郎さん\n高橋 健');
    ok('まとめて登録: 人数がボタンに出る', $('#mbSaveBtn').textContent.includes('4人'));
    click($(`[data-act="mbFixed"][data-v="${sport.id}"]`)); await sleep(20);
    click($('#mbSaveBtn')); await sleep(80);
    eq('まとめて登録: 4人・★固定つき', [S.members.length, S.members.every(m => m.fixed.includes(sport.id)), S.members.some(m => m.name === '鈴木 一郎')], [4, true, true]);
    ok('シートが閉じる', K.stack.length === 0, 'stack=' + K.stack.length);

    K.ACT.newEvent({ dataset: {} }); await sleep(30);
    ok('日程の作成シートが開く', K.topSheet() && K.topSheet().name === 'eventEdit');
    noOverflow('日程の作成シート');
    const sat = K.nextWeekday(K.todayISO(), 6);
    click($(`[data-act="evDate"][data-v="${sat}"]`)); await sleep(20);
    eq('日付を選べる', K.topSheet().p.draft.date, sat);
    ok('注文と名札が種目の設定どおり', K.topSheet().p.draft.menu === true && K.topSheet().p.draft.tape === true);
    click($('.sheet-f [data-act="evSave"]')); await sleep(150);
    const ev = S.events[0];
    ok('日程ができる', S.events.length === 1 && ev.date === sat && ev.sportId === sport.id);
    eq('★固定メンバーが未回答で入る', ev && ev.entries.map(e => e.status), ['', '', '', '']);
    ok('日程の画面に移る', location.hash === '#/e/' + (ev && ev.id), location.hash);
    ok('シートは閉じている', K.stack.length === 0);
    noOverflow('参加者タブ');

    const firstSeg = () => $('.list .item .seg');
    click(firstSeg().querySelector('[data-v="yes"]')); await sleep(20);
    eq('「参加」を押すと参加になる', K.summary(ev).yes, 1);
    click($('[data-act="peopleFilter"][data-v="none"]')); await sleep(20);
    eq('未回答でしぼる', $$('.list .item').length, 3);
    click(firstSeg().querySelector('[data-v="maybe"]')); await sleep(20);
    eq('しぼりこみ中に変えた人は消えない', $$('.list .item').length, 3);
    click($('[data-act="peopleFilter"][data-v="all"]')); await sleep(20);
    eq('全員に戻す', $$('.list .item').length, 4);

    K.ACT.addPeople({ dataset: {} }); await sleep(30);
    setVal($('[data-input="apQ"]'), '山田 花子');
    ok('新しい名前は登録ボタンが出る', !!$('[data-act="apNew"]'));
    click($('[data-act="apNew"]')); await sleep(30);
    ok('新しく登録して参加で入る', S.members.length === 5 && K.entryOf(ev, S.members.find(m => m.name === '山田 花子').id).status === 'yes');
    setVal($('[data-input="apQ"]'), '田中');
    ok('探すと名前がしぼられる', $$('#apList .namegrid button').length === 1);
    noOverflow('人を追加');
    K.closeSheet(); await sleep(60);
    ok('戻るでシートが閉じる', K.stack.length === 0);

    const tanaka = S.members.find(m => m.name === '田中 太郎');
    K.ACT.person({ closest: () => ({ getAttribute: () => tanaka.id }) }); await sleep(30);
    ok('1人分のシートが開く', K.topSheet().name === 'person');
    click($('[data-act="pSt"][data-v="yes"]')); await sleep(20);
    click($('[data-act="pDin"][data-v="1"]')); await sleep(20);
    eq('ご飯「行く」', K.entryOf(ev, tanaka.id).dinner, true);
    click($('.sheet [data-act="numpad"]')); await sleep(30);
    ok('番号入力が重なって開く', K.topSheet().name === 'numpad' && K.stack.length === 2);
    noOverflow('番号入力');
    click($('[data-act="npKey"][data-v="1"]')); click($('[data-act="npKey"][data-v="2"]')); await sleep(20);
    eq('番号が入る', K.topSheet().p.no, '12');
    click($('[data-act="npQty"][data-v="1"]')); await sleep(20);
    click($('#npAddBtn')); await sleep(120);
    eq('注文が入る（12番×2）', K.entryOf(ev, tanaka.id).orders, [{ no: '12', qty: 2 }]);
    ok('番号入力を閉じると1人分のシートに戻る', K.stack.length === 1 && K.topSheet().name === 'person', 'stack=' + K.stack.map(x => x.name).join(','));
    click($('[data-act="pQty"][data-no="12"][data-v="-1"]')); await sleep(20);
    eq('個数を減らせる', K.entryOf(ev, tanaka.id).orders[0].qty, 1);
    click($('[data-act="pPay"][data-g="pay"]')); await sleep(20);
    ok('参加費を受け取りにできる', K.entryOf(ev, tanaka.id).paid === true && K.entryOf(ev, tanaka.id).payMethod === '現金');
    setVal($('[data-change="pMemo"]'), '遅れて来る', 'change'); await sleep(30);
    eq('メモが残る', K.entryOf(ev, tanaka.id).memo, '遅れて来る');
    noOverflow('1人分のシート');
    history.back(); await sleep(120);
    ok('ブラウザの戻るでシートが閉じる', K.stack.length === 0, 'stack=' + K.stack.length);
    ok('閉じても日程の画面のまま', location.hash === '#/e/' + ev.id, location.hash);

    await go(`#/e/${ev.id}/dinner`);
    ok('ご飯タブ', ($('.etabs a[aria-current="page"]') || {}).textContent.includes('ご飯'));
    ok('注文が行に出る', $('main').textContent.includes('12番'));
    noOverflow('ご飯タブ');
    K.ACT.text({ dataset: { kind: 'shop' } }); await sleep(30);
    has('お店に送る文が作られる', $('textarea.msg').value, '12番 ×1');
    noOverflow('お店に送る文');
    click($('[data-act="markSent"]')); await sleep(120);
    ok('お店に伝えた印', !!ev.sent && $('main').textContent.includes('お店へ伝えました'));
    const sato = S.members.find(m => m.name === '佐藤 花子');
    const se = K.entryOf(ev, sato.id); K.setEntry(ev, se, 'status', { status: 'yes' }); K.setEntry(ev, se, 'dinner', { dinner: true });
    K.setEntry(ev, se, 'orders', { orders: [{ no: '3', qty: 1 }] }); K.renderAll(); await sleep(20);
    ok('伝えたあとの変更を知らせる', $('main').textContent.includes('内容が変わっています'));

    await go(`#/e/${ev.id}/money`);
    const pays = $$('main .pay[data-g="pay"]');
    ok('集金タブに参加者の分のボタン', pays.length === K.summary(ev).feePeople, `${pays.length} vs ${K.summary(ev).feePeople}`);
    click($('main .pay[data-g="pay"][aria-pressed="false"]')); await sleep(20);
    eq('押すと受取済になる', K.summary(ev).feePaid, 2);
    click($('[data-act="dfMode"][data-v="split"]')); await sleep(20);
    setVal($('[data-change="dfTotal"]'), '5000', 'change'); await sleep(40);
    eq('割り勘の合計を入れる', ev.dinnerFee.total, 5000);
    eq('割り勘で1人2500円', K.summary(ev).dDue, 5000);
    noOverflow('集金タブ');

    await go(`#/e/${ev.id}/tape`);
    eq('名札タブに参加の人', $$('main .tape').length, K.summary(ev).yes);
    click($('main [data-act="tape"]')); await sleep(20);
    eq('「作った」を押す', K.summary(ev).tapeDone, 1);
    K.ACT.tapeName({ closest: () => ({ getAttribute: () => tanaka.id }) }); await sleep(30);
    setVal($('[data-input="tapeVal"]'), 'タロ');
    eq('名札の見本が変わる', $('#tapePrev').textContent, 'タロ');
    click($('.sheet-f [data-act="tapeSave"]')); await sleep(120);
    eq('名札の名前が残る', tanaka.tape, 'タロ');
    noOverflow('名札タブ');

    /* 受け渡し: 自分に送って受け取る（何も変わらない） */
    K.ACT.handoff({ dataset: { kind: 'handoff', id: ev.id } }); await sleep(250);
    const hoText = K.topSheet().p.text;
    has('受け渡しのメッセージができる', hoText, '#p=KN1');
    noOverflow('受け渡し');
    K.closeSheet(); await sleep(80);
    await K.receiveCode(hoText); await sleep(30);
    ok('受け取りの確認が出る', K.topSheet() && K.topSheet().name === 'importPreview');
    click($('[data-act="impDo"]')); await sleep(80);
    has('受け取り結果', $('.sheet').textContent, 'すでに最新');
    K.closeSheet(); await sleep(80);

    /* 予定の画面・カレンダー */
    await go('#/');
    ok('予定に日程が出る', $$('main .ev').length === 1);
    click($('[data-act="homeMode"][data-v="cal"]')); await sleep(20);
    ok('カレンダーが出る', !!$('.cal'));
    click($(`[data-act="calDay"][data-date="${ev.date}"]`)); await sleep(20);
    ok('日付を押すとその日の予定', $$('main .ev').length === 1);
    noOverflow('カレンダー');
    click($('[data-act="calMove"][data-v="1"]')); await sleep(20);
    ok('次の月へ', !$('[aria-pressed="true"].day'));
    click($('[data-act="homeMode"][data-v="list"]')); await sleep(20);

    /* ほかの画面 */
    await go('#/members');
    setVal($('[data-input="memberQ"]'), '佐藤');
    eq('メンバーを探す', $$('#memberList .linkrow').length, 1);
    setVal($('[data-input="memberQ"]'), '');
    noOverflow('メンバー');
    await go('#/money'); ok('お金の画面', $('main').textContent.includes('手元にあるはずのお金')); noOverflow('お金');
    await go('#/data');
    ok('データの画面に手順', $$('main .steps li').length >= 10 && $('main').textContent.includes('貼り付けて受け取る'));
    noOverflow('データ');
    await go('#/settings'); noOverflow('設定');
    click($('[data-act="prefFont"][data-v="xl"]')); await sleep(20);
    eq('文字を大きくできる', document.documentElement.dataset.font, 'xl');
    await go(`#/e/${ev.id}`); noOverflow('文字が大きい参加者タブ');
    await go('#/settings');
    click($('[data-act="prefTheme"][data-v="dark"]')); await sleep(20);
    eq('暗い画面', getComputedStyle(document.body).backgroundColor, 'rgb(0, 0, 0)');
    click($('[data-act="prefTheme"][data-v="auto"]')); click($('[data-act="prefFont"][data-v="m"]')); await sleep(20);

    /* 削除と元に戻す */
    await go(`#/e/${ev.id}`);
    K.ACT.deleteEvent(); await sleep(60);
    ok('日程を削除', !!ev.deletedAt && location.hash === '#/');
    click($('#toast [data-act="toastAct"]')); await sleep(80);
    ok('元に戻す', !ev.deletedAt && location.hash === '#/e/' + ev.id);

    /* 保存されているか（DBから読み直す） */
    await sleep(100);
    const evId = ev.id;
    for (const k of ['sports','members','shops','events','extras']) S[k] = [];
    await K.loadAll();
    const ev2b = S.events.find(e => e.id === evId);
    ok('操作した内容がDBに残っている', !!ev2b && K.entryOf(ev2b, tanaka.id).orders[0].no === '12' && K.entryOf(ev2b, tanaka.id).paid && ev2b.dinnerFee.total === 5000);
    ok('名札の名前もDBに残っている', S.members.find(m => m.id === tanaka.id).tape === 'タロ');

    ok('画面の操作中にエラーが出ていない', errors.length === 0, errors.join(' / '));
  } catch (e) {
    fail++; out.push('FAIL  例外: ' + (e && e.stack || e));
  } finally {
    window.confirm = origConfirm;
  }
  const div = document.createElement('div'); div.id = 'selftest-out';
  div.textContent = `${fail ? 'FAILED' : 'ALL PASSED'}  pass=${pass} fail=${fail}\n` + out.join('\n');
  document.body.appendChild(div);
  document.title = `SELFTEST ${fail ? 'FAIL' : 'PASS'} ${pass}/${pass + fail}` + (fail ? ' :: ' + out.filter(l => l.startsWith('FAIL')).map(l => l.slice(6)).join(' || ') : '');
})();

# 一次ふるい(screen.json)から候補を絞り、取得対象リストと候補ごとの資料を出す
#   python3 pick.py lists     # shortlist.json（食べログ評価分布の取得対象）/ hp_targets.json（ホットペッパー詳細の取得対象）
#   python3 pick.py dossier   # 候補ごとの資料（紹介文を書くための材料）→ dossier.txt
import json, sys, os, re, collections

TB_MIN = 3.30        # 食べログのボーダー（ユーザー指定 2026-09-15。母集団での位置は stats で出す）
RV_MIN = 50

def load(p, default=None):
    return json.load(open(p)) if os.path.exists(p) else default

def shortlist():
    sc = load('screen.json'); jn = {j['tb_id']: j for j in load('join.json', [])}
    extra = load('join_extra.json', {})          # hp_find.py が店名検索で拾った分
    sl = [x for x in sc if x['score'] >= TB_MIN and x['reviews'] >= RV_MIN]
    for x in sl: x['hp_id'] = (jn.get(x['id']) or {}).get('hp_id') or extra.get(x['id'])
    return sl

def stats():
    """ボーダーの根拠: 掃引した母集団（個室あり／貸切可 × 夜¥2,000〜5,999）での評点の分布"""
    d = load('tabelog_all.json'); R = d['rows']; T = d['totals']; out = {}
    for area in ('shibuya', 'shinjuku'):
        for fk in ('room', 'charter'):
            tot = T[f'{area}_{fk}']
            rs = [r for r in R if r['area'] == area and fk in r['found_by']]
            out[f'{area}_{fk}'] = dict(total=tot, **{f'ge{th}': round(sum(1 for r in rs if (r['score'] or 0) >= th) / tot * 100, 1)
                                                    for th in (3.3, 3.35, 3.4, 3.45, 3.5)})
    return out

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'lists'
    if cmd == 'lists':
        sl = shortlist()
        json.dump([dict(id=x['id'], url=x['url']) for x in sl], open('shortlist.json', 'w'), ensure_ascii=False)
        json.dump(sorted({x['hp_id'] for x in sl if x['hp_id']}), open('hp_targets.json', 'w'))
        print('shortlist', len(sl), 'hp matched', sum(1 for x in sl if x['hp_id']))
        print(collections.Counter((x['area'], x['room']['kind'] if x['room'] else '貸切') for x in sl))
        print(json.dumps(stats(), ensure_ascii=False, indent=1))
    elif cmd == 'rank':
        # 掲載候補の下書き順。紹介文を書く前に機械で並べ、最終の取捨は content.py で人が決める
        from build import eligible_courses, cospa
        from screen import NOISY, CALM
        sl = shortlist(); det = {d['id']: d for d in load('tabelog_detail.json')}
        hps = load('hpg_store.json', {}); neg = load('tabelog_neg.json', {}); av = load('hpg_avail.json', {}).get('avail', {})
        rows = []
        for x in sl:
            H = hps.get(x['hp_id'] or '', {}); cs = eligible_courses(H); c = cs[0] if cs else None
            if c and c['price'] > 5000: continue                                   # 予算オーバー
            if not c and x['budget'] == '￥4,000～￥4,999': pass                     # 価格不明は残すが減点
            nd = neg.get(x['id'], {}); tot = sum(nd.values()) or 1
            low = sum(v for k, v in nd.items() if float(k) <= 2.5) / tot
            texts = list(det[x['id']].get('sample_reviews') or []) + [r['text'] for r in H.get('report', {}).get('reviews', [])]
            nz = sum(1 for t in texts if any(w in t for w in NOISY))
            g = cospa(c)['grade']
            pts = ((x['score'] - 3.30) * 20                     # 3.30→0, 3.50→4
                   + g * 1.5 + (1.5 if x['calm_space'] else 0)
                   + (1.0 if x['room'] and x['room'].get('exact') else 0)
                   + (1.0 if av.get(x['hp_id'] or '') else 0)
                   - nz * 1.5 - (2 if x['service_pct'] else 0) - (1 if x['sunday'] is None else 0)
                   - (2 if x['room'] and x['room']['kind'] == '個室(大)' else 0) - max(0, low - 0.08) * 30)
            rows.append((round(pts, 2), x, c, g, nz, low))
        rows.sort(key=lambda r: -r[0])
        for area in ('shibuya', 'shinjuku'):
            print('==', area)
            for pts, x, c, g, nz, low in [r for r in rows if r[1]['area'] == area][:30]:
                sp = (x['room'] or {}).get('label') or (x['charter'] or {}).get('label')
                print(f"  {pts:5.2f} {x['id']} {x['score']:.2f} {'◎○△'[3-g]} {(str(c['price'])+'円') if c else '----':>6} 騒{nz} 低{low*100:3.0f}% {x['name'][:24]:<26} {x['genre'][:14]:<16} {sp}")
        json.dump([dict(id=r[1]['id'], pts=r[0]) for r in rows], open('rank.json', 'w'))
    elif cmd == 'dossier':
        sl = shortlist(); det = {d['id']: d for d in load('tabelog_detail.json')}
        hps = load('hpg_store.json', {}); neg = load('tabelog_neg.json', {}); av = load('hpg_avail.json', {}).get('avail', {})
        lines = []
        for x in sorted(sl, key=lambda x: (x['area'], -x['score'])):
            d = det[x['id']]; t = d['tbl']; H = hps.get(x['hp_id'] or '', {}); I = H.get('info', {})
            cs = [c for c in H.get('courses', []) if c['nomi'] and not c['nomi_only']]
            nd = neg.get(x['id'], {}); tot = sum(nd.values()) or 1
            low = sum(v for k, v in nd.items() if float(k) <= 2.5)
            rep = H.get('report', {})
            lines += [f"■ {x['id']} {x['name']} [{x['area']}] 食べログ{x['score']}({x['reviews']}) HP{rep.get('score')}({rep.get('calc_n')}) hp={x['hp_id']} 空き={av.get(x['hp_id'] or '', [])}",
                      f"  ジャンル: {x['genre']} ／ 予算: {x['budget']} ／ {d.get('station','')} {d.get('dist_m','')}m",
                      f"  部屋: {x['room']} ／ {x['charter']} ／ 最大予約{x['maxseat']} ／ 落ち着いた空間={x['calm_space']} 騒言及={x['noisy_hits']} 静言及={x['calm_hits']}",
                      f"  個室欄: {t.get('個室','')[:160]}",
                      f"  席数: {t.get('席数','')[:80]} ／ 空間: {t.get('空間・設備','')[:90]}",
                      f"  営業: {t.get('営業時間','')[:170]}",
                      f"  料金: サービス料{x['service_pct']}% {x['charge_text'][:80]}",
                      f"  HP: 収容{I.get('最大宴会収容人数','')[:60]} ／ 個室{I.get('個室','')[:80]} ／ 予約{I.get('ネット予約受付時間','')[:30]}",
                      f"  コース: " + ' | '.join(f"{c['price']}円 {c['people']} {c['name'][:48]}" for c in sorted(cs, key=lambda c: c['price'])[:6]),
                      f"  低評価(2.5以下): {low}/{tot}  ",
                      "  食べログ口コミ: " + ' ／ '.join(r[:160].replace('\n', ' ') for r in (d.get('sample_reviews') or [])[:3]),
                      "  HP口コミ: " + ' ／ '.join(f"[{r['scene']}]{r['text'][:110]}" for r in rep.get('reviews', [])[:4]),
                      ""]
        open('dossier.txt', 'w').write('\n'.join(lines))
        print('dossier', len(sl), 'shops →', 'dossier.txt')

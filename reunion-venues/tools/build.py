# -*- coding: utf-8 -*-
# 掲載する店（content.py の FINAL）と取得データから data.json / data.js を書き出す
import json, re, math, os, urllib.parse, datetime, collections
from screen import room_for, charter_for, DAYTOK, has_sun, NOISY, CALM
from pick import stats, TB_MIN, RV_MIN

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIONS = {'shibuya': dict(name='渋谷駅', lat=35.658034, lon=139.701636),
            'shinjuku': dict(name='新宿駅', lat=35.690921, lon=139.700258)}
N = 15
CAP = 5000            # 飲み放題付きコースの上限（1人・税込）
DATE_LABEL = '2026年9月15日'

def hav(a, b, c, d):
    R = 6371000.0; p1, p2 = math.radians(a), math.radians(c)
    x = math.sin(math.radians(c-a)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(math.radians(d-b)/2)**2
    return 2*R*math.asin(math.sqrt(x))

def people_ok(p):
    """コースの利用人数「2～30名」「2名～」が15名を含むか"""
    m = re.search(r'(\d+)\s*[～~]\s*(\d+)\s*名', p or '')
    if m: return int(m.group(1)) <= N <= int(m.group(2))
    m = re.search(r'(\d+)\s*名\s*[～~]', p or '')
    return int(m.group(1)) <= N if m else True

def eligible_courses(H):
    out = []
    for c in H.get('courses', []):
        nm = c['name']
        if not c['nomi'] or c['nomi_only'] or c['price'] < 2500: continue
        if ('プラン' in nm and 'コース' not in nm) or '単品' in nm: continue     # 飲み放題だけのプラン
        # 開催日（日曜）に使えない。「日～木限定」は日曜を含むので残す（お茶づけバーZUZU 4,000円）
        if re.search(r'平日(限定|のみ)|月～木|月-木|月～金|金土祝前日?限定|日曜不可', nm): continue
        # 昼だけ・遅い時間スタートだけの割安コースは夜の同窓会に使えない
        # （ごだいご「昼宴会個室 3,000円」、23番地「20:30～ 激得 3,500円」が最安に出ていた）
        if re.search(r'昼宴会|昼の部|昼飲み|ランチ|昼限定|[12]\d[:：]\d{2}\s*[～~]|[12]\d時\s*[～~]|\d{1,2}[:：]\d{2}まで|深夜|早割'
                     r'|\d{1,2}時以降|\d{1,2}[:：]\d{2}以降|二次会|２次会|2次会', nm): continue    # ZUZU「21時以降限定 3,000円」など
        if not people_ok(c['people']): continue
        out.append(c)
    return sorted(out, key=lambda c: c['price'])

def course_facts(name):
    h = re.search(r'(\d(?:\.\d)?)\s*(?:時間|[Hh](?![a-z]))', name)
    m = re.search(r'(\d{2,3})\s*分', name)
    hours = float(h.group(1)) if h else (int(m.group(1))/60 if m else None)
    d = re.search(r'(\d{1,2})\s*品', name)
    return hours, (int(d.group(1)) if d else None)

def cospa(c):
    """コスパの目安。飲み放題付きコースの価格と飲み放題の時間で決める（基準はフッターに明記）"""
    if not c: return dict(grade=1, note='サイトにコース価格が無いので、予約時に予算を伝えて相談')
    hours, dishes = course_facts(c['name']); p = c['price']
    parts = ([f'{hours:g}時間飲み放題'] if hours else ['飲み放題付き']) + ([f'{dishes}品'] if dishes else [])
    note = '・'.join(parts) + f'で{p:,}円'
    if p <= 3500 or (p <= 4000 and (hours or 0) >= 2.5): g = 3
    elif p <= 4500: g = 2
    else: g = 1
    return dict(grade=g, note=note)

def sunday_hours(t):
    first = (t.get('営業時間') or '').split('■')[0]
    toks = list(re.finditer(DAYTOK + r'(?=\s*\d{1,2}:\d{2})', first))
    for i, m in enumerate(toks):
        if has_sun(m.group(1)):
            seg = first[m.end(): toks[i+1].start() if i+1 < len(toks) else len(first)]
            return (m.group(1) + ' ' + re.sub(r'\s+', ' ', seg)).strip()[:80]
    return re.sub(r'\s+', ' ', first).strip()[:80]

if __name__ == '__main__':
    from content import FINAL, GENRES      # pick.py rank から eligible_courses/cospa だけ使えるよう、ここで読む
    det = {d['id']: d for d in json.load(open('tabelog_detail.json'))}
    scr = {x['id']: x for x in json.load(open('screen.json'))}
    jn = {j['tb_id']: j for j in json.load(open('join.json'))}
    extra = json.load(open('join_extra.json')) if os.path.exists('join_extra.json') else {}
    for tid, hid in extra.items():
        if not (jn.get(tid) or {}).get('hp_id'): jn[tid] = dict(tb_id=tid, hp_id=hid)
    hps = json.load(open('hpg_store.json'))
    neg = json.load(open('tabelog_neg.json'))
    av = json.load(open('hpg_avail.json'))['avail']
    GK = {k: label for k, label in GENRES}

    shops = []
    for rank, (tid, gkey, C) in enumerate(FINAL):
        d = det[tid]; t = d['tbl']; S = scr[tid]
        assert d['score'] >= TB_MIN and d['reviews'] >= RV_MIN, f"{d['name']}: 食べログ基準を満たさない"
        hid = C.get('hp_id', (jn.get(tid) or {}).get('hp_id'))
        H = hps.get(hid or '', {}); I = H.get('info', {}); R = H.get('report', {})
        area = d['area']; st = STATIONS[area]
        dist = int(d['dist_m']) if d.get('dist_m') else round(hav(st['lat'], st['lon'], d['lat'], d['lon']))

        room = room_for(N, t); ch = charter_for(N, t)
        if C.get('space') == 'charter' or not room:
            room_kind, space_label = 'charter', C.get('space_label') or (ch or {}).get('label', '貸切')
        else:
            room_kind, space_label = 'room', C.get('space_label') or room['label']

        cs = eligible_courses(H)
        cheapest = cs[0] if cs else None
        if C.get('course_min'): cheapest = dict(price=C['course_min'], name=C.get('course_name', ''))
        assert not cheapest or cheapest['price'] <= CAP, f"{d['name']}: 飲み放題付きコースが{CAP}円を超える"

        net = I.get('ネット予約受付時間', '')
        can_net = net.startswith('即予約') or net.startswith('リクエスト')

        nd = neg.get(tid, {}); tot = sum(nd.values())
        low = sum(v for k, v in nd.items() if float(k) <= 2.5)
        texts = list(d.get('sample_reviews') or []) + [r['text'] for r in R.get('reviews', [])]
        nz = sum(1 for x in texts if any(w in x for w in NOISY)); cm = sum(1 for x in texts if any(w in x for w in CALM))
        review_text = ((f'食べログで2.5点以下をつけた人 {low/tot*100:.0f}%（{tot}人中）。' if tot else '') +
                       f'口コミ抜粋{len(texts)}件のうち「落ち着く・静か」系{cm}件／「うるさい」系{nz}件')

        shops.append(dict(
            id=tid, rank=rank, name=d['name'], area=area, genre_label=GK[gkey],
            lat=d['lat'], lon=d['lon'], station=d.get('station') or st['name'], walk_min=max(1, math.ceil(dist/80)),
            tabelog=dict(score=d['score'], reviews=d['reviews'], url=d['url']),
            hotpepper=(dict(score=R.get('score'), n=R.get('calc_n'), url=f'https://www.hotpepper.jp/{hid}/') if hid else None),
            gnavi=C.get('gnavi', ''),
            gmap='https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(d['name'] + ' ' + (d.get('addr') or '')),
            book_url=(f'https://www.hotpepper.jp/{hid}/' if hid and can_net else ''),
            room_kind=room_kind, space_label=space_label,
            course_min=cheapest['price'] if cheapest else None, cospa=cospa(cheapest),
            budget_text=d['budget_dinner'].replace('～', '〜'),
            slot=sorted(av.get(hid or '', [])), service_pct=S['service_pct'],
            reasons=C['reasons'], caution=C.get('caution', ''),
            room_text=(t.get('個室') or '')[:140], charter_text=(t.get('貸切') or '')[:80],
            course_text=' ／ '.join(f"{c['price']:,}円 {c['name'][:44]}" for c in cs[:3]),
            sunday_hours=sunday_hours(t), charge_text=S['charge_text'] if S['service_pct'] or 'チャージ' in S['charge_text'] else '',
            review_text=review_text, tel=d.get('tel') or '',
        ))

    ids = [s['id'] for s in shops]; assert len(ids) == len(set(ids)), '重複あり'
    ST = stats(); k = f'ge{TB_MIN:g}'
    n_slot = sum(1 for s in shops if s['slot'])
    # 掲載15軒はすべて個室（うち半個室・要確認が各1）。貸切だけの店は残らなかったので、上部の条件表示も個室に合わせる
    rules = [f'食べログ {TB_MIN:.2f}以上', '15名で入れる個室', '飲み放題付き 1人5,000円まで', '日曜の夜も営業', 'にぎやか過ぎる業態は除外']
    foot = f'''<h2>載せている店の条件</h2>
<ul>
<li>食べログ <b>{TB_MIN:.2f}以上・口コミ{RV_MIN}件以上</b>（個室あり／貸切可・夜¥2,000〜5,999の店のうち、渋谷で上位{max(ST['shibuya_room'][k], ST['shibuya_charter'][k])}%以内、新宿で上位{max(ST['shinjuku_room'][k], ST['shinjuku_charter'][k])}%以内）</li>
<li>15名が入る個室がある、または20名以下で貸切にできる</li>
<li>日曜も21時以降まで営業。立ち飲み・大衆酒場・ライブ演奏・スポーツ観戦の店、バー・カフェは除外</li>
<li>飲み放題付きコースが1人5,000円まで（コース価格がサイトに無い店は、夜の予算が5,000円未満）</li>
</ul>
<h2>コスパの目安</h2>
<ul>
<li><b>◎</b> 飲み放題付きコースが3,500円以下、または4,000円以下で飲み放題2.5時間以上</li>
<li><b>○</b> 4,500円以下　<b>△</b> 5,000円まで、またはコース価格がサイトに無い</li>
</ul>
<h2>見るときの注意</h2>
<ul>
<li>「空き枠」はホットペッパーで10/25に15名の予約フォームが開くという意味で、個室が取れるとは限らない（{n_slot}軒）。個室希望は予約時に伝える</li>
<li>評点・コース・営業時間は{DATE_LABEL}時点。徒歩分数は食べログ記載の距離÷80m</li>
<li>楽天ぐるなびは店のページに点数・口コミ件数が出ないため、基準には使っていない</li>
</ul>
<p>集め方の詳細は<a href="https://github.com/ko-yamatoya/Projects/tree/main/reunion-venues#readme" target="_blank" rel="noopener">README</a>。
地図 &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors</p>'''

    data = dict(generated=datetime.date.today().isoformat(), stations=list(STATIONS.values()),
                rules=rules, shops=shops, footer_html=foot)
    json.dump(data, open(os.path.join(OUT, 'data.json'), 'w'), ensure_ascii=False, indent=1)
    open(os.path.join(OUT, 'data.js'), 'w', encoding='utf-8').write(
        '/* 生成物: tools/build.py が作る。編集しない */\nwindow.__DATA__ = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print('shops', len(shops), 'slot', n_slot, 'area', collections.Counter(s['area'] for s in shops))
    print('room', collections.Counter(s['room_kind'] for s in shops), 'cospa', collections.Counter(s['cospa']['grade'] for s in shops))

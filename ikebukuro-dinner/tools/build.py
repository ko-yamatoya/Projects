# -*- coding: utf-8 -*-
import json, re, math, urllib.parse, datetime, os
from final_list import FINAL
from content import CONTENT

OUT = os.path.expanduser('~/Projects/ikebukuro-dinner')
STA = (35.72953, 139.71107)                      # JR池袋駅
GENRES = [
  ("izakaya","大衆居酒屋","酒"), ("private","個室・宴会向け","個"),
  ("yakitori","焼き鳥・もつ焼き","鳥"), ("seafood","海鮮・魚介","魚"),
  ("yakiniku","焼肉・ホルモン","肉"), ("chinese","中華・点心","中"),
  ("korean","韓国料理","韓"), ("ethnic","エスニック","亜"),
  ("bal","バル・イタリアン","伊"), ("beer","ビア・ワイン","杯"), ("nabe","そば・鍋","鍋"),
]
GKEY = {lab:(k,gl) for k,lab,gl in GENRES}
# 地図の「ジャンルで色分け」用の系統。4色に抑えているのは、全ペア検証で5色以上だと
# 通常視の識別下限(ΔE15)を割るため（tools/valpal.py）。文字（漢字）が識別の主役で、色は補助。
# 明るい地図面(#f2efe9)に対して4色とも3.4:1以上、全ペアの通常視の色差16.3。
GROUPS = [
  ("wa",   "和・酒場", "#e34948", "#ffffff", ["izakaya","private","yakitori","nabe"]),
  ("niku", "肉",       "#4a3aa7", "#ffffff", ["yakiniku"]),
  ("sakana","魚",      "#2a78d6", "#ffffff", ["seafood"]),
  ("world","世界の料理","#008300", "#ffffff", ["chinese","korean","ethnic","bal","beer"]),
]
GRP = {g:(k,c,i) for k,_,c,i,ks in GROUPS for g in ks}

def hav(a,b,c,d):
    R=6371000.0
    p1,p2=math.radians(a),math.radians(c)
    dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

cand = {x['name']:x for x in json.load(open('candidates4.json'))}
det  = {r['id']:r for r in json.load(open('tabelog_detail.json'))}
hps  = json.load(open('hpg_store.json'))
hpr  = json.load(open('hpg_reports.json'))
hpc  = json.load(open('hpg_courses.json'))
neg  = json.load(open('tabelog_neg.json'))
hidx = {h['id']:h for h in json.load(open('hpg_index.json'))}

def exit_of(x, d):
    acc = (d['tbl'].get('交通手段') or '') + ' ' + (d.get('addr') or '')
    hi = hidx.get(x.get('hp_id') or '') or {}
    hg = hi.get('genre','')
    hits=[(acc.find(e), e) for e in ('西口','北口','東口','南口') if e in acc]
    if hits:
        e=min(hits)[1]
        return '東口' if e=='南口' else e
    if '池袋西口' in hg: return '西口'
    if '池袋北口' in hg: return '北口'
    if '池袋東口' in hg or '南池袋' in hg or '東池袋' in hg: return '東口'
    a = d.get('addr') or ''
    if a.startswith('西池袋'): return '西口'
    if a.startswith('南池袋') or a.startswith('東池袋'): return '東口'
    if a.startswith('池袋'): return '北口'
    lon = d.get('lon') or STA[1]
    return '西口' if lon < STA[1] else '東口'

def band(bd):
    m = re.search(r'￥([\d,]+)', bd or '')
    if not m: return "3000"
    v = int(m.group(1).replace(',',''))
    return str(min(5000, max(2000, (v//1000)*1000)))

def closed_of(hours):
    m = re.search(r'(?:定休日[:：]?\s*)([^■]{1,40})', hours or '')
    if m: return m.group(1).strip()[:40]
    m = re.search(r'([^\s]{1,12})\s*定休日', hours or '')
    return (m.group(1)+' 定休') if m else ''

shops=[]
for name, blabel, glyph in FINAL:
    x=cand[name]; d=det[x['id']]; t=d['tbl']; C=CONTENT[name]
    hid=x.get('hp_id'); H=hps.get(hid or '') or {}; HI=H.get('info') or {}
    R=hpr.get(hid or '') or {}; N=neg[x['id']]
    lat,lon = d.get('lat'), d.get('lon')
    dist = round(hav(STA[0],STA[1],lat,lon))
    gkey,_ = GKEY[blabel]

    # 個室
    # 個室は食べログの構造化された記述を正とする（人数が入っているため）。
    # ホットペッパー側の「あり」は15名〜のフロア貸切を指すことがあり、4人には使えないので採らない。
    room=''; room4=False
    tb_room=(t.get('個室') or '')
    hp_room=(HI.get('個室') or '')
    if tb_room.startswith('有'):
        room=re.sub(r'^有\s*','',tb_room).strip()[:46] or 'あり'
    elif '半個室' in tb_room:
        m=re.search(r'半個室[^。]{0,26}', tb_room); room=(m.group(0) if m else '半個室あり')[:34]
    elif '半個室' in hp_room:
        m=re.search(r'半個室[^。]{0,26}', hp_room); room=(m.group(0) if m else '半個室あり')[:34]
    # 4人で使えるか。10名〜しか無い個室は4人では通らないので「個室あり」に数えない
    if room:
        small = any(k in room for k in ('半個室','2人可','4人可','5名','4名','6人可','8人可','2名'))
        room4 = small or not re.search(r'\d+\s*[～~]\s*\d+人可|\d+人以上可', room)

    # 飲み放題
    nomi=''; nomi_ok=None
    cs=[c for c in (hpc.get(hid or '') or []) if c['nomi']]
    if cs:
        cs.sort(key=lambda c:c['price'])
        lo,hi=cs[0]['price'],cs[-1]['price']
        nomi = ('飲み放題付きコース %s円' % f'{lo:,}') + ('' if lo==hi else '〜%s円'%f'{hi:,}')
        nomi += '（%s）' % ('予算内' if lo<=6000 else '上限6,000円を超える')
    elif HI.get('飲み放題','').startswith('あり'): nomi='あり（価格は店に確認）'
    elif HI.get('飲み放題','').startswith('なし'): nomi=''
    elif '飲み放題' in (t.get('ドリンク') or '')+(t.get('コース') or ''): nomi='あり（価格は情報なし）'

    # 予約の入口。ホットペッパーの「ネット予約受付時間」の書き出しが即予約かリクエストかを示す。
    # 想定利用（金曜19時・4名）でネットに空き枠が出るかは avail_map.json で別途確認済み（内部確認のみ）。
    rsv=(t.get('予約可否') or '')
    net=(HI.get('ネット予約受付時間') or '')
    instant = net.startswith('即予約')
    if instant:                      rkind='ネット即予約'
    elif net.startswith('リクエスト'): rkind='ネット予約（リクエスト）'
    elif '電話予約のみ' in rsv:        rkind='電話予約のみ'
    else:                            rkind='電話予約'
    if hid:
        rurl='https://www.hotpepper.jp/%s/'%hid; rsite='ホットペッパー'
    else:
        rurl=x['url']; rsite='食べログ'
    rnote=re.sub(r'^予約可\s*','',rsv)[:90] or '予約可'

    # 口コミ
    vm=N.get('visit_months') or []
    latest=max(vm) if vm else ''
    dist_tb=N.get('dist') or {}
    tot=sum(dist_tb.values()) or 1
    low=sum(v for k,v in dist_tb.items() if k.startswith(('2.','1.')))
    lowtxt='食べログ2点台以下 %.1f%%（%d/%d件）'%(low/tot*100, low, tot)
    if R.get('dist'):
        rd=R['dist']; rt=sum(rd.values()) or 1
        lowtxt+=' ／ ホットペッパー★1〜2 %.0f%%（%d/%d件）'%((rd.get('1',0)+rd.get('2',0)+rd.get(1,0)+rd.get(2,0))/rt*100,
                                                        rd.get('1',0)+rd.get('2',0)+rd.get(1,0)+rd.get(2,0), rt)
    srcs=['食べログ']+(['ホットペッパーグルメ'] if (R.get('score') or HI) else [])

    hours=(t.get('営業時間') or '')[:150]
    shops.append(dict(
        id=x['id'], name=name, kana='',
        genre=gkey, genre_label=blabel, glyph=glyph, group=GRP[gkey][0],
        lat=lat, lon=lon, dist_m=dist, walk_min=max(1,math.ceil(dist/80)),
        exit=exit_of(x,d), cuisine=x['genres'],
        budget_band=band(x['budget_dinner']),
        tabelog=dict(score=x['score'], reviews=x['reviews'], url=x['url']),
        hotpepper=(dict(score=R['score'], n=R['calc_n'], url='https://www.hotpepper.jp/%s/'%hid)
                   if R.get('score') else None),
        private_room=room, room4=room4, nomihodai=nomi,
        seats=(t.get('席数') or '情報なし')[:70], seats_note=C['seat'],
        signature=C['sig'], comment=C['cmt'],
        reserve_url=rurl, reserve_site=rsite, reserve_kind=rkind, instant=instant, reserve_note=rnote,
        tel=d.get('tel') or '', hours=hours, closed=closed_of(hours),
        low_ratio_text=lowtxt, latest_review=(latest+'（口コミの訪問月）') if latest else '情報なし',
        sources=srcs,
        gmap='https://www.google.com/maps/search/?api=1&query='+urllib.parse.quote(name+' 池袋'),
    ))

today=datetime.date.today().isoformat()
FOOT = open('footer.html',encoding='utf-8').read()
data=dict(generated=today, station='JR池袋駅',
          genres=[dict(key=k,label=l,glyph=g) for k,l,g in GENRES],
          groups=[dict(key=k,label=l,color=c,ink=i) for k,l,c,i,_ in GROUPS],
          shops=shops, footer_html=FOOT)
json.dump(data, open(os.path.join(OUT,'data.json'),'w'), ensure_ascii=False, indent=1)
open(os.path.join(OUT,'data.js'),'w',encoding='utf-8').write(
    '/* 生成物: build.py が data.json から作る。編集しない */\nwindow.__DATA__ = '
    + json.dumps(data, ensure_ascii=False, separators=(',',':')) + ';\n')
print('shops',len(shops))
from collections import Counter
print('genre ',Counter(s['genre_label'] for s in shops))
print('budget',Counter(s['budget_band'] for s in shops))
print('exit  ',Counter(s['exit'] for s in shops))
print('個室   ',sum(1 for s in shops if s['private_room']),' 飲放',sum(1 for s in shops if s['nomihodai']))
print('walk max',max(s['walk_min'] for s in shops),'dist max',max(s['dist_m'] for s in shops))

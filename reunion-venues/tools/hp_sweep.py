# ホットペッパー 渋谷(Y030)・新宿(Y055)
#  1) 「個室あり」の全件索引（突合用）                       → hpg_index.json
#  2) 開催日・15名・ネット予約で空き枠が出る店（18時／19時） → hpg_avail.json
import re, json, time, os, urllib.request, gzip
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
CACHE='cache'; os.makedirs(CACHE, exist_ok=True)
def get(url, key, sleep=0.8):
    p=os.path.join(CACHE,key)
    if os.path.exists(p) and os.path.getsize(p)>3000:
        return open(p,encoding='utf-8',errors='replace').read()
    req=urllib.request.Request(url, headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            raw=r.read()
            if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
    except Exception as e:
        print('ERR',url,e,flush=True); return ''
    h=raw.decode('utf-8','replace'); open(p,'w',encoding='utf-8').write(h); time.sleep(sleep); return h
def t(s): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',s)).replace('&amp;','&').strip()
def parse(h):
    out=[]
    for b in re.split(r'(?=<div class="shopDetailTop)', h)[1:]:
        idm=re.search(r'href="/(str[JA]\d+)/', b)
        nm=re.search(r'shopDetailStoreName">\s*<a[^>]*>(.*?)</a>', b, re.S)
        if not (idm and nm): continue
        lat=re.search(r'data-lat="([\d.]+)"', b); lon=re.search(r'data-lon="([\d.]+)"', b)
        gen=re.search(r'parentGenreName">(.*?)</p>', b, re.S)
        bud=re.search(r'dinnerBudget">(.*?)</p>', b, re.S)
        acc=re.search(r'shopDetailInfoAccess"[^>]*>(.*?)</li>', b, re.S)
        cat=re.search(r'shopDetailGenreCatch[^>]*>(.*?)</p>', b, re.S)
        out.append(dict(id=idm.group(1), name=t(nm.group(1)),
                        genre=t(gen.group(1)) if gen else '',
                        lat=float(lat.group(1)) if lat else None,
                        lon=float(lon.group(1)) if lon else None,
                        budget=t(bud.group(1)) if bud else '',
                        access=t(acc.group(1)) if acc else '',
                        catch=t(cat.group(1)) if cat else ''))
    return out
def sweep(area, qs, tag):
    rows={}; tot=None; pages=1
    for pg in range(1, 80):
        seg='' if pg==1 else 'bgn%d/'%pg
        h=get(f'https://www.hotpepper.jp/SA11/{area}/lst/{seg}?{qs}', f'hp_{tag}_{area}_{pg}.html')
        if not h: break
        if tot is None:
            m=re.search(r'fcLRed bold fs18 padLR3">([\d,]+)</span>',h); tot=int(m.group(1).replace(',','')) if m else 0
            pm=re.search(r'(\d+)/(\d+)ページ',h); pages=int(pm.group(2)) if pm else 1
        for r in parse(h): rows.setdefault(r['id'], r)
        if pg>=pages: break
    print(f'{tag} {area}: hits={tot} pages={pages} got={len(rows)}', flush=True)
    return tot, rows

AREAS={'Y030':'shibuya','Y055':'shinjuku'}
idx={}; counts={}
for a,name in AREAS.items():
    tot, rows = sweep(a, 'FCS=U004', 'room')
    counts[f'{name}_room']=tot
    for r in rows.values(): r['area']=name; idx.setdefault(r['id'], r)
json.dump(list(idx.values()), open('hpg_index.json','w'), ensure_ascii=False, indent=1)

# 開催日の空き枠。日時・人数はここだけに置く（ページ側は結果のフラグだけ持つ）
RDT='20261025'; RPN='15'
avail={}
for a,name in AREAS.items():
    for rtm in ('1800','1900'):
        tot, rows = sweep(a, f'RDT={RDT}&RTM={rtm}&RPN={RPN}&NET=1&FCS=U004', f'av{rtm}')
        counts[f'{name}_avail{rtm}']=tot
        for hid, r in rows.items():
            avail.setdefault(hid, []).append(rtm)
            if hid not in idx: r['area']=name; idx[hid]=r
json.dump(list(idx.values()), open('hpg_index.json','w'), ensure_ascii=False, indent=1)
json.dump({'counts':counts,'avail':avail}, open('hpg_avail.json','w'), ensure_ascii=False, indent=1)
print('INDEX', len(idx), 'AVAIL', len(avail), counts)

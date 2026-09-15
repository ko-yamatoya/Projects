# 掃引結果のうち 評点3.30以上・口コミ50件以上・夜予算￥4,999以下 の店の詳細
# （座標・席・個室・貸切・営業時間・口コミ抜粋）→ tabelog_detail.json
# 評価分布（/dtlratings/）は件数が多いので、絞り込み後の候補だけ tb_neg.py で取る
import re, json, time, os, urllib.request, gzip
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
CACHE='cache'; os.makedirs(CACHE, exist_ok=True)
def get(url, key, sleep=1.0):
    p=os.path.join(CACHE,key)
    if os.path.exists(p) and os.path.getsize(p)>5000:
        return open(p,encoding='utf-8',errors='replace').read()
    req=urllib.request.Request(url, headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            raw=r.read()
            if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
    except Exception as e:
        print('ERR', key, e, flush=True); return ''
    h=raw.decode('utf-8','replace'); open(p,'w',encoding='utf-8').write(h); time.sleep(sleep); return h
def clean(s): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).replace('&amp;','&').strip()

CHEAP=('￥2,000～￥2,999','￥3,000～￥3,999','￥4,000～￥4,999')
rows=json.load(open('tabelog_all.json'))['rows']
pool=[r for r in rows if (r['score'] or 0)>=3.30 and r['reviews']>=50 and r['budget_dinner'] in CHEAP]
print('pool',len(pool),flush=True)
out={}
for i,r in enumerate(pool):
    h=get(r['url'], f"tbd_{r['id']}.html")
    if not h: continue
    d=dict(r)
    m=re.search(r'<script type="application/ld\+json">\s*(\{.*?"@type":\s*"Restaurant".*?\})\s*</script>', h, re.S)
    if m:
        try:
            j=json.loads(m.group(1))
            d['addr']=j.get('address',{}).get('streetAddress','')
            g=j.get('geo',{}) or {}
            d['lat']=g.get('latitude'); d['lon']=g.get('longitude')
            d['tel']=j.get('telephone','')
            d['sample_reviews']=[(x.get('reviewBody') or '')[:900] for x in (j.get('review') or [])][:4]
        except Exception as e: print('jsonerr',r['id'],e,flush=True)
    tbl={}
    for mm in re.finditer(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', h, re.S):
        k=clean(mm.group(1)); v=clean(mm.group(2))
        if k and v: tbl.setdefault(k, v[:700])
    d['tbl']=tbl
    out[r['id']]=d
    if i%50==0: print(i, r['name'][:20], len(tbl), flush=True)
json.dump(list(out.values()), open('tabelog_detail.json','w'), ensure_ascii=False, indent=1)
print('DONE', len(out))

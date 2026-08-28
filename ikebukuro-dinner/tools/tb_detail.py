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

rows=json.load(open('tabelog_all.json'))['rows']
pool=[r for r in rows if (r['score'] or 0)>=3.38]
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
            d['locality']=j.get('address',{}).get('addressLocality','')
            g=j.get('geo',{}) or {}
            d['lat']=g.get('latitude'); d['lon']=g.get('longitude')
            d['tel']=j.get('telephone',''); d['cuisine']=j.get('servesCuisine','')
            ar=j.get('aggregateRating',{}) or {}
            d['score_detail']=float(ar.get('ratingValue') or 0) or None
            d['reviews_detail']=int(ar.get('ratingCount') or 0)
            d['sample_reviews']=[ (x.get('reviewBody') or '')[:900] for x in (j.get('review') or [])][:4]
        except Exception as e: print('jsonerr',r['id'],e,flush=True)
    tbl={}
    for mm in re.finditer(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', h, re.S):
        k=clean(mm.group(1)); v=clean(mm.group(2))
        if k and v: tbl.setdefault(k, v[:600])
    d['tbl']=tbl
    out[r['id']]=d
    if i%25==0: print(i, r['name'][:20], flush=True)
json.dump(list(out.values()), open('tabelog_detail.json','w'), ensure_ascii=False, indent=1)
print('DONE', len(out))

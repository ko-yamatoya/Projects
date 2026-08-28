import re, json, time, os, urllib.request, gzip, sys
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
        print('ERR',url,e); return ''
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
        pre=re.search(r'storeNamePrefix[^>]*>(.*?)</p>', b, re.S)
        bud=re.search(r'dinnerBudget">(.*?)</p>', b, re.S)
        acc=re.search(r'shopDetailInfoAccess"[^>]*>(.*?)</li>', b, re.S)
        cat=re.search(r'shopDetailGenreCatch[^>]*>(.*?)</p>', b, re.S)
        out.append(dict(id=idm.group(1), name=t(nm.group(1)),
                        prefix=t(pre.group(1)) if pre else '',
                        genre=t(gen.group(1)) if gen else '',
                        lat=float(lat.group(1)) if lat else None,
                        lon=float(lon.group(1)) if lon else None,
                        budget=t(bud.group(1)) if bud else '',
                        access=t(acc.group(1)) if acc else '',
                        catch=t(cat.group(1)) if cat else ''))
    return out
GENRES=['G001','G002','G003','G004','G005','G006','G007','G008','G017','G009','G010','G012','G013','G014','G015','G016','G011']
idx={}
for g in GENRES:
    h=get(f'https://www.hotpepper.jp/SA11/Y050/{g}/', f'hp_{g}_1.html')
    if not h: continue
    m=re.search(r'fcLRed bold fs18 padLR3">([\d,]+)</span>', h)
    tot=int(m.group(1).replace(',','')) if m else 0
    pm=re.search(r'(\d+)/(\d+)ページ', h); pages=int(pm.group(2)) if pm else 1
    rows=parse(h)
    for r in rows: r['hp_genre_code']=g; idx.setdefault(r['id'], r)
    for pg in range(2, min(pages,40)+1):
        hh=get(f'https://www.hotpepper.jp/SA11/Y050/{g}/bgn{pg}/', f'hp_{g}_{pg}.html')
        if not hh: break
        for r in parse(hh):
            r['hp_genre_code']=g; idx.setdefault(r['id'], r)
    print(f'{g}: total={tot} pages={pages} cum={len(idx)}', flush=True)
json.dump(list(idx.values()), open('hpg_index.json','w'), ensure_ascii=False, indent=1)
print('HPG INDEX', len(idx))

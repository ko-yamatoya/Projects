import re, json, time, sys, os, urllib.request, gzip, io

UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
CACHE='cache'; os.makedirs(CACHE, exist_ok=True)

def get(url, key, sleep=1.0):
    p=os.path.join(CACHE, key)
    if os.path.exists(p) and os.path.getsize(p)>2000:
        return open(p, encoding='utf-8', errors='replace').read()
    req=urllib.request.Request(url, headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw=r.read()
        if r.headers.get('Content-Encoding')=='gzip':
            raw=gzip.decompress(raw)
    h=raw.decode('utf-8','replace')
    open(p,'w',encoding='utf-8').write(h)
    time.sleep(sleep)
    return h

def txt(s):
    s=re.sub(r'<[^>]+>','',s)
    return re.sub(r'\s+',' ',s).replace('&amp;','&').strip()

def parse_list(h):
    out=[]
    blocks=re.split(r'(?=<div class="list-rst js-bookmark)', h)
    for b in blocks[1:]:
        rid=re.search(r'data-rst-id="(\d+)"', b)
        url=re.search(r'data-detail-url="([^"]+)"', b)
        nm=re.search(r'class="list-rst__rst-name-target[^"]*"[^>]*>(.*?)</a>', b, re.S)
        ag=re.search(r'class="list-rst__area-genre[^"]*">(.*?)</div>', b, re.S)
        sc=re.search(r'list-rst__rating-val">([0-9.]+)<', b)
        rv=re.search(r'cpy-review-count">([\d,]+)<', b)
        sv=re.search(r'list-rst__save-count-num[^>]*>([\d,]+)<', b)
        dn=re.search(r'c-rating-v3__time--dinner"[^>]*></i><span class="c-rating-v3__val">([^<]*)</span>', b)
        ln=re.search(r'c-rating-v3__time--lunch"[^>]*></i><span class="c-rating-v3__val">([^<]*)</span>', b)
        hd=re.search(r'list-rst__holiday-text">([^<]*)<', b)
        if not (rid and nm): continue
        a=txt(ag.group(1)) if ag else ''
        m=re.match(r'(.+?駅)\s*([\d.]+)(m|km)\s*/\s*(.*)$', a)
        st, dist, gen = ('','',a)
        if m:
            st=m.group(1); d=float(m.group(2)); dist=int(d*1000) if m.group(3)=='km' else int(d); gen=m.group(4)
        out.append(dict(id=rid.group(1), url=url.group(1) if url else '', name=txt(nm.group(1)),
                        station=st, dist_m=dist, genres=gen,
                        score=float(sc.group(1)) if sc else None,
                        reviews=int(rv.group(1).replace(',','')) if rv else 0,
                        saves=int(sv.group(1).replace(',','')) if sv else 0,
                        budget_dinner=txt(dn.group(1)) if dn else '',
                        budget_lunch=txt(ln.group(1)) if ln else '',
                        holiday=txt(hd.group(1)) if hd else ''))
    return out

BASE='https://tabelog.com/tokyo/A1305/A130501/rstLst/{p}?SrtT=rt&RdoCosTp=2&LstCos=2&LstCosT=6'
all_rows={}; total=None
for page in range(1, 41):
    seg='' if page==1 else f'{page}/'
    h=get(BASE.format(p=seg), f'tb_all_{page}.html')
    if total is None:
        m=re.findall(r'class="c-page-count__num"[^>]*>\s*<strong>([\d,]+)</strong>', h)
        if len(m)>=3: total=int(m[2].replace(',',''))
    rows=parse_list(h)
    if not rows: print('no rows at page',page); break
    for r in rows: all_rows[r['id']]=r
    lo=min(r['score'] for r in rows if r['score'] is not None)
    print(f'page {page}: {len(rows)} rows, min={lo}, cum={len(all_rows)}', flush=True)
    if lo < 3.25: break

json.dump({'total_hits':total,'rows':list(all_rows.values())}, open('tabelog_all.json','w'), ensure_ascii=False, indent=1)
print('TOTAL HITS', total, 'collected', len(all_rows))

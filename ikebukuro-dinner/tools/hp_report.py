import re, json, time, os, urllib.request, gzip
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
CACHE='cache'
def get(url,key,sleep=0.9):
    p=os.path.join(CACHE,key)
    if os.path.exists(p) and os.path.getsize(p)>3000: return open(p,encoding='utf-8',errors='replace').read()
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            raw=r.read()
            if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
    except Exception as e:
        print('ERR',key,e,flush=True); return ''
    h=raw.decode('utf-8','replace'); open(p,'w',encoding='utf-8').write(h); time.sleep(sleep); return h
def clean(s): return re.sub(r'\s+',' ',re.sub(r'<br\s*/?>','\n',re.sub(r'<[^>]+>',' ',s))).replace('&amp;','&').strip()

joined=[r for r in json.load(open('join.json')) if r.get('hp_id')]
print('targets',len(joined),flush=True)
out={}
for i,j in enumerate(joined):
    hid=j['hp_id']
    h=get(f'https://www.hotpepper.jp/{hid}/report/', f'hpr_{hid}.html')
    if not h: continue
    d={'hp_id':hid,'tb_id':j['tb_id']}
    m=re.search(r'ratingScoreNumber">\s*([\d.]+)\s*<',h)
    d['score']=float(m.group(1)) if m else None
    dist={}
    for mm in re.finditer(r'ratingScore">\s*(\d)\s*</[^>]+>.*?ratingCount">\s*([\d,]+)件',h,re.S):
        dist[int(mm.group(1))]=int(mm.group(2).replace(',',''))
    d['dist']=dist; d['calc_n']=sum(dist.values())
    m=re.search(r'reportCount">口コミ([\d,]+)件',h)
    d['total_reviews']=int(m.group(1).replace(',','')) if m else None
    cats={}
    for mm in re.finditer(r'ratingCategoryItemTitle">\s*(.*?)\s*</[^>]+>\s*<[^>]*ratingCategoryItemScore">\s*([\d.]+)\s*<',h,re.S):
        cats[clean(mm.group(1))]=float(mm.group(2))
    d['cats']=cats
    revs=[]
    for b in re.split(r'(?=<div class="reportCassette">)',h)[1:]:
        dt=re.search(r'individualInfo[^>]*>\s*(.*?)</p>',b,re.S)
        sc=re.search(r'starRatingValue">\s*([\d.]+)\s*<',b)
        tx=re.search(r'reportText">\s*<span class="text">(.*?)</span>',b,re.S)
        vs=[clean(x) for x in re.findall(r'<div(?:\s+class="icn\w+")?>(.*?)</div>',b,re.S)]
        vis=re.search(r'icn(Dinner|Lunch)">(.*?)</div>',b,re.S)
        bill=re.search(r'会計：([^<]*)',b); scene=re.search(r'来店シーン：([^<]*)',b); crs=re.search(r'予約コース：([^<]*)',b)
        dm=re.search(r'来店日：([\d/]+)',b)
        revs.append(dict(when=dm.group(1) if dm else '', who=clean(dt.group(1)) if dt else '',
                         score=float(sc.group(1)) if sc else None,
                         text=clean(tx.group(1))[:600] if tx else '',
                         visit=clean(vis.group(2)) if vis else '',
                         bill=clean(bill.group(1)) if bill else '',
                         scene=clean(scene.group(1)) if scene else '',
                         course=clean(crs.group(1)) if crs else ''))
    d['reviews']=revs
    out[hid]=d
    if i%20==0: print(i,hid,d['score'],d['calc_n'],flush=True)
json.dump(out,open('hpg_reports.json','w'),ensure_ascii=False,indent=1)
print('DONE',len(out))

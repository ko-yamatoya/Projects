import re,json,random,os,time,urllib.request,gzip
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
def get(url,key,sleep=0.8):
    p=os.path.join('cache',key)
    if os.path.exists(p) and os.path.getsize(p)>3000: return open(p,encoding='utf-8',errors='replace').read()
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    try:
        with urllib.request.urlopen(req,timeout=40) as r:
            raw=r.read()
            if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
    except Exception as e: return ''
    h=raw.decode('utf-8','replace'); open(p,'w',encoding='utf-8').write(h); time.sleep(sleep); return h
idx=json.load(open('hpg_index.json'))
random.seed(20260829)
sample=random.sample(idx, 160)
res=[]
for i,s in enumerate(sample):
    h=get(f"https://www.hotpepper.jp/{s['id']}/report/", f"hpr_{s['id']}.html")
    if not h: continue
    m=re.search(r'ratingScoreNumber">\s*([\d.]+)\s*<',h)
    dist={}
    for mm in re.finditer(r'ratingScore">\s*(\d)\s*</[^>]+>.*?ratingCount">\s*([\d,]+)件',h,re.S):
        dist[int(mm.group(1))]=int(mm.group(2).replace(',',''))
    tm=re.search(r'reportCount">口コミ([\d,]+)件',h)
    res.append(dict(id=s['id'],name=s['name'],genre=s.get('genre',''),
                    score=float(m.group(1)) if m else None, calc_n=sum(dist.values()),
                    total=int(tm.group(1).replace(',','')) if tm else 0))
    if i%40==0: print(i,flush=True)
json.dump(res,open('hpg_baseline.json','w'),ensure_ascii=False,indent=1)
print('DONE',len(res))

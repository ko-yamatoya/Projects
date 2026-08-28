import re,json,os,time,urllib.request,gzip
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
def get(url,key,sleep=0.9):
    p=os.path.join('cache',key)
    if os.path.exists(p) and os.path.getsize(p)>5000: return open(p,encoding='utf-8',errors='replace').read()
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            raw=r.read()
            if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
    except Exception as e:
        print('ERR',key,e,flush=True); return ''
    h=raw.decode('utf-8','replace'); open(p,'w',encoding='utf-8').write(h); time.sleep(sleep); return h
def cl(s): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' | ',s)).strip()

cands=json.load(open('candidates.json'))
out={}
for i,c in enumerate(cands):
    base=c['url'].rstrip('/')
    d={'id':c['id']}
    h=get(base+'/dtlratings/', f"tbrat_{c['id']}.html")
    if h:
        i2=h.find('評価分布')
        seg=cl(h[i2:i2+6000]) if i2>0 else ''
        buckets=re.findall(r'((?:5\.0|[1-4]\.\d\s*-\s*[1-5]\.\d))\s*\|[^0-9]*?\|\s*([\d,]+)\s*\|\s*人', seg)
        dist={}
        for k,v in buckets:
            dist[re.sub(r'\s','',k)]=int(v.replace(',',''))
        d['dist']=dist
    h2=get(base+'/dtlrvwlst/', f"tbrvw_{c['id']}.html")
    if h2:
        d['visit_months']=re.findall(r'(\d{4}/\d{2})訪問', h2)[:25]
        titles=[re.sub(r'<[^>]+>','',x).strip() for x in re.findall(r'rvw-item__title-target[^>]*>(.*?)</a>', h2, re.S)][:20]
        d['recent_titles']=titles
        bodies=[re.sub(r'\s+',' ',re.sub(r'<[^>]+>','',x)).strip()[:400] for x in re.findall(r'rvw-item__rvw-comment[^>]*>(.*?)</div>', h2, re.S)][:12]
        d['recent_bodies']=bodies
    out[c['id']]=d
    if i%20==0: print(i,c['name'][:18],d.get('dist'),flush=True)
json.dump(out,open('tabelog_neg.json','w'),ensure_ascii=False,indent=1)
print('DONE',len(out))

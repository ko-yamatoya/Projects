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
def cl(s): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).replace('&amp;','&').replace('&nbsp;',' ').strip()
KEEP=['住所','アクセス','営業時間','定休日','予算詳細','総席数','最大宴会収容人数','個室','座敷','掘りごたつ','カウンター','ソファー','貸切','飲み放題','食べ放題','お酒','禁煙・喫煙','クレジットカード','その他設備','ネット予約受付時間','お子様連れ','Wi-Fi']
cands=[c for c in json.load(open('candidates.json')) if c.get('hp_id')]
print('targets',len(cands),flush=True)
out={}
for i,c in enumerate(cands):
    hid=c['hp_id']; d={'hp_id':hid,'tb_id':c['id']}
    h=get(f'https://www.hotpepper.jp/{hid}/', f'hps_{hid}.html')
    if h:
        tbl={}
        for m in re.finditer(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>',h,re.S):
            k=cl(m.group(1)); v=cl(m.group(2))
            if k in KEEP and k not in tbl: tbl[k]=v[:400]
        d['info']=tbl
        m=re.search(r'<h1[^>]*>(.*?)</h1>',h,re.S); d['hp_name']=cl(m.group(1))[:80] if m else ''
    hc=get(f'https://www.hotpepper.jp/{hid}/course/', f'hpc_{hid}.html')
    if hc:
        cs=[]
        for b in re.split(r'(?=<div class="courseNameWrap|<h3 class="courseName)',hc)[1:]:
            nm=re.search(r'(?:courseName[^>]*>|<a[^>]*>)(.*?)</',b,re.S)
            pr=re.search(r'([\d,]+)円',b)
            if nm and pr:
                cs.append((cl(nm.group(1))[:90], pr.group(1)))
        d['courses']=cs[:14]
        d['course_raw_nomi']=[cl(x)[:120] for x in re.findall(r'([^<>]{0,90}飲み放題[^<>]{0,60})',hc)][:12]
    out[hid]=d
    if i%15==0: print(i,hid,flush=True)
json.dump(out,open('hpg_store.json','w'),ensure_ascii=False,indent=1)
print('DONE',len(out))

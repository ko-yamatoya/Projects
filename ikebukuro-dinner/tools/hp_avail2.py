import re,json,os,time,urllib.request,gzip,sys
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
# 想定利用の日時・人数は引数で渡す（ページにも既定値にも残さない）
#   python3 hp_avail2.py NET YYYYMMDD HHMM 人数
MODE=sys.argv[1]                      # 'IMR'(即予約) or 'NET'(ネット予約)
RDT,RTM,RPN=sys.argv[2],sys.argv[3],sys.argv[4]
def get(url,key,sleep=0.7):
    p=os.path.join('cache',key)
    if os.path.exists(p) and os.path.getsize(p)>3000: return open(p,encoding='utf-8',errors='replace').read()
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            raw=r.read()
            if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
    except Exception as e:
        print('ERR',key,e,flush=True); return ''
    h=raw.decode('utf-8','replace'); open(p,'w',encoding='utf-8').write(h); time.sleep(sleep); return h
G=['G001','G002','G003','G004','G005','G006','G007','G008','G017','G009','G010','G012','G013','G014','G015','G016','G011']
ids=set(); grand=0
for g in G:
    tot=None; pages=1
    for pg in range(1,40):
        seg='' if pg==1 else 'bgn%d/'%pg
        u='https://www.hotpepper.jp/SA11/Y050/%s/%s?RDT=%s&RTM=%s&RPN=%s&%s=1'%(g,seg,RDT,RTM,RPN,MODE)
        h=get(u,'hpav2_%s_%s_%s_%d.html'%(MODE,RDT,g,pg))
        if not h: break
        if tot is None:
            m=re.search(r'fcLRed bold fs18 padLR3">([\d,]+)</span>',h); tot=int(m.group(1).replace(',','')) if m else 0
            pm=re.search(r'(\d+)/(\d+)ページ',h); pages=int(pm.group(2)) if pm else 1
            grand+=tot
        ids |= set(re.findall(r'/(str[JA]\d+)/',h))
        if pg>=pages: break
    print(f'{g}: {tot} ({pages}p) cum={len(ids)}',flush=True)
json.dump(sorted(ids), open('hpg_avail_%s.json'%MODE,'w'))
print('MODE',MODE,'延べ',grand,'ユニーク',len(ids))

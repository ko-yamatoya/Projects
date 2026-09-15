# 突合できた候補のホットペッパー店舗ページ・コース・口コミ → hpg_store.json
#   店舗: 総席数／最大宴会収容人数／個室／貸切／飲み放題／営業時間／定休日／ネット予約受付
#   コース: コース名・税込価格・利用人数・飲み放題付きか
#   口コミ: 評点・星分布・来店シーン・本文（騒がしさの言及を数えるため）
import re, json, os, sys, time, urllib.request, gzip
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
CACHE='cache'
def get(url,key,sleep=0.9):
    p=os.path.join(CACHE,key)
    if os.path.exists(p) and os.path.getsize(p)>5000: return open(p,encoding='utf-8',errors='replace').read()
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            raw=r.read()
            if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
    except Exception as e:
        print('ERR',key,e,flush=True); return ''
    h=raw.decode('utf-8','replace'); open(p,'w',encoding='utf-8').write(h); time.sleep(sleep); return h
def cl(s): return re.sub(r'\s+',' ',re.sub(r'<br\s*/?>',' ',re.sub(r'<[^>]+>',' ',s))).replace('&amp;','&').replace('&nbsp;',' ').strip()

KEEP=['営業時間','定休日','予算詳細','総席数','最大宴会収容人数','個室','座敷','掘りごたつ','貸切','飲み放題','禁煙・喫煙','ネット予約受付時間','その他設備','アクセス','住所']

def parse_courses(hc):
    out=[]
    for b in re.split(r'(?=<[^>]+class="courseCassetteTitle)', hc)[1:]:
        title=re.search(r'class="courseCassetteTitle[^"]*"[^>]*>(.*?)</p>', b, re.S)
        pm=re.search(r'class="priceNumber">\s*([\d,]+)\s*<', b)
        if not (title and pm): continue
        body=cl(b)[:600]
        ppl=re.search(r'利用人数：\s*([^／\s]+)', body)
        nm=cl(title.group(1))[:120]
        # 飲み放題付きかはカードのラベル画像（alt="飲み放題"）が確実。単品飲み放題プランも同じラベルなので名前で区別する
        label='alt="飲み放題"' in b
        solo=bool(re.search(r'単品飲み放題|飲み放題(のみ|単品)', nm))
        out.append(dict(name=nm, price=int(pm.group(1).replace(',','')),
                        people=ppl.group(1) if ppl else '',
                        nomi=label or '飲み放題' in nm, nomi_only=solo))
    return out

def parse_report(h):
    d={}
    m=re.search(r'ratingScoreNumber">\s*([\d.]+)\s*<',h); d['score']=float(m.group(1)) if m else None
    dist={int(mm.group(1)):int(mm.group(2).replace(',','')) for mm in re.finditer(r'ratingScore">\s*(\d)\s*</[^>]+>.*?ratingCount">\s*([\d,]+)件',h,re.S)}
    d['dist']=dist; d['calc_n']=sum(dist.values())
    m=re.search(r'reportCount">口コミ([\d,]+)件',h); d['total_reviews']=int(m.group(1).replace(',','')) if m else None
    revs=[]
    for b in re.split(r'(?=<div class="reportCassette">)',h)[1:]:
        tx=re.search(r'reportText">\s*<span class="text">(.*?)</span>',b,re.S)
        dm=re.search(r'来店日：([\d/]+)',b); sc=re.search(r'来店シーン：([^<]*)',b)
        st=re.search(r'starRatingValue">\s*([\d.]+)\s*<',b)
        revs.append(dict(when=dm.group(1) if dm else '', scene=cl(sc.group(1)) if sc else '',
                         score=float(st.group(1)) if st else None, text=cl(tx.group(1))[:500] if tx else ''))
    d['reviews']=revs
    return d

if __name__=='__main__':
    ids=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'hp_targets.json'))
    print('targets',len(ids),flush=True)
    out={}
    for i,hid in enumerate(ids):
        d={'hp_id':hid}
        h=get(f'https://www.hotpepper.jp/{hid}/', f'hps_{hid}.html')
        if h:
            tbl={}
            for m in re.finditer(r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>',h,re.S):
                k=cl(m.group(1)); v=cl(m.group(2))
                if k in KEEP and k not in tbl: tbl[k]=v[:500]
            d['info']=tbl
            m=re.search(r'<h1 class="shopName">(.*?)</h1>',h,re.S); d['hp_name']=cl(m.group(1))[:100] if m else ''
        hc=get(f'https://www.hotpepper.jp/{hid}/course/', f'hpc_{hid}.html')
        d['courses']=parse_courses(hc) if hc else []
        hr=get(f'https://www.hotpepper.jp/{hid}/report/', f'hpr_{hid}.html')
        d['report']=parse_report(hr) if hr else {}
        out[hid]=d
        if i%10==0: print(i,hid,len(d['courses']),d['report'].get('score'),flush=True)
    json.dump(out,open('hpg_store.json','w'),ensure_ascii=False,indent=1)
    print('DONE',len(out))

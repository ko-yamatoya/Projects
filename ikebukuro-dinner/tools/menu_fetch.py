import re,json,os,time,urllib.request,gzip
from final_list import FINAL
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
def get(url,key,sleep=0.9):
    p=os.path.join('cache',key)
    if os.path.exists(p) and os.path.getsize(p)>4000: return open(p,encoding='utf-8',errors='replace').read()
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            raw=r.read()
            if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
    except Exception as e:
        print('ERR',key,e,flush=True); return ''
    h=raw.decode('utf-8','replace'); open(p,'w',encoding='utf-8').write(h); time.sleep(sleep); return h
def cl(s): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s)).replace('&amp;','&').replace('&nbsp;',' ').strip()
c={x['name']:x for x in json.load(open('candidates4.json'))}
out={}
for n,b,g in FINAL:
    x=c[n]; d={'name':n,'tb_menu':[],'hp_food':[]}
    h=get(x['url'].rstrip('/')+'/dtlmenu/', f"tbm_{x['id']}.html")
    if h:
        items=[]
        for m in re.finditer(r'rstdtl-menu-lst__menu-name[^>]*>(.*?)</(?:p|h4|div|span)>',h,re.S):
            t=cl(m.group(1))
            if t and len(t)<40: items.append(t)
        if not items:
            for m in re.finditer(r'class="[^"]*menu-name[^"]*"[^>]*>(.*?)<',h,re.S):
                t=cl(m.group(1))
                if t and len(t)<40: items.append(t)
        d['tb_menu']=list(dict.fromkeys(items))[:25]
    if x.get('hp_id'):
        hf=get(f"https://www.hotpepper.jp/{x['hp_id']}/food/", f"hpf_{x['hp_id']}.html")
        if hf:
            items=[]
            for m in re.finditer(r'class="(?:foodName|dishName|recommendName|itemName)"[^>]*>(.*?)</',hf,re.S):
                items.append(cl(m.group(1)))
            if not items:
                for m in re.finditer(r'<h3[^>]*>(.*?)</h3>',hf,re.S):
                    t=cl(m.group(1))
                    if t and len(t)<40: items.append(t)
            d['hp_food']=list(dict.fromkeys([i for i in items if i]))[:25]
    out[n]=d
    print(n[:20],len(d['tb_menu']),len(d['hp_food']),flush=True)
json.dump(out,open('menus.json','w'),ensure_ascii=False,indent=1)

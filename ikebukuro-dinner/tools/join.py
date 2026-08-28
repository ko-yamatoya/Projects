import json, re, math, unicodedata, difflib, sys

def norm(s):
    s=unicodedata.normalize('NFKC', s or '')
    s=re.sub(r'[【（(\[].*?[】）)\]]','',s)
    s=re.sub(r'[\s・,、。／/\-–—~〜’\'"”“!！?？&＆+＋*×#]','',s)
    return s.lower()

DROP=['池袋西口本店','池袋東口店','池袋西口店','池袋北口店','池袋本店','池袋店','池袋','本店','別館','支店','店']
def core(s):
    n=norm(s)
    for d in DROP:
        n=n.replace(norm(d),'')
    return n

def hav(a,b,c,d):
    if None in (a,b,c,d): return 9e9
    R=6371000.0
    p1,p2=math.radians(a),math.radians(c)
    dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

tb=json.load(open('tabelog_detail.json'))
hp=json.load(open('hpg_index.json'))
for h in hp:
    h['_n']=norm(h['name']); h['_c']=core(h['name'])

res=[]
for t in tb:
    tn=norm(t['name']); tc=core(t['name'])
    lat=t.get('lat'); lon=t.get('lon')
    best=None
    for h in hp:
        d=hav(lat,lon,h.get('lat'),h.get('lon'))
        if d>250: continue
        sim=difflib.SequenceMatcher(None,tn,h['_n']).ratio()
        sub = (tc and (tc in h['_n'] or h['_c'] in tn)) or (h['_c'] and h['_c'] in tn)
        sc = sim + (0.35 if sub else 0) + (0.25 if d<60 else 0.1 if d<120 else 0)
        if best is None or sc>best[0]: best=(sc,d,sim,sub,h)
    if best and (best[0]>=0.85 or (best[2]>=0.6 and best[1]<120) or (best[3] and best[1]<150)):
        sc,d,sim,sub,h=best
        res.append(dict(tb_id=t['id'], tb_name=t['name'], hp_id=h['id'], hp_name=h['name'],
                        dist=round(d,1), sim=round(sim,2), sub=bool(sub), conf=round(sc,2)))
    else:
        res.append(dict(tb_id=t['id'], tb_name=t['name'], hp_id=None,
                        near=(round(best[1],1), best[4]['name'], round(best[2],2)) if best else None))
json.dump(res, open('join.json','w'), ensure_ascii=False, indent=1)
m=[r for r in res if r['hp_id']]
print('tabelog',len(tb),'matched',len(m),f'{len(m)/max(1,len(tb))*100:.0f}%')
print('\n-- sample matched --')
for r in m[:15]: print(f"  {r['conf']} d={r['dist']}m  {r['tb_name'][:24]:<26} <-> {r['hp_name'][:40]}")
print('\n-- sample unmatched --')
for r in [x for x in res if not x['hp_id']][:15]: print(f"  {r['tb_name'][:28]:<30} near={r['near']}")

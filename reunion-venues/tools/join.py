# 店名＋座標(250m以内)で 食べログ ↔ ホットペッパー を突合 → join.json
import json, re, math, unicodedata, difflib

def norm(s):
    s=unicodedata.normalize('NFKC', s or '')
    s=re.sub(r'[【（(\[].*?[】）)\]]','',s)
    s=re.sub(r'[\s・,、。／/\-–—~〜’\'"”“!！?？&＆+＋*×#♪◎]','',s)
    return s.lower()

DROP=['渋谷センター街店','渋谷道玄坂店','渋谷宮益坂店','渋谷駅前店','渋谷本店','渋谷店','渋谷',
      '新宿東口店','新宿西口店','新宿南口店','新宿三丁目店','歌舞伎町店','新宿本店','新宿店','新宿',
      '本店','別館','支店','店','個室','完全個室','居酒屋','食べ飲み放題','飲み放題','食べ放題']
def core(s):
    n=norm(s)
    for d in DROP: n=n.replace(norm(d),'')
    return n

def hav(a,b,c,d):
    if None in (a,b,c,d): return 9e9
    R=6371000.0
    p1,p2=math.radians(a),math.radians(c)
    dp=math.radians(c-a); dl=math.radians(d-b)
    x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(x))

if __name__=='__main__':
    tb=json.load(open('tabelog_detail.json'))
    hp=json.load(open('hpg_index.json'))
    for h in hp: h['_n']=norm(h['name']); h['_c']=core(h['name'])
    res=[]
    for t in tb:
        tn=norm(t['name']); tc=core(t['name'])
        best=None
        for h in hp:
            d=hav(t.get('lat'),t.get('lon'),h.get('lat'),h.get('lon'))
            if d>250: continue
            # 類似度は支店名・地名を除いた芯どうしで測る。全体で測ると「○○ 新宿西口店」どうしが
            # 別の店でも0.6を超えた（電光石火↔プングム、松よし↔焼肉トラジ など）
            sim=difflib.SequenceMatcher(None,tc or tn,h['_c'] or h['_n']).ratio()
            # ホットペッパーの店名は宣伝文句が前に付く（「完全個室 肉バル ○○ 渋谷店」）ので、芯の名前の包含を重く見る
            sub=bool(len(tc)>=2 and (tc in h['_n'])) or bool(len(h['_c'])>=2 and h['_c'] in tn)
            sc=sim+(0.35 if sub else 0)+(0.25 if d<60 else 0.1 if d<120 else 0)
            if best is None or sc>best[0]: best=(sc,d,sim,sub,h)
        if best and (best[0]>=0.85 or (best[2]>=0.6 and best[1]<120) or (best[3] and best[1]<150)):
            sc,d,sim,sub,h=best
            res.append(dict(tb_id=t['id'], tb_name=t['name'], hp_id=h['id'], hp_name=h['name'],
                            dist=round(d,1), sim=round(sim,2), sub=sub, conf=round(sc,2)))
        else:
            res.append(dict(tb_id=t['id'], tb_name=t['name'], hp_id=None,
                            near=(round(best[1],1), best[4]['name'], round(best[2],2)) if best else None))
    json.dump(res, open('join.json','w'), ensure_ascii=False, indent=1)
    m=[r for r in res if r['hp_id']]
    print('tabelog',len(tb),'matched',len(m),f'{len(m)/max(1,len(tb))*100:.0f}%')
    for r in m[:25]: print(f"  {r['conf']} d={r['dist']}m  {r['tb_name'][:24]:<26} <-> {r['hp_name'][:44]}")

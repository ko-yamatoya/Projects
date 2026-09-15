# 候補の食べログ評価分布（1.0〜5.0の人数）→ tabelog_neg.json
#   python3 tb_neg.py shortlist.json   # [{id,url}, ...]
import re, json, sys
from common import get

ids=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'shortlist.json'))
out={}
for i,x in enumerate(ids):
    hr=get(x['url'].rstrip('/')+'/dtlratings/', f"tbr_{x['id']}.html")
    dist={}
    # ラベルは「5.0」「4.5 - 4.9」の形。下限の数字をキーにする
    for mm in re.finditer(r'ratings-contents__item-score">\s*([\d.]+)(?:\s*-\s*[\d.]+)?\s*<.*?ratings-contents__item-num[^>]*>\s*(?:<[^>]+>\s*)*([\d,]+)', hr, re.S):
        dist[mm.group(1)]=int(mm.group(2).replace(',',''))
    out[x['id']]=dist
    if i%10==0: print(i, x['id'], sum(dist.values()), flush=True)
json.dump(out, open('tabelog_neg.json','w'), ensure_ascii=False, indent=1)
print('DONE', len(out))

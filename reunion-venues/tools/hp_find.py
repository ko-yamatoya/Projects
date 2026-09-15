# 候補のうちホットペッパー索引で突合できなかった店を、店名の芯でフリーワード検索して拾う → join_extra.json
#   索引（個室あり一覧）はページ送りで取りこぼすうえ、ホットペッパーの店名は宣伝文句つきで長いので、
#   食べログ名そのままでは0件になる。「西５東３」「老辺餃子舘」のように芯だけで引くと当たる（2026-09-15実測）
import json, re, unicodedata, urllib.parse, hashlib
from common import get
from join import hav, norm

AREA = {'shibuya': 'Y030', 'shinjuku': 'Y055'}
BRANCH = r'(渋谷|新宿|西新宿|東新宿|新宿三丁目|新大久保|道玄坂|宮益坂)?\S*?(本店|本館|本殿|別邸|別館|店)$'
# ジャンル名だけの語で引くと、250m以内の別の店に当たりうるので検索語にしない
GENERIC = re.compile(r'(料理|酒場|居酒屋|食堂|ダイニング|ビストロ|海鮮|おばんざい|炙り焼き|個室|完全個室|専門店|レストラン)$'
                     r'|^(BISTRO|BAR|DINING|CAFE|KITCHEN|酒|肉|魚)$'
                     # 地名・つなぎ語で引くと別の店に当たった（「渋谷」→カラオケパセラ、「新宿」→ビール工房、「DE」→別のメキシカン）
                     r'|^(渋谷|新宿|西新宿|東新宿|歌舞伎町|SHIBUYA|SHINJUKU|TOKYO|東京|カフェ|DE|BY|AND|THE|LA|LE|IL)$', re.I)

def cores(name):
    """検索語の候補。～…～の中 → 後ろの語から（固有名は後ろに来やすい）→ 全体、の順で最大3つ"""
    n = unicodedata.normalize('NFKC', name).replace('&#39;', "'")
    n2 = re.sub(r'\s+' + BRANCH, '', n).strip()
    qs = []
    m = re.search(r'[～~]\s*([^～~]+?)\s*[～~]', n2)
    if m: qs.append(m.group(1))
    toks = [t for t in re.split(r'[\s・～~×&]+', n2) if len(t) >= 2 and not GENERIC.search(t)]
    qs += list(reversed(toks))
    qs.append(n2)
    out = []
    for q in qs:
        if q and q not in out: out.append(q)
    return out[:3]

def parse(h):
    out = []
    for b in re.split(r'(?=<div class="shopDetailTop)', h)[1:]:
        idm = re.search(r'href="/(str[JA]\d+)/', b)
        nm = re.search(r'shopDetailStoreName">\s*<a[^>]*>(.*?)</a>', b, re.S)
        lat = re.search(r'data-lat="([\d.]+)"', b); lon = re.search(r'data-lon="([\d.]+)"', b)
        if idm and nm:
            out.append(dict(id=idm.group(1), name=re.sub(r'<[^>]+>|\s+', ' ', nm.group(1)).strip(),
                            lat=float(lat.group(1)) if lat else None, lon=float(lon.group(1)) if lon else None))
    return out

if __name__ == '__main__':
    sl = {x['id'] for x in json.load(open('shortlist.json'))}
    jn = {j['tb_id']: j for j in json.load(open('join.json'))}
    det = {d['id']: d for d in json.load(open('tabelog_detail.json'))}
    targets = [det[i] for i in sl if not (jn.get(i) or {}).get('hp_id')]
    print('targets', len(targets), flush=True)
    extra = {}
    for d in targets:
        hit = None
        for q in cores(d['name']):
            url = f"https://www.hotpepper.jp/SA11/{AREA[d['area']]}/lst/?FWT=" + urllib.parse.quote(q)
            # キャッシュ名は実行ごとに変わらない md5 で作る（str の hash() はプロセスごとに乱数化される）
            h = get(url, 'hpfw_' + d['id'] + '_' + hashlib.md5(q.encode()).hexdigest()[:10] + '.html', sleep=1.0)
            # 250m以内 かつ ホットペッパーの店名に検索語が入っている店だけを同じ店とみなす
            near = [(hav(d.get('lat'), d.get('lon'), r['lat'], r['lon']), r) for r in parse(h) if norm(q) in norm(r['name'])]
            near = sorted([x for x in near if x[0] <= 250], key=lambda x: x[0])
            if near:
                hit = (q, round(near[0][0]), near[0][1]); break
        if hit:
            extra[d['id']] = hit[2]['id']
            print(f"  + {d['name'][:24]:<26} q={hit[0][:14]:<16} {hit[1]}m -> {hit[2]['name'][:36]}", flush=True)
    json.dump(extra, open('join_extra.json', 'w'), ensure_ascii=False, indent=1)
    print('found', len(extra), 'of', len(targets))

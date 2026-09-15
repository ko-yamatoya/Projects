# 取得の共通部品。応答は cache/ に貯め、2回目以降は取りに行かない
import os, time, gzip, urllib.request
UA='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'
CACHE=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
os.makedirs(CACHE, exist_ok=True)

def get(url, key, sleep=1.0, min_size=3000):
    p=os.path.join(CACHE, key)
    if os.path.exists(p) and os.path.getsize(p)>min_size:
        return open(p, encoding='utf-8', errors='replace').read()
    req=urllib.request.Request(url, headers={'User-Agent':UA,'Accept-Language':'ja-JP,ja;q=0.9','Accept-Encoding':'gzip'})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            raw=r.read()
            if r.headers.get('Content-Encoding')=='gzip': raw=gzip.decompress(raw)
    except Exception as e:
        print('ERR', key, e, flush=True); return ''
    h=raw.decode('utf-8', 'replace')
    open(p, 'w', encoding='utf-8').write(h)
    time.sleep(sleep)
    return h

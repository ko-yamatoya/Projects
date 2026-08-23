#!/usr/bin/env python3
"""GoogleマップのURL・住所・店名から spots.js へ1件追加する。

使い方:
    python3 add_spot.py "https://maps.app.goo.gl/xxxx" --cat 食事 --note "海鮮" --tag 雨天微妙
    python3 add_spot.py "千葉県銚子市犬吠埼9576" --name 犬吠埼灯台 --cat 景色

短縮URLはブラウザUAを付けると中間ページで止まるので、curl既定UAで素直に展開させる。
座標は国土地理院の住所検索API（日本住所に強い）→ OSM Nominatim の順で引く。
"""
import argparse, json, re, subprocess, sys, unicodedata, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

SPOTS = Path(__file__).parent / "spots.js"
CHIBA = (34.80, 36.15, 139.65, 141.00)  # lat_min, lat_max, lng_min, lng_max
UA = "chiba-trip-map/1.0 (+https://github.com/ko-yamatoya/Projects)"


def expand(url):
    """短縮URLを展開して最終URLを返す。curl既定UAでないとJSの中間ページに阻まれる。"""
    r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{url_effective}", "-L", url],
                       capture_output=True, text=True, timeout=30)
    return r.stdout.strip() or url


def parse_gmap(url):
    """展開後のGoogleマップURLから 名称・住所・ftid を取り出す。"""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    raw = q.get("q", [""])[0]
    ftid = q.get("ftid", [""])[0]
    name = addr = ""
    if raw.startswith("〒"):
        # 「〒299-4615 千葉県いすみ市岬町井沢300-1 南印度料理 巡るインド」
        rest = re.sub(r"^〒\s*[0-9０-９\-−]+\s*", "", raw)
        parts = rest.split(" ", 1)
        addr = parts[0]
        name = parts[1].strip() if len(parts) > 1 else ""
    elif "," in raw:
        # 「Name, 番地, 市町村 郡 県 郵便番号」
        chunks = [c.strip() for c in raw.split(",")]
        name = chunks[0]
        # chunks[1] が「長生郡一宮町一宮字東台場10144番」のように郡市町村から始まる本体
        body = chunks[1] if len(chunks) > 1 else ""
        addr = body if body.startswith("千葉県") else "千葉県" + body
    else:
        name = raw
    # 座標がURLに含まれていれば拾う（!3d緯度!4d経度 が実際の地点）
    m = re.search(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)", url)
    latlng = (float(m.group(1)), float(m.group(2))) if m else None
    return name.strip(), addr.strip(), ftid, latlng


def h2a(s):
    """全角の数字・ハイフンを半角へ（ジオコーダに渡す用）。"""
    s = unicodedata.normalize("NFKC", s)
    return s.replace("−", "-").replace("ー", "-").replace("番地", "").replace("番", "-")


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def geocode(addr, name):
    """住所→座標。GSI（国土地理院）優先、ダメならNominatim。千葉県内かを必ず検証する。"""
    tries = []
    if addr:
        tries.append(("gsi", "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
                      + urllib.parse.quote(h2a(addr))))
    if name:
        tries.append(("osm", "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1"
                      "&accept-language=ja&countrycodes=jp&q=" + urllib.parse.quote(name + " 千葉県")))
    if addr:
        tries.append(("osm", "https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1"
                      "&accept-language=ja&countrycodes=jp&q=" + urllib.parse.quote(h2a(addr))))
    for src, url in tries:
        try:
            d = get_json(url)
        except Exception as e:
            print(f"  [{src}] 失敗: {e}", file=sys.stderr)
            continue
        if not d:
            continue
        if src == "gsi":
            lng, lat = d[0]["geometry"]["coordinates"]
        else:
            lat, lng = float(d[0]["lat"]), float(d[0]["lon"])
        if CHIBA[0] <= lat <= CHIBA[1] and CHIBA[2] <= lng <= CHIBA[3]:
            return lat, lng, src
        print(f"  [{src}] 千葉県外の座標 {lat},{lng} を棄却", file=sys.stderr)
    return None, None, None


def load():
    if not SPOTS.exists():
        return []
    t = SPOTS.read_text(encoding="utf-8")
    m = re.search(r"window\.SPOTS\s*=\s*(\[.*?\]);\s*$", t, re.S)
    return json.loads(m.group(1)) if m else []


def save(spots):
    body = json.dumps(spots, ensure_ascii=False, indent=2)
    SPOTS.write_text(f"// 行きたい場所リスト（add_spot.py が追記する。手で直してもよい）\nwindow.SPOTS = {body};\n",
                     encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", help="GoogleマップURL / 住所 / 店名")
    p.add_argument("--name"); p.add_argument("--addr"); p.add_argument("--area", default="")
    p.add_argument("--cat", default="その他"); p.add_argument("--note", default="")
    p.add_argument("--by", default=""); p.add_argument("--tag", action="append", default=[])
    a = p.parse_args()

    src_url = a.input if a.input.startswith("http") else ""
    if src_url:
        final = expand(src_url)
        name, addr, ftid, latlng = parse_gmap(final)
    else:
        name, addr, ftid, latlng = (a.input, a.input, "", None)
    name = a.name or name
    addr = a.addr or addr
    lat, lng, src = (latlng[0], latlng[1], "url") if latlng else geocode(addr, name)
    if lat is None:
        sys.exit(f"座標が取れなかった: {name} / {addr}")

    spots = load()
    key = ftid or name
    spots = [s for s in spots if (s.get("ftid") or s["name"]) != key]
    spots.append({"id": re.sub(r"\W+", "-", name.lower())[:40] or f"s{len(spots)+1}",
                  "name": name, "address": addr, "lat": round(lat, 6), "lng": round(lng, 6),
                  "area": a.area, "cat": a.cat, "tags": a.tag, "note": a.note, "by": a.by,
                  "gmap": src_url, "ftid": ftid, "added": date.today().isoformat()})
    save(spots)
    print(f"追加: {name}\n  住所: {addr}\n  座標: {lat},{lng} (出典 {src})\n  計 {len(spots)} 件")


if __name__ == "__main__":
    main()

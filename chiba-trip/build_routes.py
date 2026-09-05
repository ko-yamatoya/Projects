#!/usr/bin/env python3
"""route_plan.json + spots.js から routes.js（プラン一式）を生成する。

区間の距離・所要時間・道路の線形は OSRM（実際の道路網）から取る。
生成時に焼き込むので、公開ページ側は外部APIに依存しない。
プランを足したり順番を変えたら、このスクリプトを再実行する。

OSRM の所要時間は信号・渋滞を織り込まない素の値なので、
表示側で余裕を持たせられるよう、生の分数をそのまま残す。
"""
import json, re, subprocess, time
from pathlib import Path

HERE = Path(__file__).parent
OSRM = "https://router.project-osrm.org/route/v1/driving/"
CACHE = HERE / ".leg_cache.json"


def load_spots():
    t = (HERE / "spots.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.SPOTS\s*=\s*(\[.*?\]);\s*$", t, re.S).group(1))


def leg(a, b, cache):
    """2点間を道路でつなぐ。距離(km)・所要(分)・線形を返す。落ちたら直線にフォールバック。"""
    key = f'{a["lat"]},{a["lng"]}>{b["lat"]},{b["lng"]}'
    if key in cache:
        return cache[key]
    url = f'{OSRM}{a["lng"]},{a["lat"]};{b["lng"]},{b["lat"]}?overview=simplified&geometries=geojson'
    try:
        # urllib だと相手のTLS設定で握手に失敗することがあるので curl に投げる
        r = subprocess.run(["curl", "-sS", url], capture_output=True, text=True, timeout=40)
        d = json.loads(r.stdout)
        if d.get("code") != "Ok":
            raise RuntimeError(d.get("code"))
        r0 = d["routes"][0]
        out = {"dist": round(r0["distance"] / 1000, 1), "min": round(r0["duration"] / 60),
               "line": [[round(c[1], 5), round(c[0], 5)] for c in r0["geometry"]["coordinates"]],
               "src": "osrm"}
    except Exception as e:
        print(f'  ! OSRM失敗 ({e}) → 直線でつなぐ: {a["name"]} → {b["name"]}')
        out = {"dist": None, "min": None,
               "line": [[a["lat"], a["lng"]], [b["lat"], b["lng"]]], "src": "straight"}
    cache[key] = out
    time.sleep(1)   # 公共のデモサーバなので礼儀として間隔を空ける
    return out


def main():
    spots = {s["name"]: s for s in load_spots()}
    plan = json.loads((HERE / "route_plan.json").read_text(encoding="utf-8"))
    gates = plan["gateways"]
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}

    out = []
    for p in plan["plans"]:
        routes, p_dist, p_min, p_stay, partial = [], 0, 0, 0, False
        for r in p["routes"]:
            stops = []
            for st in r["stops"]:
                if "gate" in st:
                    g = gates[st["gate"]]
                    stops.append({"id": "", "name": g["name"], "lat": g["lat"], "lng": g["lng"],
                                  "stay": st.get("stay", g.get("stay", 0)),
                                  "memo": st.get("memo", g.get("memo", "")),
                                  "gate": True, "kind": g.get("kind", "gate"),
                                  "at": st.get("at"), "limit": st.get("limit")})
                else:
                    s = spots.get(st["spot"])
                    if not s:
                        raise SystemExit(f'spots.js に無い地点: {st["spot"]}')
                    stops.append({"id": s["id"], "name": s["name"], "lat": s["lat"], "lng": s["lng"],
                                  "stay": st.get("stay", 45), "memo": st.get("memo", ""),
                                  "gate": False, "kind": "spot",
                                  "at": st.get("at"), "limit": st.get("limit")})
            legs = []
            for a, b in zip(stops, stops[1:]):
                print(f'  {a["name"]} → {b["name"]}')
                legs.append(leg(a, b, cache))
            known = [l for l in legs if l["dist"] is not None]
            partial |= len(known) != len(legs)
            d = round(sum(l["dist"] for l in known), 1)
            m = sum(l["min"] for l in known)
            stay = sum(s["stay"] for s in stops)
            p_dist, p_min, p_stay = p_dist + d, p_min + m, p_stay + stay
            routes.append({**{k: r[k] for k in ("id", "day", "color", "note")},
                           "stops": stops, "legs": legs,
                           "dist": d, "min": m, "stay": stay})
        out.append({**{k: p[k] for k in ("id", "name", "tagline", "good", "hard", "who", "drops")},
                    "routes": routes,
                    "dist": round(p_dist, 1), "min": p_min, "stay": p_stay,
                    "spots": len({s["id"] for r in routes for s in r["stops"] if s["id"]}),
                    "partial": partial})

    CACHE.write_text(json.dumps(cache), encoding="utf-8")
    (HERE / "routes.js").write_text(
        "// プランとルート（build_routes.py が route_plan.json から生成。直接編集しない）\n"
        "window.PLANS = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")

    print()
    for p in out:
        h, mm = divmod(p["min"], 60)
        print(f'{p["name"]:<16} {p["spots"]}か所 / {p["dist"]:>5.1f}km / 運転 {h}時間{mm:02d}分'
              f' / 滞在 {p["stay"]//60}時間{p["stay"]%60:02d}分'
              + ("（一部直線）" if p["partial"] else ""))


if __name__ == "__main__":
    main()

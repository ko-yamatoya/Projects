#!/usr/bin/env python3
"""route_plan.json + spots.js から routes.js を生成する。

区間の距離・所要時間・道路の線形は OSRM（実際の道路網）から取る。
生成時に焼き込むので、公開ページ側は外部APIに依存しない。
スポットを足したり順番を変えたら、このスクリプトを再実行する。
"""
import json, re, subprocess, time
from pathlib import Path

HERE = Path(__file__).parent
OSRM = "https://router.project-osrm.org/route/v1/driving/"


def load_spots():
    t = (HERE / "spots.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"window\.SPOTS\s*=\s*(\[.*?\]);\s*$", t, re.S).group(1))


def leg(a, b):
    """2点間を道路でつなぐ。距離(m)・所要(秒)・線形を返す。落ちたら直線にフォールバック。"""
    url = f"{OSRM}{a['lng']},{a['lat']};{b['lng']},{b['lat']}?overview=simplified&geometries=geojson"
    try:
        # urllib だと相手のTLS設定で握手に失敗することがあるので curl に投げる
        r = subprocess.run(["curl", "-sS", url], capture_output=True, text=True, timeout=40)
        d = json.loads(r.stdout)
        if d.get("code") != "Ok":
            raise RuntimeError(d.get("code"))
        r0 = d["routes"][0]
        line = [[c[1], c[0]] for c in r0["geometry"]["coordinates"]]
        return {"dist": round(r0["distance"] / 1000, 1), "min": round(r0["duration"] / 60),
                "line": [[round(p[0], 5), round(p[1], 5)] for p in line], "src": "osrm"}
    except Exception as e:
        print(f"  ! OSRM失敗 ({e}) → 直線でつなぐ: {a['name']} → {b['name']}")
        return {"dist": None, "min": None,
                "line": [[a["lat"], a["lng"]], [b["lat"], b["lng"]]], "src": "straight"}


def main():
    spots = {s["name"]: s for s in load_spots()}
    plan = json.loads((HERE / "route_plan.json").read_text(encoding="utf-8"))
    out = []
    for r in plan["routes"]:
        stops = []
        for st in r["stops"]:
            if "spot" in st:
                s = spots.get(st["spot"])
                if not s:
                    raise SystemExit(f"spots.js に無い地点: {st['spot']}")
                stops.append({"id": s["id"], "name": s["name"], "lat": s["lat"], "lng": s["lng"],
                              "memo": st.get("memo", ""), "wp": False})
            else:
                stops.append({"id": "", "name": st["wp"], "lat": st["lat"], "lng": st["lng"],
                              "memo": st.get("memo", ""), "wp": True})
        legs = []
        for a, b in zip(stops, stops[1:]):
            print(f"  {a['name']} → {b['name']}")
            legs.append(leg(a, b))
            time.sleep(1)  # 公共のデモサーバなので礼儀として間隔を空ける
        known = [l for l in legs if l["dist"] is not None]
        out.append({"id": r["id"], "name": r["name"], "color": r["color"], "note": r["note"],
                    "stops": stops, "legs": legs,
                    "totalDist": round(sum(l["dist"] for l in known), 1) if known else None,
                    "totalMin": sum(l["min"] for l in known) if known else None,
                    "partial": len(known) != len(legs)})
    (HERE / "routes.js").write_text(
        "// 推奨ルート（build_routes.py が route_plan.json から生成。直接編集しない）\n"
        "window.ROUTES = " + json.dumps(out, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    for r in out:
        print(f'{r["name"]}: {r["totalDist"]}km / 移動 {r["totalMin"]}分 / {len(r["stops"])}地点')


if __name__ == "__main__":
    main()

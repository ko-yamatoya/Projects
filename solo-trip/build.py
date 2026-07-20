#!/usr/bin/env python3
"""
index.html を生成する。
_template.html の <!--INLINE_SVG--> に japan.svg を差し込むだけ。
地図SVGを外部読み込みにせず1ファイルに埋めるため（出先でも壊れない）。

使い方:  python3 build.py
経県値やプランを変えるだけなら data.js / plans.js を直接編集すればよく、
build は SVG や _template.html を触ったときだけ実行する。
"""
import pathlib, sys, re

here = pathlib.Path(__file__).parent
tpl = (here / "_template.html").read_text(encoding="utf-8")
svg = (here / "japan.svg").read_text(encoding="utf-8")

# XML宣言・DOCTYPE・コメントを落として <svg>…</svg> 本体だけ取り出す
m = re.search(r"<svg[\s\S]*?</svg>", svg)
if not m:
    sys.exit("japan.svg に <svg> が見つからない")
svg_body = m.group(0)

marker = "<!--INLINE_SVG-->"
if marker not in tpl:
    sys.exit("_template.html に " + marker + " がない")

out = tpl.replace(marker, svg_body)
(here / "index.html").write_text(out, encoding="utf-8")

# 47県ぶんの data-code が入っているか軽く検証
n = len(re.findall(r'data-code="\d+"', out))
print(f"index.html を生成: {len(out):,} bytes / prefecture data-code = {n}")
if n != 47:
    sys.exit(f"想定外: data-code が {n} 個（47のはず）")

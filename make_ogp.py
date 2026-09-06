# -*- coding: utf-8 -*-
"""basis.json から OGP 画像（1200x630 PNG）を生成する。

SNS や記事に貼られたときに、最新の指数値が画像側に焼き込まれている状態にする。
build.py のあとに実行する。

    py make_ogp.py        # -> ogp.png
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
W, H = 1200, 630

BG = (21, 24, 19)
INK = (233, 235, 228)
INK2 = (168, 176, 163)
INK3 = (118, 126, 113)
SHU = (228, 102, 74)
RULE = (47, 52, 44)

# 日本語フォント。上から順に試す。CI(Linux) と Windows の両方で動くようにしてある。
FONT_CANDIDATES = [
    # Linux（GitHub Actions。fonts-noto-cjk を入れておくこと）
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    # Windows
    r"C:\Windows\Fonts\YuGothB.ttc",
    r"C:\Windows\Fonts\meiryob.ttc",
    r"C:\Windows\Fonts\YuGothM.ttc",
    r"C:\Windows\Fonts\meiryo.ttc",
    r"C:\Windows\Fonts\msgothic.ttc",
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    raise SystemExit("日本語フォントが見つかりません。FONT_CANDIDATES を環境に合わせて追加してください。")


def main() -> None:
    b = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    d = b["deflator"]
    month = d["months"][-1]
    value = d["series"][d["primary"]][-1]
    prev_year = d["series"][d["primary"]][-13] if len(d["series"][d["primary"]]) > 13 else None
    yoy = (value / prev_year - 1) * 100 if prev_year else None

    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)

    # 方眼（サイトの背景と揃える）
    for x in range(0, W, 56):
        dr.line([(x, 0), (x, H)], fill=(28, 32, 26))
    for y in range(0, H, 56):
        dr.line([(0, y), (W, y)], fill=(28, 32, 26))

    dr.rectangle([0, 0, W, 8], fill=SHU)

    dr.text((72, 74), "大規模修繕統計ビューア", font=_font(40), fill=INK)
    dr.text((72, 132), "政府統計が、そのまま読める。", font=_font(24), fill=SHU)

    dr.line([(72, 196), (W - 72, 196)], fill=RULE, width=2)

    dr.text((72, 228), "建設工事費デフレーター「建築補修」", font=_font(26), fill=INK2)
    dr.text((72, 268), f"改装・改修工事の物価　{month}", font=_font(21), fill=INK3)

    big = _font(150)
    dr.text((72, 316), f"{value:.1f}", font=big, fill=INK)
    bw = dr.textlength(f"{value:.1f}", font=big)
    dr.text((72 + bw + 24, 420), "2020年度＝100", font=_font(24), fill=INK3)
    if yoy is not None:
        dr.text((72 + bw + 24, 372), f"前年同月比 {'+' if yoy >= 0 else '−'}{abs(yoy):.1f}%",
                font=_font(28), fill=SHU)

    dr.line([(72, 512), (W - 72, 512)], fill=RULE, width=2)
    dr.text((72, 534), "出典：国土交通省 建設工事費デフレーター（e-Stat API）", font=_font(22), fill=INK2)
    dr.text((72, 570), f"取得 {b['generated'].split()[0]}　制作・提供 株式会社第一技研", font=_font(20), fill=INK3)

    out = HERE / "ogp.png"
    img.save(out, "PNG", optimize=True)
    print(f"{out}  {out.stat().st_size:,} bytes  ({month} = {value})")


if __name__ == "__main__":
    main()

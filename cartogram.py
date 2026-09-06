# -*- coding: utf-8 -*-
"""47都道府県のタイル・カートグラム（地図データ不要）。

地理の形は捨て、1都道府県＝1タイルの等面積グリッドに置く。
面積の大小に引きずられず、値そのものを比べられるのが利点。
配置は下の TILES が唯一の定義。列は東ほど大きく、行は南ほど大きい。
"""
from __future__ import annotations

MONO = "IBM Plex Mono, monospace"

# 都道府県 → (列, 行)
TILES: dict[str, tuple[int, int]] = {
    "北海道": (13, 0),
    "青森県": (12, 1),
    "秋田県": (11, 2), "岩手県": (12, 2),
    "山形県": (11, 3), "宮城県": (12, 3),
    "石川県": (8, 4), "富山県": (9, 4), "新潟県": (10, 4), "福島県": (11, 4),
    "島根県": (3, 5), "鳥取県": (4, 5), "兵庫県": (5, 5), "京都府": (6, 5),
    "福井県": (7, 5), "岐阜県": (8, 5), "長野県": (9, 5), "群馬県": (10, 5),
    "栃木県": (11, 5), "茨城県": (12, 5),
    "山口県": (2, 6), "広島県": (3, 6), "岡山県": (4, 6), "大阪府": (5, 6),
    "滋賀県": (6, 6), "三重県": (7, 6), "愛知県": (8, 6), "山梨県": (9, 6),
    "埼玉県": (10, 6), "千葉県": (11, 6),
    "福岡県": (2, 7), "愛媛県": (3, 7), "香川県": (4, 7), "和歌山県": (5, 7),
    "奈良県": (6, 7), "静岡県": (8, 7), "神奈川県": (9, 7), "東京都": (10, 7),
    "佐賀県": (1, 8), "長崎県": (2, 8), "大分県": (3, 8), "高知県": (4, 8), "徳島県": (5, 8),
    "熊本県": (2, 9), "宮崎県": (3, 9),
    "鹿児島県": (2, 10),
    "沖縄県": (0, 11),
}

# タイルに入れる略称（2文字）
SHORT = {
    "北海道": "北海", "神奈川県": "神奈", "和歌山県": "和歌", "鹿児島県": "鹿児",
}

PITCH, SIZE = 58, 52
X0, Y0 = 30, 92


def _short(name: str) -> str:
    if name in SHORT:
        return SHORT[name]
    return name.rstrip("都道府県")[:2]


def cartogram(units: dict[str, int], highlight: tuple[str, ...] = (),
              links: dict[str, str] | None = None) -> str:
    """units: 都道府県名 → 戸数。highlight: 枠を強調。links: 都道府県名 → リンク先。"""
    missing = set(TILES) - set(units)
    if missing:
        raise SystemExit(f"配置表にあるが数値が無い都道府県: {sorted(missing)}")
    extra = set(units) - set(TILES)
    if extra:
        raise SystemExit(f"数値にあるが配置表に無い地域: {sorted(extra)}")

    # 六分位（同数ずつ）。値の偏りが大きいので等間隔ではなく順位で切る
    ordered = sorted(units.values())
    n = len(ordered)
    cuts = [ordered[round(n * k / 6)] for k in range(1, 6)]

    def bin_of(v: int) -> int:
        b = 0
        for c in cuts:
            if v >= c:
                b += 1
        return min(b, 5)

    s = ['<svg viewBox="0 0 900 790" role="img" aria-label="都道府県別の分譲マンション着工戸数タイルマップ。'
         + "、".join(f"{k}{v:,}戸" for k, v in list(sorted(units.items(), key=lambda kv: -kv[1]))[:5])
         + ' の順に多い。">']

    # 凡例
    s.append(f'<text x="{X0}" y="18" font-family="{MONO}" font-size="11.5" fill="var(--ink3)" '
             f'letter-spacing="1">単位：千戸　　少ない ← → 多い</text>')
    lw = 52
    for b in range(6):
        lx = X0 + b * lw
        s.append(f'<rect x="{lx}" y="28" width="{lw - 3}" height="14" fill="var(--b{b})"/>')
    s.append(f'<g font-family="{MONO}" font-size="10.5" fill="var(--ink3)">')
    s.append(f'<text x="{X0}" y="56">0</text>')
    for b, c in enumerate(cuts):
        s.append(f'<text x="{X0 + (b + 1) * lw}" y="56" text-anchor="middle">{round(c/1000)}</text>')
    s.append('</g>')

    # タイル
    for name, (col, row) in TILES.items():
        v = units[name]
        b = bin_of(v)
        x, y = X0 + col * PITCH, Y0 + row * PITCH
        stroke = ' stroke="var(--ink)" stroke-width="2"' if name in highlight else ''
        href = (links or {}).get(name)
        if href:
            s.append(f'<a href="{href}" aria-label="{name}の大規模修繕統計">')
        s.append(f'<rect x="{x}" y="{y}" width="{SIZE}" height="{SIZE}" rx="3" fill="var(--b{b})"{stroke}/>')
        s.append(f'<text x="{x + SIZE/2}" y="{y + 21}" text-anchor="middle" font-size="13" '
                 f'font-weight="600" fill="var(--b{b}f)">{_short(name)}</text>')
        s.append(f'<text x="{x + SIZE/2}" y="{y + 39}" text-anchor="middle" font-family="{MONO}" '
                 f'font-size="13" fill="var(--b{b}f)">{round(v/1000)}</text>')
        if href:
            s.append('</a>')

    # 凡例まで目を戻さなくて済むよう、東京タイルの下に単位と読み方を添える
    tx, ty = TILES["東京都"]
    ex, ey = X0 + tx * PITCH, Y0 + ty * PITCH + SIZE + 26
    s.append(f'<text x="{ex}" y="{ey}" font-family="{MONO}" font-size="12" fill="var(--ink3)">単位：千戸</text>')
    s.append(f'<text x="{ex}" y="{ey + 19}" font-family="{MONO}" font-size="11.5" fill="var(--ink3)">'
             f'例）東京 {round(units["東京都"]/1000)} ＝ {units["東京都"]/10000:.1f}万戸</text>')

    if highlight:
        s.append(f'<text x="{X0}" y="778" font-family="{MONO}" font-size="11.5" fill="var(--ink3)">'
                 f'太枠＝{"・".join(_short(h) for h in highlight)}（一都三県）</text>')
    s.append('</svg>')
    return "\n      ".join(s)

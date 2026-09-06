# -*- coding: utf-8 -*-
"""都道府県ページの下部へ差し込む「市区町村の内訳」ブロック。

**以前は、上（着工統計・フロー・分譲マンション）と下（住宅・土地統計・ストック・
非木造共同住宅）で出典も定義も期間も違い、同じ東京都が5.3倍ちがっていた。**
「ここから下は別の統計です」という帯の注意書きが、このモジュールの中身のほとんどだった。

都道府県ページの見出し数字をストック側へ統一したので、上下は同じ統計・同じ定義になり、
帯は要らなくなって消した。**上下で出典が違う状態に戻すなら、帯も戻すこと。**

build_pref.py から呼ばれる。逆向きに import しないこと（循環参照になる）。
"""
from __future__ import annotations


def city_section(basis: dict, pref_name: str) -> str:
    """一都三県以外は空文字を返す（basis に city が無いときも同様）。"""
    city = basis.get("city")
    if not city:
        return ""
    areas = city["areas"]
    cohort = city["cohort"]

    pre = next((c[:2] for c, a in areas.items() if a["pref"] == pref_name), None)
    if not pre:
        return ""

    def coh(a: dict) -> int:
        # .get(k, 0) にしないこと。コホートのラベルが periods に無いのは
        # 区分が変わったということで、0 として黙って足すと全ページが 0 戸になる。
        return sum(a["periods"][k] for k in cohort)

    leaves = sorted(
        ((c, a) for c, a in areas.items()
         if c[:2] == pre and a["is_leaf"] and not c.endswith("000")),
        key=lambda kv: -coh(kv[1]))
    if not leaves:
        return ""

    pref_v = coh(areas[pre + "000"]) if pre + "000" in areas else 0
    total = sum(coh(a) for _, a in leaves)

    h = []
    h.append('  <section>')
    h.append(f'    <h2><span class="idx">City</span>{pref_name}の市区町村別</h2>')
    h.append(f'    <p class="lede">{pref_name}の {len(leaves)} 市区町村を、'
             '築26〜45年の非木造共同住宅が多い順に並べています。'
             f'<strong>上の {pref_v:,}戸 と同じ統計・同じ定義</strong>です。'
             '市区町村名をクリックすると個別のページへ移動します。</p>')
    h.append('    <div class="prefgrid">')
    for code, a in leaves:
        h.append(f'<a href="../city/{code}.html"><span class="nm">{a["name"]}</span>'
                 f'<span class="vv">{coh(a):,}</span></a>')
    h.append('</div>')
    h.append(f'    <p class="colophon">単位：戸。{pref_name}全体は {pref_v:,}戸、'
             f'市区町村の合計は {total:,}戸。'
             f'差 {pref_v - total:,}戸 は個別に公表されない小規模町村の分です（標本調査のため）。</p>')
    h.append('    <p class="lede"><a href="../city/">一都三県の市区町村一覧を見る →</a></p>')
    h.append('  </section>')
    h.append('')
    return "\n".join(h)

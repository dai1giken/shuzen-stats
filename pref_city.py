# -*- coding: utf-8 -*-
"""都道府県ページの下部へ差し込む「市区町村の内訳」ブロック。

上（着工統計・フロー・分譲マンション）と下（住宅・土地統計・ストック・非木造共同住宅）で
**出典も定義も期間の取り方も違う**。混ぜて読まれると誤解になるので、境目を必ず明示する。
そのための注意書きが、このモジュールの中身のほとんどを占めている。

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
        return sum(a["periods"].get(k, 0) for k in cohort)

    leaves = sorted(
        ((c, a) for c, a in areas.items()
         if c[:2] == pre and a["is_leaf"] and not c.endswith("000")),
        key=lambda kv: -coh(kv[1]))
    if not leaves:
        return ""

    pref_v = coh(areas[pre + "000"]) if pre + "000" in areas else 0
    total = sum(coh(a) for _, a in leaves)
    survey = city["survey"]

    h = []
    h.append('  <section>')
    h.append(f'    <h2><span class="idx">City</span>{pref_name}の市区町村別</h2>')
    h.append('    <div class="srcband" style="margin-top:16px">')
    h.append('      <b>ここから下は別の統計です</b>')
    h.append('      上の戸数は<strong>着工統計</strong>')
    h.append('      〔その年度に着工した分譲マンションの数〕ですが、ここから下は')
    h.append(f'      <strong>{survey}</strong>')
    h.append('      〔2023年10月1日時点で現存する住宅の数〕です。')
    h.append('      絞り込みも「分譲マンション」ではなく<strong>「非木造の共同住宅」まで</strong>で、')
    h.append('      賃貸が混ざります。期間の取り方も違い、こちらは')
    h.append('      <strong>1981〜2000年建築＝2026年時点で築26〜45年</strong>です。')
    h.append('    </div>')
    h.append(f'    <p class="lede">{pref_name}の {len(leaves)} 市区町村を、'
             '築26〜45年の非木造共同住宅が多い順に並べています。'
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

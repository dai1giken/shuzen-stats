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

# 築26〜45年の非木造共同住宅がこの戸数に満たない市区町村は、ページを作らない。
#
# 一都三県210市区町村の実測では、1,000戸未満が37件あり、嵐山町（埼玉県）は 0戸 だった。
# 「嵐山町の大規模修繕統計｜築26〜45年 0戸」というページが公開されていた。
# 閾値1,000戸なら 210→173件 に減るが、戸数のカバー率は 99.5% を保つ。
# 日本でもっともマンションが密な一都三県ですらこうなる。
#
# 基準は機械的にしてページにも書く。「営業エリアだから」のような自社都合で選ばない。
MIN_UNITS = 1000


def label(areas: dict, code: str) -> str:
    """表示用の市区町村名。政令指定都市の区は、親の市名を前に付ける。

    住宅・土地統計の name は区名だけで、親の市名が入らない。そのまま出すと
    千葉市中央区が「中央区（千葉県）」になり、どこの中央区か分からない。
    同名の区は一都三県だけで4組、全国では「南区」12・「西区」12ある。

    **東京23区の親は「特別区部」で市ではないので付けない。**
    「特別区部中央区」は誤りで、東京都中央区が正しい。親名が「市」で終わる
    ときだけ前置する、という判定にしてあるのはこのため。全国へ広げても
    札幌市・大阪市・福岡市はすべて「市」で終わるのでそのまま効く。
    """
    a = areas[code]
    parent = a.get("parent")
    if parent and not parent.endswith("000"):
        pname = areas.get(parent, {}).get("name", "")
        if pname.endswith("市"):
            return pname + a["name"]
    return a["name"]


def cohort_sum(a: dict, cohort: list[str]) -> int:
    """築26〜45年の戸数。

    .get(k, 0) にしないこと。コホートのラベルが periods に無いのは区分が変わった
    ということで、0 として黙って足すと全ページが 0 戸になる。
    """
    return sum(a["periods"][k] for k in cohort)


def published_leaves(areas: dict, cohort: list[str], pre: str) -> list[tuple[str, dict]]:
    """その都県で「ページを作る」市区町村を、戸数の多い順に返す。

    順位も近隣リンクも一覧もこの結果から作る。ここを一本にしておかないと、
    閾値で落とした市区町村へのリンクが残って404になる。
    """
    return sorted(((c, a) for c, a in areas.items()
                   if c[:2] == pre and a["is_leaf"] and not c.endswith("000")
                   and cohort_sum(a, cohort) >= MIN_UNITS),
                  key=lambda kv: -cohort_sum(kv[1], cohort))


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
        return cohort_sum(a, cohort)

    leaves = published_leaves(areas, cohort, pre)
    if not leaves:
        return ""

    pref_v = coh(areas[pre + "000"]) if pre + "000" in areas else 0
    total = sum(coh(a) for _, a in leaves)
    # 閾値で落とした市区町村。差の内訳を分けて書くために数えておく
    dropped = [(c, a) for c, a in areas.items()
               if c[:2] == pre and a["is_leaf"] and not c.endswith("000")
               and coh(a) < MIN_UNITS]

    h = []
    h.append('  <section>')
    h.append(f'    <h2><span class="idx">City</span>{pref_name}の市区町村別</h2>')
    h.append(f'    <p class="lede">{pref_name}の {len(leaves)} 市区町村を、'
             '築26〜45年の非木造共同住宅が多い順に並べています。'
             f'<strong>上の {pref_v:,}戸 と同じ統計・同じ定義</strong>です。'
             '市区町村名をクリックすると個別のページへ移動します。</p>')
    h.append('    <div class="prefgrid">')
    for code, a in leaves:
        h.append(f'<a href="../city/{code}.html"><span class="nm">{label(areas, code)}</span>'
                 f'<span class="vv">{coh(a):,}</span></a>')
    h.append('</div>')
    drop_v = sum(coh(a) for _, a in dropped)
    h.append(f'    <p class="colophon">単位：戸。{pref_name}全体は {pref_v:,}戸、'
             f'上に並べた {len(leaves)} 市区町村の合計は {total:,}戸。'
             f'差 {pref_v - total:,}戸 の内訳は、'
             f'築26〜45年が {MIN_UNITS:,}戸 未満のため個別ページを作っていない '
             f'{len(dropped)} 市区町村ぶん {drop_v:,}戸 と、'
             f'個別に公表されない小規模町村ぶん {pref_v - total - drop_v:,}戸 です'
             f'（標本調査のため）。</p>')
    h.append('    <p class="lede"><a href="../city/">一都三県の市区町村一覧を見る →</a></p>')
    h.append('  </section>')
    h.append('')
    return "\n".join(h)

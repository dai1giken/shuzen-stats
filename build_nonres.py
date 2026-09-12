# -*- coding: utf-8 -*-
"""非住宅建築物（事務所・店舗・倉庫ほか）のページを生成する。

    py build_nonres.py      # build.py から呼ばれる（basis.json が要る）

出力: nonres/<用途スラッグ>.html ／ nonres/index.html

--- 住宅ページとの決定的な違い -------------------------------------------
**これは着工（フロー）であって、ストックではない。**
その年度に着工した棟数と床面積であり、いま現存する棟数ではない。
取り壊しも用途変更も反映しない。

住宅側（pref/ と city/）は住宅・土地統計＝ストックを見出しに使っている。
性格が違うものを同じ顔で出すと、以前あった「同じ東京都が5.3倍ちがう」問題と
同じことになる。**ページには必ず「着工の累計」と書くこと。**

--- 収録期間の制約 -------------------------------------------------------
この統計表は2003年度以降しか収録していない。2026年時点で最も古いものが築23年。
**それ以前に建った建物は、実際には存在するがこの数字に入っていない。**
つまりここに出る棟数は実際のストックより小さい。誤差の向きをページに書くこと。

--- なぜ「再掲」の6区分を使うのか ---------------------------------------
産業分類（A居住専用住宅〜R他に分類されない建築物）ではなく、
事務所・店舗・工場・倉庫・学校の校舎・病院診療所という建物の呼び方を使う。
探している人が使う言葉に近く、そのまま見出しになる。
"""
from __future__ import annotations

import json
from pathlib import Path

from build_pref import (CSS, CTA_BUILDING, SITE_URL, bar_cell, cite_block,
                        head, ref_ages, year_chart)

HERE = Path(__file__).resolve().parent

SLUG = {"事務所": "office", "店舗": "shop", "工場・作業場": "factory",
        "倉庫": "warehouse", "学校の校舎": "school", "病院・診療所": "hospital"}

# 用途ごとの一文。**公表統計の定義の言い換えに留める。**
# 「オーナーが多い」「発注が早い」のような当社の見立ては書かない。
NOTE = {
    "事務所": "オフィスビル、事業所の事務棟など。",
    "店舗": "物販店、飲食店、ショッピングセンターなど。",
    "工場・作業場": "製造の工場、作業場、整備場など。",
    "倉庫": "物流施設、保管倉庫、配送センターなど。",
    "学校の校舎": "小中高、大学、専門学校の校舎。",
    "病院・診療所": "病院、診療所、介護・福祉の施設を含みます。",
}

FOOT = CTA_BUILDING + """
  <a class="cta" href="index.html">
    <span class="k">用途別の一覧へ</span>
    <span class="n">首都圏の非住宅建築物</span>
    <span class="d">事務所・店舗・工場・倉庫・学校・病院を並べて比べられます</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{site}#calc">
    <span class="k">Tool ／ 自分の物件で試す</span>
    <span class="n">修繕積立金と工事費を並べる</span>
    <span class="d">戸数と積立の条件を入れると、入力した積立額と、実態調査の分布に戸数を掛けた額とを並べて表示します。見積でも、必要額の算定でも、助言でもありません</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{site}">
    <span class="k">全国の統計へ</span>
    <span class="n">大規模修繕統計ビューア</span>
    <span class="d">住宅（分譲・賃貸）のストックは都道府県別・市区町村別に出しています</span>
    <span class="arrow">→</span>
  </a>

  <a class="sitelink" href="https://dai1giken.co.jp/" target="_blank" rel="noopener">
    <span class="k">制作・提供</span>
    <span class="n">株式会社第一技研</span>
    <span class="d">マンション・ビルの外装大規模修繕　dai1giken.co.jp</span>
    <span class="arrow">→</span>
  </a>

  <p class="credit">この統計データは、政府統計総合窓口(e-Stat)のAPI機能を使用していますが、内容は国によって保証されたものではありません。<br>
  本ページの図表・数値は、出典の明記だけで自由に転載できます（CC BY 4.0）。</p>
</div>
</body>
</html>
"""


def _sum(d: dict, prefs: list[str], years: list[int]) -> int:
    """指定した都県・年度の合計。欠測は 0 として扱わず、無い年度は飛ばす。"""
    t = 0
    for p in prefs:
        s = d.get(p, {})
        for y in years:
            t += s.get(str(y), 0)
    return t


def build(basis: dict) -> int:
    nr = basis.get("nonres")
    if not nr:
        return 0
    ref, _, _ = ref_ages(basis)
    day = basis["generated"].split()[0]
    years = nr["years"]
    prefs = nr["prefs"]
    bld, flo = nr["buildings"], nr["floor_m2"]

    # 築13〜23年＝1回目から2回目の修繕期にあたる層。着工年度から引き算で決める。
    # 直書きすると年が明けたときに古くなる。
    old = [y for y in years if ref - y >= 13]
    new = [y for y in years if ref - y < 13]
    age_lo, age_hi = ref - max(old), ref - min(old)

    out = HERE / "nonres"
    out.mkdir(exist_ok=True)
    written = []

    # 全用途の首都圏合計。順位と一覧に使う
    totals = {u: _sum(bld[u], prefs, old) for u in nr["uses"]}
    ranked = sorted(nr["uses"], key=lambda u: -totals[u])

    for use in nr["uses"]:
        slug = SLUG[use]
        n_old = totals[use]
        n_all = _sum(bld[use], prefs, years)
        m2_old = _sum(flo[use], prefs, old)
        nat_old = _sum(bld[use], list(bld[use]), old)
        share = n_old / nat_old * 100 if nat_old else 0
        rank = ranked.index(use) + 1

        canonical = f"{SITE_URL}nonres/{slug}.html"
        title = f"首都圏の{use}の大規模修繕統計｜築{age_lo}〜{age_hi}年 {n_old:,}棟"
        desc = (f"一都三県で{min(old)}〜{max(old)}年度に着工した{use}は {n_old:,}棟。"
                f"{ref}年時点で築{age_lo}〜{age_hi}年、1回目から2回目の修繕周期にあたります。"
                "国土交通省「建築着工統計」の公表値。")

        h = [head(title, desc, canonical, crumb="非住宅")]
        h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて国土交通省「建築着工統計調査」の公表値です。</strong>
    e-Stat の API から取得し、<strong>用途と都県で絞って年度を合計するところまで</strong>を行っています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表統計 ／ 一都三県</span>
  <h1>首都圏の{use}
    <span class="sub">一都三県で{min(old)}〜{max(old)}年度に着工した{use}は <strong>{n_old:,}棟</strong>。{ref}年時点で築{age_lo}〜{age_hi}年、大規模修繕の1回目から2回目にあたります。{NOTE[use]}</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">築{age_lo}〜{age_hi}年の{use}</span>
      <div class="v">{n_old:,}<small>棟</small></div>
      <p>延べ床面積 {m2_old:,} m²。全国同期間の {share:.1f}%。</p>
    </div>
    <div class="kpi">
      <span class="k">用途別の順位</span>
      <div class="v">{rank}<small>位 / {len(nr["uses"])}</small></div>
      <p>一都三県の非住宅建築物のうち、築{age_lo}〜{age_hi}年の棟数で。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig.</span>一都三県の{use}（着工年度別）</h2>
    <p class="lede">各年度に着工した棟数です。朱色の期間が、{ref}年時点で築{age_lo}〜{age_hi}年にあたります。棒にカーソルを重ねると実数が出ます。</p>
    <div class="chartbox">
      {year_chart({str(y): _sum(bld[use], prefs, [y]) for y in years}, min(old), max(old), ref)}
      <div class="chart-foot">
        出典：{nr["name"]}／<a href="{nr["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={nr["statsDataId"]}</a><br>
        {nr["filter"]}　取得日 {day}
      </div>
    </div>
  </section>
''')

        rows = []
        _pmax = max(_sum(bld[use], [p], old) for p in prefs)
        for p in sorted(prefs, key=lambda p: -_sum(bld[use], [p], old)):
            po, pa = _sum(bld[use], [p], old), _sum(bld[use], [p], years)
            pm = _sum(flo[use], [p], old)
            rows.append(f'<tr><td>{p}</td>'
                        + bar_cell(f'{po:,}', po, 0, _pmax, "var(--ai)")
                        + f'<td class="n">{pm:,}</td><td class="n">{pa:,}</td></tr>')
        h.append(f'''  <section>
    <h2><span class="idx">Area</span>都県別の{use}</h2>
    <p class="lede">築{age_lo}〜{age_hi}年（{min(old)}〜{max(old)}年度着工）が多い順です。</p>
    <div class="tablebox"><table>
      <thead><tr><th>都県</th><th>築{age_lo}〜{age_hi}年</th><th>延べ床面積</th><th>{min(years)}〜{max(years)}年度 計</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table></div>
    <p class="colophon">単位：棟／m²。出典：{nr["name"]}（statsDataId={nr["statsDataId"]}）。着工の累計で、現存する棟数ではありません。</p>
  </section>
''')

        near = []
        for u2 in ranked:
            cls = ' class="me"' if u2 == use else ''
            nm = u2 if u2 == use else f'<a href="{SLUG[u2]}.html">{u2}</a>'
            near.append(f'<tr{cls}><td class="n">{ranked.index(u2)+1}</td><td>{nm}</td>'
                        + bar_cell(f'{totals[u2]:,}', totals[u2], 0,
                                   max(totals.values()), "var(--ai)") + '</tr>')
        h.append(f'''  <section>
    <h2><span class="idx">Rank</span>用途別の比較（一都三県）</h2>
    <div class="tablebox"><table>
      <thead><tr><th>順位</th><th>用途</th><th>築{age_lo}〜{age_hi}年</th></tr></thead>
      <tbody>{"".join(near)}</tbody>
    </table></div>
    <p class="lede"><a href="index.html">首都圏の非住宅建築物の一覧を見る →</a></p>
  </section>

  <div class="warn">
    <h4>読むときの注意</h4>
    <ul>
      <li><strong>これは着工（フロー）の累計で、現存する棟数ではありません。</strong>その年度に着工した建物の数で、取り壊しや用途変更は反映していません。</li>
      <li><strong>{min(years)}年度より前に建った建物は入っていません。</strong>この統計表の収録がそこから始まるためで、実際の建物はこれより多く存在します。数字は少なめに出ます。</li>
      <li>大規模修繕の実施周期は<strong>12〜15年程度が目安</strong>（国土交通省ガイドライン）で、築年数だけで実施時期が決まるものではありません。</li>
      <li>用途は着工時の区分です。その後の用途変更は反映していません。</li>
    </ul>
  </div>
''')
        h.append(cite_block(canonical, day))
        h.append(FOOT.format(site=SITE_URL))
        (out / f"{slug}.html").write_text("".join(h), encoding="utf-8")
        written.append(slug)

    # ---- 一覧 ----
    canonical = f"{SITE_URL}nonres/"
    tot_old = sum(totals.values())
    idx = [head("首都圏の非住宅建築物 大規模修繕統計",
                f"一都三県で{min(old)}〜{max(old)}年度に着工した事務所・店舗・工場・倉庫・学校・病院は"
                f"あわせて {tot_old:,}棟。{ref}年時点で築{age_lo}〜{age_hi}年。"
                "国土交通省「建築着工統計」の公表値。",
                canonical, crumb="非住宅")]
    idx.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて国土交通省「建築着工統計調査」の公表値です。</strong>
  </div>

  <span class="toplabel">公表統計 ／ 一都三県</span>
  <h1>首都圏の非住宅建築物
    <span class="sub">一都三県で{min(old)}〜{max(old)}年度に着工した非住宅建築物は <strong>{tot_old:,}棟</strong>。{ref}年時点で築{age_lo}〜{age_hi}年、大規模修繕の1回目から2回目にあたります。<strong>着工の累計であって、現存する棟数ではありません。</strong></span>
  </h1>

  <div class="prefgrid">''')
    for u in ranked:
        idx.append(f'<a href="{SLUG[u]}.html"><span class="nm">{u}</span>'
                   f'<span class="vv">{totals[u]:,}</span></a>')
    idx.append(f'''</div>
  <p class="colophon">単位：棟。築{age_lo}〜{age_hi}年（{min(old)}〜{max(old)}年度着工）の多い順。
  {min(years)}年度より前に建った建物は、この統計表に収録がないため入っていません。</p>

  <div class="warn">
    <h4>住宅のページとの違い</h4>
    <ul>
      <li>このページは<strong>着工（フロー）</strong>です。都道府県別・市区町村別の住宅ページは<strong>現存ストック</strong>（住宅・土地統計調査）で、出典も定義も違います。<strong>直接は比べられません。</strong></li>
      <li>住宅のストックを見る場合は <a href="../pref/">都道府県別</a> ／ <a href="../city/">市区町村別</a> をご覧ください。</li>
    </ul>
  </div>
''')
    idx.append(cite_block(canonical, day))
    idx.append(FOOT.format(site=SITE_URL))
    (out / "index.html").write_text("".join(idx), encoding="utf-8")

    # 用途が減ったときに古いページを残さない
    keep = {f"{s}.html" for s in written} | {"index.html"}
    for p in sorted(out.glob("*.html")):
        if p.name not in keep:
            p.unlink()

    return len(written)


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    print(f"nonres/ に {build(basis)} 用途 ＋ 一覧を生成しました")


if __name__ == "__main__":
    main()

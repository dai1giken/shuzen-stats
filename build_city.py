# -*- coding: utf-8 -*-
"""一都三県の市区町村別ページと一覧を生成する。

    py build_city.py        # build.py から呼ばれる（basis.json が要る）

出力: city/<JISコード>.html ／ city/index.html

--- なぜ着工統計ではなく住宅・土地統計を使うのか -------------------------
都道府県ページ（pref/）は着工統計＝フロー。その年に何戸着工したかであって、
いま何戸建っているかではない。取り壊しも用途変更も反映されない。
市区町村ページは住宅・土地統計＝ストック。現存する住宅を数えている。
**修繕の対象は現存ストックなので、こちらのほうが指標として正しい。**

--- 引き換えに失うもの ---------------------------------------------------
この表には所有関係（持ち家／借家）の軸が無い。だから絞れるのは
「非木造の共同住宅」までで、**分譲と賃貸が混ざる**。ページに明記すること。

--- URL にローマ字を使わない理由 -----------------------------------------
210市区町村分のローマ字表記を手で用意すると誤りが混入する。JISコードなら
一意で、市町村合併があっても追跡できる。読みやすさは title と本文で担保する。
"""
from __future__ import annotations

import json
from pathlib import Path

from build_pref import CSS, SITE_URL, SLUG, head, MONO

HERE = Path(__file__).resolve().parent


def unit(pref_name: str) -> str:
    """東京都→「都」、北海道→「道」、大阪府→「府」、それ以外→「県」。
    ラベルを「県全体」「県内比」と決め打ちにすると東京都で誤りになる。"""
    return pref_name[-1] if pref_name[-1] in "都道府県" else "県"

FOOT_T = """
  <a class="cta" href="{back}">
    <span class="k">都道府県の統計へ</span>
    <span class="n">{pref}の大規模修繕統計</span>
    <span class="d">{whole}の戸数と、順位の近い都道府県</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{site}">
    <span class="k">全国の統計へ</span>
    <span class="n">大規模修繕統計ビューア</span>
    <span class="d">工事費指数・戸あたり工事金額・修繕周期・積立金は全国共通です</span>
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


def period_chart(periods: dict[str, int], cohort: list[str]) -> str:
    """建築の時期別の住宅数。コホートの帯だけ朱で塗る。"""
    labels = list(periods)
    vals = [periods[k] for k in labels]
    n = len(labels)
    x0, x1, ytop, ybase = 96, 872, 34, 250
    ymax = max(vals) or 1
    step = 10 ** (len(str(int(ymax))) - 1)
    top = -(-ymax // step) * step
    slot = (x1 - x0) / n
    bw = slot - 10

    def Y(v):
        return ybase - v / top * (ybase - ytop)

    s = [f'<svg viewBox="0 0 900 320" role="img" aria-label="建築の時期別の非木造共同住宅数。'
         + "、".join(f"{k}は{v:,}戸" for k, v in periods.items()) + '。">']
    s.append('<g stroke="var(--rule-soft)" stroke-width="1">')
    for k in range(1, 5):
        y = ybase - (ybase - ytop) * k / 4
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
    s.append('</g>')
    s.append(f'<g font-family="{MONO}" font-size="11" fill="var(--ink3)" text-anchor="end">')
    for k in range(0, 5):
        y = ybase - (ybase - ytop) * k / 4
        s.append(f'<text x="{x0 - 9}" y="{y + 4:.1f}">{int(top * k / 4):,}</text>')
    s.append('</g>')
    s.append(f'<text x="{x0}" y="20" font-family="{MONO}" font-size="10.5" fill="var(--ink3)">戸</text>')
    s.append(f'<line x1="{x0}" y1="{ybase}" x2="{x1}" y2="{ybase}" stroke="var(--rule)"/>')

    for i, (lb, v) in enumerate(zip(labels, vals)):
        on = lb in cohort
        x = x0 + i * slot + 5
        yy = Y(v)
        s.append(f'<rect x="{x:.1f}" y="{yy:.1f}" width="{bw:.1f}" height="{ybase - yy:.1f}" rx="3" '
                 f'fill="{"var(--shu)" if on else "var(--ai)"}" opacity="{1 if on else 0.42}"/>')
        s.append(f'<text x="{x + bw/2:.1f}" y="{yy - 7:.1f}" text-anchor="middle" font-family="{MONO}" '
                 f'font-size="11.5" fill="{"var(--shu)" if on else "var(--ink3)"}">{v:,}</text>')
        s.append(f'<text x="{x + bw/2:.1f}" y="{ybase + 17}" text-anchor="middle" font-family="{MONO}" '
                 f'font-size="10.5" fill="var(--ink3)">{lb.replace("年", "").replace("～", "-")}</text>')

    s.append(f'<g font-family="{MONO}" font-size="11">')
    s.append(f'<rect x="{x0}" y="290" width="24" height="10" rx="2" fill="var(--shu)"/>')
    s.append(f'<text x="{x0 + 31}" y="299" fill="var(--ink2)">1981〜2000年建築＝2026年時点で築26〜45年</text>')
    s.append('</g></svg>')
    return "\n      ".join(s)


def build(basis: dict) -> int:
    city = basis["city"]
    areas = city["areas"]
    cohort = city["cohort"]
    day = basis["generated"].split()[0]

    def coh(a):
        # .get(k, 0) にしないこと。理由は pref_city.py の同名関数と同じ。
        return sum(a["periods"][k] for k in cohort)

    # 都県ごとに、集計行を除いた市区町村で順位を作る
    ranks: dict[str, dict[str, int]] = {}
    leaves: dict[str, list] = {}
    for pre in {c[:2] for c in areas}:
        lv = sorted(((c, a) for c, a in areas.items()
                     if c[:2] == pre and a["is_leaf"] and not c.endswith("000")),
                    key=lambda kv: -coh(kv[1]))
        leaves[pre] = lv
        ranks[pre] = {c: i + 1 for i, (c, _) in enumerate(lv)}

    out = HERE / "city"
    out.mkdir(exist_ok=True)
    written = []

    for code, a in areas.items():
        if code.endswith("000"):          # 都県の行はページにしない（pref/ が担当）
            continue
        pre = code[:2]
        name, pref_name = a["name"], a["pref"]
        u = unit(pref_name)
        v = coh(a)
        total = a["total"]
        share = v / total * 100 if total else 0
        r = ranks[pre].get(code)
        pref_v = coh(areas[pre + "000"]) if pre + "000" in areas else 0
        pshare = v / pref_v * 100 if pref_v else 0
        canonical = f"{SITE_URL}city/{code}.html"
        full = f"{pref_name}{name}" if not name.endswith(("都", "県")) else name
        title = f"{name}（{pref_name}）の大規模修繕統計｜築26〜45年の共同住宅 {v:,}戸"
        desc = (f"{name}の非木造共同住宅のうち、1981〜2000年に建築されたものは{v:,}戸。"
                f"2026年時点で築26〜45年、大規模修繕の2〜3回目にあたります。"
                f"令和5年住宅・土地統計調査（国土交通省・総務省）の公表値。")

        h = [head(title, desc, canonical)]
        rank_html = (f'<div class="v">{r}<small>位 / {len(leaves[pre])}</small></div>'
                     f'<p>{pref_name}の市区町村のうち。{u}全体 {pref_v:,}戸 の {pshare:.1f}%。</p>'
                     if r else
                     f'<div class="v">—</div><p>区の合計にあたる行のため、順位は付けていません。'
                     f'{u}全体 {pref_v:,}戸 の {pshare:.1f}%。</p>')

        h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて{city["survey"]}の公表値です。</strong>
    e-Stat の API から取得し、期間の合計以外の加工はしていません。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表統計 ／ {pref_name}</span>
  <h1>{name}の大規模修繕統計
    <span class="sub">{name}の非木造共同住宅のうち、<strong>1981〜2000年に建築されたものは {v:,}戸</strong>。2026年時点で築26〜45年、大規模修繕の2回目から3回目にあたります。</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">築26〜45年の共同住宅</span>
      <div class="v">{v:,}<small>戸</small></div>
      <p>1981〜2000年建築。{name}の非木造共同住宅 {total:,}戸 の {share:.1f}%。</p>
    </div>
    <div class="kpi">
      <span class="k">{pref_name}内の順位</span>
      {rank_html}
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig.</span>{name}の非木造共同住宅（建築の時期別）</h2>
    <p class="lede">2023年10月1日時点で現存する住宅の数です。朱色の2本が、2026年時点で築26〜45年にあたります。</p>
    <div class="chartbox">
      {period_chart(a["periods"], cohort)}
      <div class="chart-foot">
        出典：{city["survey"]}／<a href="{city["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={city["statsDataId"]}</a><br>
        {city["filter"]}　取得日 {day}
      </div>
    </div>
  </section>
''')

        if r:
            i = r - 1
            near = leaves[pre][max(0, i - 2): i + 3]
            h.append(f'''  <section>
    <h2><span class="idx">Rank</span>{pref_name}内で順位の近い市区町村</h2>
    <div class="tablebox"><table>
      <thead><tr><th>順位</th><th>市区町村</th><th>築26〜45年</th><th>{u}内比</th></tr></thead>
      <tbody>''')
            for c2, a2 in near:
                cls = ' class="me"' if c2 == code else ''
                v2 = coh(a2)
                nm2 = a2["name"] if c2 == code else f'<a href="{c2}.html">{a2["name"]}</a>'
                h.append(f'<tr{cls}><td class="n">{ranks[pre][c2]}</td><td>{nm2}</td>'
                         f'<td class="n">{v2:,}</td><td class="n">{v2/pref_v*100:.1f}%</td></tr>')
            h.append('</tbody></table></div>\n    <p class="lede"><a href="index.html">'
                     '一都三県の市区町村一覧を見る →</a></p>\n  </section>\n')

        h.append(f'''  <div class="warn">
    <h4>この数字が指しているもの</h4>
    <ul>
      <li><strong>分譲と賃貸の区別はありません。</strong>この統計表には所有関係の軸が無く、絞り込めるのは「非木造の共同住宅」までです。賃貸マンションも含まれています。</li>
      <li><strong>標本調査にもとづく推計値です。</strong>全数調査ではありません。また小規模な町村は個別に公表されないため、市区町村の合計は{u}の値と一致しません（一都三県で0.1〜0.5%の差）。</li>
      <li>大規模修繕の実施周期は<strong>12〜15年程度が目安</strong>（国土交通省ガイドライン）で、築年数だけで実施時期が決まるものではありません。</li>
    </ul>
  </div>
''')
        h.append(FOOT_T.format(back=f"../pref/{SLUG[pref_name]}.html", pref=pref_name,
                               whole=f"{u}全体", site=SITE_URL))
        (out / f"{code}.html").write_text("".join(h), encoding="utf-8")
        written.append(code)

    # ---- 一覧 ----
    canonical = f"{SITE_URL}city/"
    idx = [head("一都三県の市区町村別 大規模修繕統計",
                "東京・神奈川・埼玉・千葉の市区町村別に、築26〜45年の非木造共同住宅の戸数を並べています。令和5年住宅・土地統計調査。",
                canonical)]
    idx.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて{city["survey"]}の公表値です。</strong>
  </div>

  <span class="toplabel">公表統計 ／ 一都三県</span>
  <h1>一都三県の市区町村別
    <span class="sub">非木造共同住宅のうち1981〜2000年に建築されたもの＝2026年時点で築26〜45年の戸数です。分譲と賃貸の区別はありません。</span>
  </h1>
''')
    for pre in ["13", "14", "11", "12"]:
        if pre not in leaves:
            continue
        pname = basis["city"]["areas"][pre + "000"]["pref"]
        idx.append(f'<section><h2><span class="idx">{pname}</span>'
                   f'{len(leaves[pre])} 市区町村</h2>\n  <div class="prefgrid">')
        for c2, a2 in leaves[pre]:
            idx.append(f'<a href="{c2}.html"><span class="nm">{a2["name"]}</span>'
                       f'<span class="vv">{coh(a2):,}</span></a>')
        idx.append('</div></section>\n')
    idx.append('  <p class="colophon">単位：戸。多い順。集計行（特別区部・政令市）は一覧から除いています。</p>\n')
    idx.append(FOOT_T.format(back="../pref/", pref="都道府県別",
                             whole="都道府県全体", site=SITE_URL))
    (out / "index.html").write_text("".join(idx), encoding="utf-8")

    return len(written)


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    print(f"city/ に {build(basis)} ページ ＋ 一覧を生成しました")


if __name__ == "__main__":
    main()

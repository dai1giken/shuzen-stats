# -*- coding: utf-8 -*-
"""改修市場（建築物リフォーム・リニューアル調査）のページを生成する。

    py build_reform.py      # build.py から呼ばれる（basis.json が要る）

出力: reform/index.html ／ reform/<用途スラッグ>.html

--- nonres/ と混同しないこと（最重要） -----------------------------------
`nonres/` は**建築着工統計**で「その年度に何棟**建った**か」（棟・フロー）。
`reform/` は**建築物リフォーム・リニューアル調査**で「いくら**改修を受注**したか」
（億円）。**同じ用途名（事務所・倉庫・学校…）が両方に出る。**

v1.0 で「同じページの上と下で東京都が5.3倍ちがう」事故を起こしている。
同じ轍を踏まないよう、**両方のページに相手方へのリンクと違いの説明を置く**。
数字を同じ図・同じ表に並べない。

--- 単位は億円 -----------------------------------------------------------
e-Stat の @unit がそうなっている。円に直さない。桁を間違えると誰も気づけない。

--- 書いてよいこと ------------------------------------------------------
公表値と、そこから引き算・割り算で出る比較まで。
**「だから今が発注の好機」のような結びは書かない。**当社は工事を受ける側で、
市場が伸びているという結論は当社に利がある。書いた時点でポジショントークになる。
"""
from __future__ import annotations

import json
from pathlib import Path

from build_consultation import link as consult_link
from build_pref import (CSS, SITE_URL, bar_cell, cta_building,  # noqa: F401
                        cite_block, foot, head)

HERE = Path(__file__).resolve().parent

# (basis 上の用途名, スラッグ, 見出し名)
# **e-Stat の用途名をキーにする。**読みやすい名前に置き換えるのは表示だけ。
USES: list[tuple[str, str, str]] = [
    ("非住宅建築物_事務所", "office", "事務所"),
    ("非住宅建築物_生産施設（工場、作業場）", "factory", "生産施設（工場・作業場）"),
    ("非住宅建築物_倉庫・流通施設", "warehouse", "倉庫・流通施設"),
    ("非住宅建築物_学校の校舎", "school", "学校の校舎"),
    ("非住宅建築物_物販店舗", "shop", "物販店舗"),
    ("非住宅建築物_飲食店", "restaurant", "飲食店"),
    ("非住宅建築物_医療施設", "medical", "医療施設"),
    ("非住宅建築物_宿泊施設", "hotel", "宿泊施設"),
    ("非住宅建築物_老人福祉施設", "welfare", "老人福祉施設"),
    ("非住宅建築物_その他の非住宅建築物", "other", "その他の非住宅建築物"),
    ("住宅_共同住宅_共用部分", "kyoyo", "共同住宅の共用部分"),
    ("住宅_共同住宅", "kyodo", "共同住宅"),
]
assert len({s for _, s, _ in USES}) == len(USES), "スラッグが重複しています"

METRO = ["東京都", "神奈川県", "千葉県", "埼玉県"]
STRUCT = ["木造", "コンクリート系構造（RC、SRC、など）",
          "鉄骨造（重量鉄骨造、軽量鉄骨造）", "その他（不明含む）"]


def _pct(a, b) -> float:
    return (a / b - 1) * 100 if (a and b) else 0.0


def _sign(v: float) -> str:
    return f"{v:+.0f}%"


def _y(row: list, i: int = -1) -> float:
    """欠測を 0 として読む。**合計に混ぜるときだけ使うこと。**"""
    try:
        return row[i] or 0.0
    except (IndexError, TypeError):
        return 0.0


def area_group(name: str) -> str:
    """施工地域を束ねる。全国・都道府県・政令市が同じ表に混ざると比較が崩れる。"""
    if name == "全国":
        return "全国"
    if name == "不明":
        return "不明"
    if name.endswith(("都", "道", "府", "県")):
        return "都道府県"
    return "市・特別区部"


def year_bars(years: list[str], vals: list, label: str,
              color: str = "var(--ai)") -> str:
    """年度別の受注高を棒で描く。金額なので 0 起点にする（途中から始めない）。"""
    W, H = 960, 320
    L, R, T, B = 74, 18, 24, 40
    hi = max([v or 0 for v in vals] + [1])
    step = 10 ** (len(str(int(hi))) - 1)
    top = (int(hi / step) + 1) * step
    n = len(years)
    bw = (W - L - R) / n * 0.62

    def x(i):
        return L + (W - L - R) * (i + 0.5) / n

    def y(v):
        return T + (H - T - B) * (1 - v / top)

    g = []
    for k in range(5):
        t = top * k / 4
        g.append(f'<line x1="{L}" y1="{y(t):.1f}" x2="{W-R}" y2="{y(t):.1f}" '
                 f'stroke="var(--rule-soft)" stroke-width="1"/>')
        g.append(f'<text x="{L-8}" y="{y(t)+4:.1f}" text-anchor="end" '
                 f'font-family="IBM Plex Mono, monospace" font-size="11" '
                 f'fill="var(--ink3)">{t:,.0f}</text>')
    for i, yr in enumerate(years):
        v = vals[i] or 0
        g.append(f'<rect x="{x(i)-bw/2:.1f}" y="{y(v):.1f}" width="{bw:.1f}" '
                 f'height="{max(H-B-y(v), 0):.1f}" fill="{color}" '
                 f'opacity="{1 if i == n-1 else .62}"/>')
        g.append(f'<text x="{x(i):.1f}" y="{H-22}" text-anchor="middle" '
                 f'font-family="IBM Plex Mono, monospace" font-size="11" '
                 f'fill="var(--ink3)">{yr.replace("年度", "")}</text>')
    g.append(f'<text x="{x(n-1):.1f}" y="{y(vals[-1] or 0)-7:.1f}" text-anchor="middle" '
             f'font-family="IBM Plex Mono, monospace" font-size="12" '
             f'fill="{color}">{vals[-1] or 0:,.0f}</text>')
    g.append(f'<text x="{L}" y="{H-6}" font-family="IBM Plex Mono, monospace" '
             f'font-size="11" fill="var(--ink3)">単位：億円　年度</text>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{label}の受注高の推移">'
            + "".join(g) + "</svg>")


def note_vs_nonres() -> str:
    """着工統計との違い。**消さないこと。**同じ用途名が両方に出る。"""
    return f'''  <div class="warn">
    <h4>このページの数字が指しているもの</h4>
    <ul>
      <li><strong>これは「改修をいくら受注したか」（億円）です。</strong>建物が何棟あるか、何棟建ったかではありません</li>
      <li>このサイトの<a href="{SITE_URL}nonres/">非住宅建築物のページ</a>は<strong>建築着工統計</strong>で、「その年度に何棟<strong>建った</strong>か」（棟）です。<strong>同じ用途名が両方に出ますが、出典も単位も別の統計です。足したり比べたりできません。</strong></li>
      <li>元請・下請を通した<strong>受注ベース</strong>の集計です。同じ工事が重複して数えられない造りですが、標本調査にもとづく推計値です</li>
      <li>これは<strong>見積でも、必要額の算定でも、助言でもありません。</strong>特定の工事・発注時期・事業者を推奨するものでもありません</li>
    </ul>
  </div>
'''


def build(basis: dict) -> int:
    rf = basis.get("reform")
    if not rf:
        print("  reform がありません。update_basis.py を先に走らせてください。")
        return 0

    years = rf["years"]
    day = basis["generated"].split()[0]
    y0, y1 = years[0], years[-1]
    i5 = max(len(years) - 6, 0)
    y5 = years[i5]
    area, use, client = rf["area"], rf["use"], rf["client"]
    url, sid = rf["url"], rf["statsDataId"]

    nat = area.get("全国", {})
    hi_now = _y(nat.get("非住宅建築物", []))
    ju_now = _y(nat.get("住宅", []))
    hi_5 = _y(nat.get("非住宅建築物", []), i5)
    metro = sum(_y(area.get(p, {}).get("非住宅建築物", [])) for p in METRO)
    metro_ju = sum(_y(area.get(p, {}).get("住宅", [])) for p in METRO)

    hi_use = use.get("非住宅建築物", {})
    rc_s = sum(_y(hi_use.get(k, [])) for k in STRUCT[1:3])
    hi_tot = _y(hi_use.get("計", []))
    rc_pct = rc_s / hi_tot * 100 if hi_tot else 0

    # 用途別ランキング（掲載する用途だけ）
    rows = []
    for key, slug, label in USES:
        d = use.get(key, {})
        v = _y(d.get("計", []))
        if v:
            rows.append((key, slug, label, v, _pct(v, _y(d.get("計", []), i5))))
    rows.sort(key=lambda r: -r[3])
    rank = {r[0]: i + 1 for i, r in enumerate(rows)}
    vmax = rows[0][3] if rows else 1

    out = HERE / "reform"
    out.mkdir(exist_ok=True)
    keep = {f"{s}.html" for _, s, _ in USES} | {"index.html"}
    for f in out.glob("*.html"):        # 刈り取り。残すとサイトマップが拾い続ける
        if f.name not in keep:
            f.unlink()

    def use_table(mark: str = "") -> str:
        tr = []
        for key, slug, label, v, ch in rows:
            cls = ' class="me"' if key == mark else ""
            nm = label if key == mark else f'<a href="{slug}.html">{label}</a>'
            tr.append(f'<tr{cls}><td class="n">{rank[key]}</td><td>{nm}</td>'
                      + bar_cell(f"{v:,.0f}", v, 0, vmax, "var(--ai)")
                      + f'<td class="n">{_sign(ch)}</td></tr>')
        return "".join(tr)

    src = f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて国土交通省「建築物リフォーム・リニューアル調査」の公表値です。</strong>
    e-Stat の API から取得し、<strong>合計と変化率を出すところまで</strong>を行っています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>
'''
    method = f'''  <section>
    <h2><span class="idx">Method</span>この数字の出し方</h2>
    <div class="tablebox"><table>
      <thead><tr><th>項目</th><th>内容</th></tr></thead>
      <tbody>
        <tr><td>出典</td><td class="n">国土交通省「建築物リフォーム・リニューアル調査」年度次</td></tr>
        <tr><td>表章項目</td><td class="n">受注高（対前年同期比ではない方）</td></tr>
        <tr><td>統計表</td><td class="n">施工地域別 {sid["area"]}／用途・構造別 {sid["use"]}／発注者・工事種類別 {sid["client"]}</td></tr>
        <tr><td>期間</td><td class="n">{y0} 〜 {y1}（{len(years)}年度）</td></tr>
        <tr><td>単位</td><td class="n">億円</td></tr>
        <tr><td>変化率</td><td class="n">（{y1} ÷ 対象年度 − 1）× 100</td></tr>
      </tbody>
    </table></div>
    <p class="colophon">取得日 {day}。機械可読な全数値は <a href="{SITE_URL}basis.json">basis.json</a> にあります。
    <a href="{url["use"]}" target="_blank" rel="noopener">e-Stat の原表</a>でも同じ数字が確認できます。</p>
  </section>
'''

    # ================= 一覧 =================
    canonical = f"{SITE_URL}reform/"
    title = f"改修市場の規模｜{y1} 非住宅 {hi_now:,.0f}億円・住宅 {ju_now:,.0f}億円"
    desc = (f"国土交通省「建築物リフォーム・リニューアル調査」の{y1}の受注高は、"
            f"非住宅建築物 {hi_now:,.0f}億円（{y5}比 {_sign(_pct(hi_now, hi_5))}）、"
            f"住宅 {ju_now:,.0f}億円。用途別・施工地域別・発注者別に並べています。")
    h = [head(title, desc, canonical, crumb="改修市場"), src]
    h.append(f'''
  <span class="toplabel">公表統計 ／ 改修市場</span>
  <h1>改修市場の規模
    <span class="sub">建物の改修を「いくら受注したか」を集めた統計です。{y1}の受注高は、非住宅建築物が <strong>{hi_now:,.0f}億円</strong>、住宅が <strong>{ju_now:,.0f}億円</strong>。{y0}からの{len(years)}年度分を、用途・施工地域・発注者で並べています。</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">非住宅建築物　{y1}</span>
      <div class="v">{hi_now:,.0f}<small>億円</small></div>
      <p>{y5}比 {_sign(_pct(hi_now, hi_5))}、{y0}比 {_sign(_pct(hi_now, _y(nat.get("非住宅建築物", []), 0)))}。</p>
    </div>
    <div class="kpi">
      <span class="k">住宅　{y1}</span>
      <div class="v">{ju_now:,.0f}<small>億円</small></div>
      <p>{y0}比 {_sign(_pct(ju_now, _y(nat.get("住宅", []), 0)))}。</p>
    </div>
    <div class="kpi">
      <span class="k">一都三県（非住宅）</span>
      <div class="v">{metro:,.0f}<small>億円</small></div>
      <p>全国の {metro/hi_now*100:.1f}%。住宅は {metro_ju:,.0f}億円。</p>
    </div>
    <div class="kpi">
      <span class="k">RC系＋鉄骨造の比率</span>
      <div class="v">{rc_pct:.0f}<small>%</small></div>
      <p>非住宅の受注高のうち、コンクリート系と鉄骨造が占める割合。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig. 1</span>非住宅建築物の受注高（年度別）</h2>
    <p class="lede">{y0}から{y1}まで。いちばん右が最新年度です。</p>
    <div class="chartbox">
      <div class="chart-head"><span class="srcchip">出典 国土交通省</span><span>建築物リフォーム・リニューアル調査　e-Stat API 取得・{day}</span></div>
      {year_bars(years, nat.get("非住宅建築物", []), "非住宅建築物", "var(--ai)")}
      <div class="chart-foot">出典：国土交通省「建築物リフォーム・リニューアル調査」／<a href="{url["area"]}" target="_blank" rel="noopener">e-Stat statsDataId={sid["area"]}</a>（全国・用途「非住宅建築物」）　取得日 {day}</div>
    </div>
  </section>

  <section>
    <h2><span class="idx">Fig. 2</span>住宅の受注高（年度別）</h2>
    <p class="lede">同じ統計の住宅側です。<strong>非住宅とは別の軸なので、上の図と同じ高さでは描いていません。</strong></p>
    <div class="chartbox">
      <div class="chart-head"><span class="srcchip">出典 国土交通省</span><span>建築物リフォーム・リニューアル調査　e-Stat API 取得・{day}</span></div>
      {year_bars(years, nat.get("住宅", []), "住宅", "var(--shu)")}
      <div class="chart-foot">出典：同上（全国・用途「住宅」）　取得日 {day}</div>
    </div>
  </section>

{note_vs_nonres()}
  <section>
    <h2><span class="idx">Use</span>用途別の受注高（{y1}）</h2>
    <p class="lede">多い順です。用途名をクリックすると、その用途の推移と構造別の内訳が出ます。掲載しているのは、この統計表の用途区分のうち {len(rows)} 区分です。</p>
    <div class="tablebox"><table>
      <thead><tr><th>順</th><th>用途</th><th>受注高（億円）</th><th>{y5}比</th></tr></thead>
      <tbody>{use_table()}</tbody>
    </table></div>
    <p class="colophon">出典：国土交通省「建築物リフォーム・リニューアル調査」／<a href="{url["use"]}" target="_blank" rel="noopener">e-Stat statsDataId={sid["use"]}</a>　表章項目「受注高」　取得日 {day}。</p>
  </section>
''')

    # 施工地域別
    ar = []
    pool = [(n, _y(d.get("非住宅建築物", [])), _y(d.get("住宅", [])))
            for n, d in area.items() if _y(d.get("非住宅建築物", []))]
    amax = max(v for _, v, _ in pool)
    groups: dict[str, list] = {"全国": [], "都道府県": [], "市・特別区部": [], "不明": []}
    for n, v, j in pool:
        groups[area_group(n)].append((n, v, j))
    for g in ("全国", "都道府県", "市・特別区部"):
        items = sorted(groups[g], key=lambda r: -r[1])
        if not items:
            continue
        ar.append(f'<tr><td colspan="3" class="grp">{g}</td></tr>')
        for n, v, j in items:
            cls = ' class="me"' if n in METRO or n == "全国" else ""
            ar.append(f'<tr{cls}><td>{n}</td>'
                      + bar_cell(f"{v:,.0f}", v, 0, amax, "var(--ai)")
                      + f'<td class="n">{j:,.0f}</td></tr>')
    h.append(f'''  <section>
    <h2><span class="idx">Area</span>施工地域別の受注高（{y1}）</h2>
    <p class="lede">非住宅建築物が多い順です。バーは非住宅。住宅の欄は同じ統計の住宅側で、参考として並べています。<strong>都道府県と政令市は重複します</strong>（政令市は都道府県の内数）ので、足し合わせないでください。</p>
    <div class="tablebox"><table>
      <thead><tr><th>施工地域</th><th>非住宅（億円）</th><th>住宅（億円）</th></tr></thead>
      <tbody>{"".join(ar)}</tbody>
    </table></div>
    <p class="colophon">出典：国土交通省「建築物リフォーム・リニューアル調査」／<a href="{url["area"]}" target="_blank" rel="noopener">e-Stat statsDataId={sid["area"]}</a>　取得日 {day}。一都三県の非住宅は {metro:,.0f}億円で、全国の {metro/hi_now*100:.1f}% です。</p>
  </section>
''')

    # 発注者別
    cl = []
    cpool = [(n, _y(d.get("計", []))) for n, d in client.items()
             if n != "計" and _y(d.get("計", []))]
    cpool.sort(key=lambda r: -r[1])
    cmax = cpool[0][1] if cpool else 1
    for n, v in cpool:
        kaiso = _y(client.get(n, {}).get("改装・改修", []))
        iji = _y(client.get(n, {}).get("維持・修理", []))
        cl.append(f'<tr><td>{n}</td>'
                  + bar_cell(f"{v:,.0f}", v, 0, cmax, "var(--shu)")
                  + f'<td class="n">{kaiso:,.0f}</td><td class="n">{iji:,.0f}</td></tr>')
    h.append(f'''  <section>
    <h2><span class="idx">Client</span>発注者別の受注高（{y1}）</h2>
    <p class="lede">誰が発注したかの区分です。右の2列は工事種類の内訳で、<strong>合計には増築・一部改築も含まれる</strong>ため、2列の和は左の計と一致しません。<strong>区分は入れ子（「住宅」の中に「住宅_管理組合」等が入る）</strong>なので、足し合わせないでください。</p>
    <div class="tablebox"><table>
      <thead><tr><th>発注者</th><th>計（億円）</th><th>改装・改修</th><th>維持・修理</th></tr></thead>
      <tbody>{"".join(cl)}</tbody>
    </table></div>
    <p class="colophon">出典：国土交通省「建築物リフォーム・リニューアル調査」／<a href="{url["client"]}" target="_blank" rel="noopener">e-Stat statsDataId={sid["client"]}</a>　取得日 {day}。</p>
  </section>

''')
    h.append(method)
    h.append(cta_building(consult_link()))
    h.append(f'''  <a class="cta" href="{SITE_URL}nonres/">
    <span class="k">着工のほうを見る</span>
    <span class="n">首都圏の非住宅建築物</span>
    <span class="d">同じ用途区分を「何棟建ったか」（着工・棟）で出しています。出典も単位も別の統計です</span>
    <span class="arrow">→</span>
  </a>
''')
    h.append(cite_block(canonical, day))
    h.append(foot())
    (out / "index.html").write_text("".join(h), encoding="utf-8")

    # ================= 用途ページ =================
    written = 1
    for key, slug, label in USES:
        d = use.get(key, {})
        vals = d.get("計", [])
        v = _y(vals)
        if not v:
            continue
        ch5 = _pct(v, _y(vals, i5))
        ch10 = _pct(v, _y(vals, 0))
        canonical = f"{SITE_URL}reform/{slug}.html"
        title = f"{label}の改修市場｜{y1} {v:,.0f}億円（{y5}比 {_sign(ch5)}）"
        desc = (f"{label}の改修工事の受注高は{y1}で {v:,.0f}億円。"
                f"{y5}比 {_sign(ch5)}、{y0}比 {_sign(ch10)}。"
                f"掲載{len(rows)}区分中 {rank[key]} 位。国土交通省の公表値。")
        g = [head(title, desc, canonical, crumb="改修市場"), src]
        st = []
        for k in STRUCT:
            sv = _y(d.get(k, []))
            st.append(f'<tr><td>{k}</td>'
                      + bar_cell(f"{sv:,.0f}", sv, 0, v, "var(--shu)")
                      + f'<td class="n">{sv/v*100:.1f}%</td></tr>')
        g.append(f'''
  <span class="toplabel">公表統計 ／ 改修市場</span>
  <h1>{label}の改修市場
    <span class="sub">{label}の改修工事の受注高は、{y1}で <strong>{v:,.0f}億円</strong>。{y5}から {_sign(ch5)}、{y0}から {_sign(ch10)} です。掲載している{len(rows)}区分のうち {rank[key]} 番目の規模になります。</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">{y1} の受注高</span>
      <div class="v">{v:,.0f}<small>億円</small></div>
      <p>建物の改修工事の受注額です。棟数ではありません。</p>
    </div>
    <div class="kpi">
      <span class="k">{y5}比</span>
      <div class="v">{_sign(ch5)}</div>
      <p>{y5} は {_y(vals, i5):,.0f}億円。</p>
    </div>
    <div class="kpi">
      <span class="k">{y0}比</span>
      <div class="v">{_sign(ch10)}</div>
      <p>{y0} は {_y(vals, 0):,.0f}億円。</p>
    </div>
    <div class="kpi">
      <span class="k">規模の順位</span>
      <div class="v">{rank[key]}<small>位 / {len(rows)}</small></div>
      <p>このサイトに載せている{len(rows)}区分のうち。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig.</span>{label}の受注高（年度別）</h2>
    <p class="lede">{y0}から{y1}まで。いちばん右が最新年度です。</p>
    <div class="chartbox">
      <div class="chart-head"><span class="srcchip">出典 国土交通省</span><span>建築物リフォーム・リニューアル調査　{label}　e-Stat API 取得・{day}</span></div>
      {year_bars(years, vals, label)}
      <div class="chart-foot">出典：国土交通省「建築物リフォーム・リニューアル調査」／<a href="{url["use"]}" target="_blank" rel="noopener">e-Stat statsDataId={sid["use"]}</a>（用途「{key}」・表章項目「受注高」）　取得日 {day}</div>
    </div>
  </section>

  <section>
    <h2><span class="idx">Struct</span>構造別の内訳（{y1}）</h2>
    <p class="lede">同じ統計の構造区分です。合計 {v:,.0f}億円 に対する内訳で、端数処理のため足しても一致しないことがあります。</p>
    <div class="tablebox"><table>
      <thead><tr><th>構造</th><th>受注高（億円）</th><th>構成比</th></tr></thead>
      <tbody>{"".join(st)}</tbody>
    </table></div>
    <p class="colophon">出典：同上（用途「{key}」×構造）　取得日 {day}。</p>
  </section>

{note_vs_nonres()}
  <section>
    <h2><span class="idx">Use</span>ほかの用途と比べる（{y1}）</h2>
    <p class="lede">受注高が多い順です。</p>
    <div class="tablebox"><table>
      <thead><tr><th>順</th><th>用途</th><th>受注高（億円）</th><th>{y5}比</th></tr></thead>
      <tbody>{use_table(mark=key)}</tbody>
    </table></div>
    <p class="colophon">出典：同上　取得日 {day}。</p>
  </section>

''')
        g.append(method)
        g.append(cta_building(consult_link(slug), "この用途でご相談の場合は"))
        g.append(f'''  <a class="cta" href="index.html">
    <span class="k">改修市場の全体へ</span>
    <span class="n">用途別・施工地域別・発注者別</span>
    <span class="d">非住宅 {hi_now:,.0f}億円・住宅 {ju_now:,.0f}億円（{y1}）の内訳</span>
    <span class="arrow">→</span>
  </a>
''')
        g.append(cite_block(canonical, day))
        g.append(foot())
        (out / f"{slug}.html").write_text("".join(g), encoding="utf-8")
        written += 1

    print(f"  非住宅 {hi_now:,.0f}億円／住宅 {ju_now:,.0f}億円（{y1}）　"
          f"一都三県の非住宅 {metro:,.0f}億円（{metro/hi_now*100:.1f}%）　"
          f"RC系＋鉄骨 {rc_pct:.0f}%")
    return written


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    n = build(basis)
    print(f"reform/ に {n} ページを生成しました")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""建物オーナー向けに、家賃と修繕費を並べたページを生成する。

    py build_rent.py      # build.py から呼ばれる（basis.json が要る）

出力: rent/index.html

--- なぜ作るのか ---------------------------------------------------------
賃貸マンション・ビルの所有者にとっての損益は「家賃 − 修繕費」。
この2つは同じ CPI の統計表に入っているのに、並べて出しているところが無い。

**結論は当社に都合が良くない。**修繕費だけが上がって家賃が上がっていない、
というのはオーナーの原資が痩せたという話で、素直に読めば工事を出しにくく
なっている。だからポジショントークにならない。ここが企画の安全弁なので、
「だから早く工事を」のような結びを足さないこと。

--- 地域を混ぜないこと ---------------------------------------------------
**建設工事費デフレーターに地域別は無い。**なので図に重ねるのは全国どうしだけ。
地域別のセクションは CPI どうし（家賃 と 設備修繕・維持）に閉じる。
v1.0 で「同じページの上と下で東京都が5.3倍ちがう」事故を起こしているので、
出典と範囲の違うものを同じ土俵に並べない。

--- 全国と地域別で品目が違う（重要） -------------------------------------
全国の図は品目「**民営家賃**」。地域別は中分類「**家賃**」。
理由は、品目レベルの民営家賃が **全国と東京都区部にしか無い**から
（メタには67地域あるが表が持っていない。2026-09-12 実測）。
中分類の家賃は公営・UR・公社を含む。**この違いを画面に書くこと。**

--- 基準が違う -----------------------------------------------------------
CPI は 2020年（暦年）＝100、建設工事費デフレーターは 2020年度＝100。
差は「基準からの離れかたの違い」であって水準の差ではない。
"""
from __future__ import annotations

import json
from pathlib import Path

from build_pref import (CSS, CTA_BUILDING, SITE_URL, cite_block, foot,  # noqa: F401
                        head)

HERE = Path(__file__).resolve().parent

# (basis 上のキー, 画面の名前, 線の色, 太さ, 破線か)
LINES = [
    ("deflator", "建設工事費デフレーター（建築補修）", "var(--shu)", 2.6, False),
    ("設備修繕・維持", "設備修繕・維持（消費者物価）", "var(--shu)", 1.6, True),
    ("民営家賃", "民営家賃（消費者物価）", "var(--ai)", 2.6, False),
    ("総合", "消費者物価（総合）", "var(--ink3)", 1.5, True),
]


def _pct(a: float, b: float) -> float:
    return (a / b - 1) * 100 if b else 0.0


def _sign(v: float) -> str:
    return f"{v:+.1f}%"


# 都市階級は**完全一致で判定する**。`"都市" in name` だと
# **京都市**が都市階級に落ちる（2026-09-12 に実際に起きた）。
CITY_CLASS = {"大都市", "中都市", "小都市Ａ", "小都市Ｂ・町村"}


def area_group(name: str) -> str:
    """地域を4つに束ねる。全国と市が同じ表に混ざると比較の意味が崩れる。"""
    if name == "全国":
        return "全国"
    if name in CITY_CLASS:
        return "都市階級"
    if name.endswith("地方"):
        return "地方"
    return "市"


def multi_chart(months: list[str], series: list[tuple[str, list[float], str, float, bool]]) -> str:
    """指数を複数本重ねる。凡例は図の中に置く（画像だけ出回っても読めるように）。"""
    W, H = 960, 400
    L, R, T, B = 58, 18, 74, 34
    allv = [v for _, vals, *_ in series for v in vals]
    lo = (int(min(allv) / 10) - 1) * 10
    hi = (int(max(allv) / 10) + 1) * 10
    n = len(months)

    def x(i: int) -> float:
        return L + (W - L - R) * i / (n - 1)

    def y(v: float) -> float:
        return T + (H - T - B) * (1 - (v - lo) / (hi - lo))

    g = []
    for t in range(lo, hi + 1, 10):
        g.append(f'<line x1="{L}" y1="{y(t):.1f}" x2="{W-R}" y2="{y(t):.1f}" '
                 f'stroke="var(--rule-soft)" stroke-width="1"/>')
        g.append(f'<text x="{L-8}" y="{y(t)+4:.1f}" text-anchor="end" '
                 f'font-family="IBM Plex Mono, monospace" font-size="11" '
                 f'fill="var(--ink3)">{t}</text>')
    g.append(f'<line x1="{L}" y1="{y(100):.1f}" x2="{W-R}" y2="{y(100):.1f}" '
             f'stroke="var(--ink3)" stroke-width="1" stroke-dasharray="2 3"/>')
    for i, m in enumerate(months):
        if m.endswith("年4月"):
            g.append(f'<text x="{x(i):.1f}" y="{H-12}" text-anchor="middle" '
                     f'font-family="IBM Plex Mono, monospace" font-size="11" '
                     f'fill="var(--ink3)">{m.split("年")[0]}</text>')

    for label, vals, color, w, dash in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
        da = ' stroke-dasharray="4 3"' if dash else ""
        g.append(f'<polyline points="{pts}" fill="none" stroke="{color}" '
                 f'stroke-width="{w}"{da}/>')
        g.append(f'<circle cx="{x(n-1):.1f}" cy="{y(vals[-1]):.1f}" r="3.5" fill="{color}"/>')

    # 凡例
    for k, (label, vals, color, w, dash) in enumerate(series):
        yy = 18 + k * 15
        g.append(f'<line x1="{L+4}" y1="{yy-4}" x2="{L+26}" y2="{yy-4}" stroke="{color}" '
                 f'stroke-width="{w}"' + (' stroke-dasharray="4 3"' if dash else "") + '/>')
        g.append(f'<text x="{L+32}" y="{yy}" font-family="IBM Plex Mono, monospace" '
                 f'font-size="11.5" fill="var(--ink2)">{label}　{vals[-1]:.1f}</text>')

    return (f'<svg viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="家賃と修繕費の推移">' + "".join(g) + "</svg>")


def build(basis: dict) -> int:
    rent = basis.get("rent")
    if not rent:
        print("  rent がありません。update_basis.py を先に走らせてください。")
        return 0

    d = basis["deflator"]
    months = d["months"]
    day = basis["generated"].split()[0]
    first, last = months[0], months[-1]
    nat = rent["national"]
    prim = d["series"][d["primary"]]

    pool = {"deflator": prim, **nat}
    series = [(label, pool[key], color, w, dash)
              for key, label, color, w, dash in LINES if key in pool]

    chg = {label: _pct(vals[-1], vals[0]) for label, vals, *_ in series}
    yachin = _pct(nat["民営家賃"][-1], nat["民営家賃"][0])
    shuzen = _pct(prim[-1], prim[0])
    setsubi = _pct(nat["設備修繕・維持"][-1], nat["設備修繕・維持"][0])
    sogo = _pct(nat["総合"][-1], nat["総合"][0])
    gap = shuzen - yachin

    canonical = f"{SITE_URL}rent/"
    title = f"家賃と修繕費の推移｜{first}〜{last} 家賃 {_sign(yachin)}／工事費 {_sign(shuzen)}"
    desc = (f"消費者物価指数の民営家賃は{first}から{last}までで {_sign(yachin)}、"
            f"建設工事費デフレーター（建築補修）は {_sign(shuzen)}。"
            f"同じ期間の消費者物価は {_sign(sogo)}。"
            "賃貸マンション・ビルの所有者向けに、政府統計の公表値を並べています。")

    # このページだけで使う CSS。**共有の CSS（build_pref.CSS）には足さないこと。**
    # 共有CSSは全ページに埋め込まれるので、1行足すだけで276ファイルが変わり、
    # 手動アップロードが毎回「全部入り」になる（2026-09-12 に実際にそうなった）。
    PAGE_CSS = ('<style>td.grp{background:var(--sunk);font-family:var(--mono);'
                'font-size:10.5px;letter-spacing:.11em;color:var(--ink3);'
                'text-transform:uppercase}</style>')
    h = [head(title, desc, canonical, crumb="家賃と修繕費"), PAGE_CSS]
    h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて総務省・国土交通省の公表値です。</strong>
    e-Stat の API から取得し、<strong>指数どうしを並べて変化率を割り算で出すところまで</strong>を行っています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表統計 ／ 建物オーナー向け</span>
  <h1>家賃と修繕費
    <span class="sub">{first}から{last}までの10年余りで、民営家賃は <strong>{_sign(yachin)}</strong>、建築補修の工事費は <strong>{_sign(shuzen)}</strong> でした。同じ期間の消費者物価は {_sign(sogo)} です。賃貸マンション・ビルの所有者にとっての収入と支出を、公表されている指数のまま並べています。</span>
  </h1>

  <div class="kpis">
    <div class="kpi">
      <span class="k">民営家賃　{first}比</span>
      <div class="v">{_sign(yachin)}</div>
      <p>消費者物価指数の品目。{last} は {nat["民営家賃"][-1]:.1f}（2020年＝100）。</p>
    </div>
    <div class="kpi hi">
      <span class="k">建築補修　{first}比</span>
      <div class="v">{_sign(shuzen)}</div>
      <p>建設工事費デフレーター。{last} は {prim[-1]:.1f}（2020年度＝100）。</p>
    </div>
    <div class="kpi">
      <span class="k">設備修繕・維持　{first}比</span>
      <div class="v">{_sign(setsubi)}</div>
      <p>消費者物価指数の品目。工事費とは別の統計です。</p>
    </div>
    <div class="kpi">
      <span class="k">差</span>
      <div class="v">{gap:.1f}<small>pt</small></div>
      <p>建築補修と民営家賃の、{first}比の差。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig. 1</span>家賃・修繕費・物価の推移（全国）</h2>
    <p class="lede">いずれも指数です。点線は 100 の高さ。<strong>朱の2本が工事・修繕の費用、藍が家賃、灰色の破線が消費者物価（総合）</strong>です。基準は消費者物価が2020年（暦年）＝100、建設工事費デフレーターが2020年度＝100で、期間の取り方が違います。</p>
    <div class="chartbox">
      <div class="chart-head"><span class="srcchip">出典 総務省・国土交通省</span><span>消費者物価指数／建設工事費デフレーター　e-Stat API 取得・{day}</span></div>
      {multi_chart(months, series)}
      <div class="chart-foot">
        出典：総務省「消費者物価指数（2020年基準）」／<a href="{rent["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={rent["statsDataId"]}</a>（全国・表章項目「指数」）、
        国土交通省「建設工事費デフレーター」{d["base"]}／<a href="{d["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={d["statsDataId"]}</a>（工事種別「建設総合_建築補修」）　取得日 {day}
      </div>
    </div>
  </section>

  <div class="warn">
    <h4>この図の読み方で、注意していただきたいこと</h4>
    <ul>
      <li>消費者物価指数の家賃は、<strong>いま入居している契約の家賃を含めて調べたもの</strong>です。新しく募集するときの賃料とは動き方が違います。<strong>「新築の募集賃料も横ばい」という意味ではありません。</strong></li>
      <li>基準期間が違います（消費者物価は<strong>2020年＝100</strong>、建設工事費デフレーターは<strong>2020年度＝100</strong>）。差は「基準からの離れかたの違い」であって、水準の差ではありません</li>
      <li>いずれも<strong>全国の平均</strong>です。個別の建物・地域の家賃や工事費とは関係がありません</li>
      <li>これは<strong>見積でも、必要額の算定でも、助言でもありません。</strong>特定の工事・発注時期・事業者を推奨するものでもありません</li>
    </ul>
  </div>

  <section>
    <h2><span class="idx">Table</span>各年4月の値</h2>
    <p class="lede">年に1行。いちばん下が最新月です。</p>
    <div class="tablebox"><table>
      <thead><tr><th>時点</th>{"".join(f"<th>{lb}</th>" for lb, *_ in series)}</tr></thead>
      <tbody>''')

    rows = []
    idxs = [i for i, m in enumerate(months) if m.endswith("年4月")] + [len(months) - 1]
    for k, i in enumerate(idxs):
        cls = ' class="me"' if k == len(idxs) - 1 else ""
        cells = "".join(f'<td class="n">{vals[i]:.1f}</td>' for _, vals, *_ in series)
        rows.append(f"<tr{cls}><td>{months[i]}</td>{cells}</tr>")
    h.append("".join(rows))
    h.append(f'''</tbody>
    </table></div>
    <p class="colophon">単位：指数。消費者物価指数は2020年＝100、建設工事費デフレーターは2020年度＝100。取得日 {day}。</p>
  </section>
''')

    # ---- 地域別（CPI どうしに閉じる） ----
    areas = rent.get("areas", {})
    if areas:
        rows = []
        groups = {"全国": [], "都市階級": [], "地方": [], "市": []}
        for nm, per in areas.items():
            y, s = per["家賃"], per["設備修繕・維持"]
            groups[area_group(nm)].append((nm, _pct(y[-1], y[0]), _pct(s[-1], s[0])))
        for gname in ("全国", "都市階級", "地方", "市"):
            items = sorted(groups[gname], key=lambda r: -r[1])
            if not items:
                continue
            rows.append(f'<tr><td colspan="4" class="grp">{gname}</td></tr>')
            for nm, ry, rs in items:
                cls = ' class="me"' if nm == "全国" else ""
                rows.append(f'<tr{cls}><td>{nm}</td><td class="n">{_sign(ry)}</td>'
                            f'<td class="n">{_sign(rs)}</td>'
                            f'<td class="n">{rs - ry:.1f}</td></tr>')
        n_over = sum(1 for _, per in areas.items()
                     if _pct(per["設備修繕・維持"][-1], per["設備修繕・維持"][0])
                     > _pct(per["家賃"][-1], per["家賃"][0]))
        h.append(f'''  <section>
    <h2><span class="idx">Area</span>地域別の家賃と設備修繕・維持</h2>
    <p class="lede">{first}から{last}までの変化率です。家賃の上昇が大きい順。<strong>ここで使っている「家賃」は中分類で、公営・都市再生機構・公社の家賃を含みます</strong>（上の図で使った品目「民営家賃」は、全国と東京都区部にしか公表がありません）。<strong>建設工事費デフレーターには地域別がないため、この表には入れていません。</strong>掲載した {len(areas)} 地域のうち、設備修繕・維持の上昇が家賃の上昇を上回ったのは {n_over} 地域です。</p>
    <div class="tablebox"><table>
      <thead><tr><th>地域</th><th>家賃（中分類）</th><th>設備修繕・維持</th><th>差（pt）</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table></div>
    <p class="colophon">出典：総務省「消費者物価指数（2020年基準）」（statsDataId={rent["statsDataId"]}）表章項目「指数」。取得日 {day}。いずれも消費者物価指数どうしの比較で、工事費とは別の統計です。この表の全国の値が上の図と少し違うのは、<strong>図が品目「民営家賃」、この表が中分類「家賃」</strong>で、別の系列だからです。</p>
  </section>
''')

    h.append(f'''  <section>
    <h2><span class="idx">Method</span>この数字の出し方</h2>
    <p class="lede">加工したのは変化率の計算だけです。式は次のとおりで、元の指数はすべて上の表に載せています。</p>
    <div class="tablebox"><table>
      <thead><tr><th>項目</th><th>内容</th></tr></thead>
      <tbody>
        <tr><td>変化率</td><td class="n">（{last}の指数 ÷ {first}の指数 − 1）× 100</td></tr>
        <tr><td>差（pt）</td><td class="n">2つの変化率の引き算</td></tr>
        <tr><td>期間</td><td class="n">{first} 〜 {last}（{len(months)}ヶ月）</td></tr>
        <tr><td>指数の基準</td><td class="n">消費者物価 2020年＝100／デフレーター 2020年度＝100</td></tr>
      </tbody>
    </table></div>
    <p class="colophon">指数の再基準化（別の年を100に置き直すこと）は行っていません。公表値のままです。機械可読な全数値は <a href="{SITE_URL}basis.json">basis.json</a> にあります。</p>
  </section>

  <a class="cta" href="{SITE_URL}deflator/">
    <span class="k">工事種別ごとに見る</span>
    <span class="n">建設工事費デフレーター</span>
    <span class="d">建築系31区分を、月次の推移と各年の値で出しています</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{SITE_URL}">
    <span class="k">全国の統計へ</span>
    <span class="n">大規模修繕統計ビューア</span>
    <span class="d">住宅ストック・着工・戸あたり工事金額・修繕積立金</span>
    <span class="arrow">→</span>
  </a>
''')
    h.append(cite_block(canonical, day))
    h.append(foot())

    out = HERE / "rent"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text("".join(h), encoding="utf-8")
    print(f"  民営家賃 {_sign(yachin)}／建築補修 {_sign(shuzen)}／差 {gap:.1f}pt　"
          f"地域別 {len(areas)} 地域")
    return 1


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    n = build(basis)
    print(f"rent/ に {n} ページを生成しました")


if __name__ == "__main__":
    main()

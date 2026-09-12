# -*- coding: utf-8 -*-
"""建物オーナー向けに、家賃と修繕費を並べたページを生成する。

    py build_rent.py      # build.py から呼ばれる（basis.json が要る）

出力: rent/index.html ／ rent/<地域スラッグ>.html（67地域）

--- なぜ作るのか ---------------------------------------------------------
賃貸マンション・ビルの所有者にとっての損益は「家賃 − 修繕費」。
この2つは同じ CPI の統計表に入っているのに、並べて出しているところが無い。

**結論は当社に都合が良くない。**修繕費だけが上がって家賃が上がっていない、
というのはオーナーの原資が痩せたという話で、素直に読めば工事を出しにくく
なっている。だからポジショントークにならない。ここが企画の安全弁なので、
「だから早く工事を」のような結びを足さないこと。

--- 地域を混ぜないこと ---------------------------------------------------
**建設工事費デフレーターに地域別は無い。**なので図に重ねるのは全国どうしだけ。
地域別のページは CPI どうし（家賃 と 設備修繕・維持）に閉じる。
v1.0 で「同じページの上と下で東京都が5.3倍ちがう」事故を起こしているので、
出典と範囲の違うものを同じ土俵に並べない。

--- 全国と地域別で品目が違う（重要） -------------------------------------
トップの図は品目「**民営家賃**」。地域別は中分類「**家賃**」。
理由は、品目レベルの民営家賃が **全国と東京都区部にしか無い**から
（メタには67地域あるが表が持っていない。2026-09-12 実測）。
中分類の家賃は公営・UR・公社を含む。**この違いを各ページに書くこと。**

--- CSS は共有のものに足さない（重要） -----------------------------------
`build_pref.CSS` は全ページにインライン展開される。**1行足すだけで276ファイルの
中身が変わり**、手動アップロードが毎回「全部入り」になる（2026-09-12 実測）。
このファイルで使う表現は PAGE_CSS に閉じ込めて、各ページの <style> で出す。
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

# 都市階級は**完全一致で判定する**。`"都市" in name` だと
# **京都市**が都市階級に落ちる（2026-09-12 に実際に起きた）。
CITY_CLASS = {"大都市", "中都市", "小都市Ａ", "小都市Ｂ・町村"}

# ファイル名。**手で決める。**自動ローマ字化は読みを外す（大津・甲府・堺 等）。
SLUG = {
    "全国": "zenkoku", "東京都区部": "tokyo-ku",
    "大都市": "daitoshi", "中都市": "chutoshi",
    "小都市Ａ": "shotoshi-a", "小都市Ｂ・町村": "shotoshi-b",
    "北海道地方": "hokkaido", "東北地方": "tohoku", "関東地方": "kanto",
    "北陸地方": "hokuriku", "東海地方": "tokai", "近畿地方": "kinki",
    "中国地方": "chugoku", "四国地方": "shikoku", "九州地方": "kyushu",
    "沖縄地方": "okinawa",
    "札幌市": "sapporo", "青森市": "aomori", "盛岡市": "morioka",
    "仙台市": "sendai", "秋田市": "akita", "山形市": "yamagata",
    "福島市": "fukushima", "水戸市": "mito", "宇都宮市": "utsunomiya",
    "前橋市": "maebashi", "さいたま市": "saitama", "千葉市": "chiba",
    "横浜市": "yokohama", "新潟市": "niigata", "富山市": "toyama",
    "金沢市": "kanazawa", "福井市": "fukui", "甲府市": "kofu",
    "長野市": "nagano", "岐阜市": "gifu", "静岡市": "shizuoka",
    "名古屋市": "nagoya", "津市": "tsu", "大津市": "otsu",
    "京都市": "kyoto", "大阪市": "osaka", "神戸市": "kobe",
    "奈良市": "nara", "和歌山市": "wakayama", "鳥取市": "tottori",
    "松江市": "matsue", "岡山市": "okayama", "広島市": "hiroshima",
    "山口市": "yamaguchi", "徳島市": "tokushima", "高松市": "takamatsu",
    "松山市": "matsuyama", "高知市": "kochi", "福岡市": "fukuoka",
    "佐賀市": "saga", "長崎市": "nagasaki", "熊本市": "kumamoto",
    "大分市": "oita", "宮崎市": "miyazaki", "鹿児島市": "kagoshima",
    "那覇市": "naha", "川崎市": "kawasaki", "相模原市": "sagamihara",
    "浜松市": "hamamatsu", "堺市": "sakai", "北九州市": "kitakyushu",
}
assert len(set(SLUG.values())) == len(SLUG), "スラッグが重複しています"

# このファイルが出すページだけで使う CSS。共有CSSには足さない（冒頭の注記参照）。
PAGE_CSS = """<style>
/* 数字だけの表では状況が伝わらないので、値の横に長さで見えるバーを置く。
   JS は使わない。幅はビルド時に計算してインラインで書き込む。 */
td.b{white-space:nowrap;font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right}
td.b .n{display:inline-block;min-width:4.8em;text-align:right}
td.b .t{display:inline-block;width:84px;height:10px;margin-left:10px;background:var(--sunk);
  border:1px solid var(--rule-soft);position:relative;vertical-align:middle}
td.b .t i{position:absolute;top:0;bottom:0;display:block}
td.b .t u{position:absolute;top:-2px;bottom:-2px;width:1px;background:var(--ink3);opacity:.6}
td.grp{background:var(--sunk);font-family:var(--mono);font-size:10.5px;
  letter-spacing:.11em;color:var(--ink3);text-transform:uppercase}
.lgd{display:flex;flex-wrap:wrap;gap:8px 22px;margin:16px 0 0;
  font-family:var(--mono);font-size:11.5px;color:var(--ink3)}
.lgd span{display:inline-flex;align-items:center;gap:8px}
.lgd em{width:24px;height:10px;display:inline-block;font-style:normal;border:1px solid var(--rule-soft)}
@media (max-width:640px){td.b .t{display:none}}
</style>"""


def _pct(a: float, b: float) -> float:
    return (a / b - 1) * 100 if b else 0.0


def _sign(v: float) -> str:
    return f"{v:+.1f}%"


def area_group(name: str) -> str:
    """地域を4つに束ねる。全国と市が同じ表に混ざると比較の意味が崩れる。"""
    if name == "全国":
        return "全国"
    if name in CITY_CLASS:
        return "都市階級"
    if name.endswith("地方"):
        return "地方"
    return "市"


def bar_cell(v: float, lo: float, hi: float, color: str, zero: bool = False) -> str:
    """数値と、その大きさを長さで示すバーを1つのセルに入れる。

    `zero=True` のときは 0 の位置に目盛りを置いて左右に伸ばす。家賃は下がった
    地域があるので、0起点にしないと「少し上がった」と「下がった」が
    同じ見た目になる。
    """
    span = (hi - lo) or 1.0
    if zero:
        z = (0 - lo) / span * 100
        if v >= 0:
            left, w = z, v / span * 100
        else:
            left, w = z + v / span * 100, -v / span * 100
        tick = f'<u style="left:{z:.1f}%"></u>'
    else:
        base = max(hi, 0.001)
        left, w = 0.0, max(v, 0) / base * 100
        tick = ""
    return (f'<td class="b"><span class="n">{_sign(v)}</span>'
            f'<span class="t"><i style="left:{left:.1f}%;width:{max(w, 0.8):.1f}%;'
            f'background:{color}"></i>{tick}</span></td>')


def multi_chart(months: list[str],
                series: list[tuple[str, list[float], str, float, bool]]) -> str:
    """指数を複数本重ねる。凡例は図の中に置く（画像だけ出回っても読めるように）。"""
    W, H = 960, 400
    L, R, T, B = 58, 18, 20 + 15 * len(series), 34
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

    for k, (label, vals, color, w, dash) in enumerate(series):
        yy = 18 + k * 15
        g.append(f'<line x1="{L+4}" y1="{yy-4}" x2="{L+26}" y2="{yy-4}" stroke="{color}" '
                 f'stroke-width="{w}"' + (' stroke-dasharray="4 3"' if dash else "") + "/>")
        g.append(f'<text x="{L+32}" y="{yy}" font-family="IBM Plex Mono, monospace" '
                 f'font-size="11.5" fill="var(--ink2)">{label}　{vals[-1]:.1f}</text>')

    return (f'<svg viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="家賃と修繕費の推移">' + "".join(g) + "</svg>")


def strip_plot(pairs: list[tuple[str, float, float]], mark: str = "") -> str:
    """地域を2本の帯に点で置く。**2つの範囲が重なっているか**を一目で見せる図。

    数字の表だけだと「家賃はほとんど動かず、修繕費だけ上がった」が伝わらない。
    """
    W, H = 960, 250
    L, R = 100, 24
    lo = min(min(y for _, y, _ in pairs), 0)
    hi = max(s for _, _, s in pairs)
    lo = (int(lo / 10) - 1) * 10
    hi = (int(hi / 10) + 1) * 10

    def x(v: float) -> float:
        return L + (W - L - R) * (v - lo) / (hi - lo)

    g = []
    for t in range(lo, hi + 1, 10):
        g.append(f'<line x1="{x(t):.1f}" y1="44" x2="{x(t):.1f}" y2="196" '
                 f'stroke="var(--rule-soft)" stroke-width="1"/>')
        g.append(f'<text x="{x(t):.1f}" y="216" text-anchor="middle" '
                 f'font-family="IBM Plex Mono, monospace" font-size="11" '
                 f'fill="var(--ink3)">{t:+d}%</text>')
    g.append(f'<line x1="{x(0):.1f}" y1="38" x2="{x(0):.1f}" y2="200" '
             f'stroke="var(--ink3)" stroke-width="1" stroke-dasharray="2 3"/>')

    for label, idx, color, yy in (("家賃", 1, "var(--ai)", 90),
                                  ("設備修繕・維持", 2, "var(--shu)", 155)):
        g.append(f'<text x="{L-12}" y="{yy+4}" text-anchor="end" '
                 f'font-family="IBM Plex Mono, monospace" font-size="12" '
                 f'fill="var(--ink2)">{label}</text>')
        g.append(f'<line x1="{L}" y1="{yy}" x2="{W-R}" y2="{yy}" '
                 f'stroke="var(--rule)" stroke-width="1"/>')
        for nm, ry, rs in pairs:
            v = ry if idx == 1 else rs
            on = nm == mark
            g.append(f'<circle cx="{x(v):.1f}" cy="{yy}" r="{5.5 if on else 3.6}" '
                     f'fill="{color}" opacity="{1 if on else .4}"'
                     + (' stroke="var(--ink)" stroke-width="1.4"' if on else "") + "/>")
    note = f"　濃い点＝{mark}" if mark else ""
    g.append(f'<text x="{L}" y="26" font-family="IBM Plex Mono, monospace" font-size="11.5" '
             f'fill="var(--ink3)">●1つ＝1地域　全{len(pairs)}地域{note}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="地域別の家賃と設備修繕・維持の分布">' + "".join(g) + "</svg>")


def rank_table(pairs: list[tuple[str, float, float]], mark: str = "") -> str:
    """地域の一覧。数値の横にバーを置き、4つの区分に束ねる。"""
    ys = [y for _, y, _ in pairs]
    ss = [s for _, _, s in pairs]
    ds = [s - y for _, y, s in pairs]
    ylo, yhi = min(ys), max(ys)
    shi, dhi = max(ss), max(ds)

    def one(nm: str, ry: float, rs: float) -> str:
        cls = ' class="me"' if nm == mark else ""
        label = nm if nm == mark else f'<a href="{SLUG[nm]}.html">{nm}</a>'
        return (f"<tr{cls}><td>{label}</td>"
                + bar_cell(ry, ylo, yhi, "var(--ai)", zero=True)
                + bar_cell(rs, 0, shi, "var(--shu)")
                + bar_cell(rs - ry, 0, dhi, "var(--ink3)") + "</tr>")

    groups: dict[str, list] = {"全国": [], "都市階級": [], "地方": [], "市": []}
    for nm, ry, rs in pairs:
        groups[area_group(nm)].append((nm, ry, rs))
    rows = []
    for gname in ("全国", "都市階級", "地方", "市"):
        items = sorted(groups[gname], key=lambda r: -r[1])
        if not items:
            continue
        rows.append(f'<tr><td colspan="4" class="grp">{gname}</td></tr>')
        rows += [one(*it) for it in items]
    return "".join(rows)


LEGEND = ('<p class="lgd">'
          '<span><em style="background:var(--ai)"></em>家賃（中分類）</span>'
          '<span><em style="background:var(--shu)"></em>設備修繕・維持</span>'
          '<span><em style="background:var(--ink3)"></em>差</span>'
          '<span>バーの長さ＝変化率の大きさ。家賃だけ 0 の位置に目盛りがあります</span>'
          "</p>")


def area_note(rent: dict, day: str) -> str:
    return (f'<p class="colophon">出典：総務省「消費者物価指数（2020年基準）」'
            f'（statsDataId={rent["statsDataId"]}）表章項目「指数」。取得日 {day}。'
            'ここでいう「家賃」は中分類で、公営・都市再生機構・公社の家賃を含みます。'
            "<strong>建設工事費デフレーターには地域別が無いため、"
            "この比較には入れていません。</strong></p>")


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
    areas = rent.get("areas", {})

    unknown = [a for a in areas if a not in SLUG]
    if unknown:
        print(f"  ⚠ スラッグ未定義の地域を飛ばしました: {unknown}")

    pairs = [(nm, _pct(p["家賃"][-1], p["家賃"][0]),
              _pct(p["設備修繕・維持"][-1], p["設備修繕・維持"][0]))
             for nm, p in areas.items() if nm in SLUG]
    pairs.sort(key=lambda r: -r[1])
    n_over = sum(1 for _, ry, rs in pairs if rs > ry)
    y_hi, y_lo = max(r[1] for r in pairs), min(r[1] for r in pairs)
    s_hi, s_lo = max(r[2] for r in pairs), min(r[2] for r in pairs)
    # **「範囲が重なっていない」を直書きしないこと。**2026-09-12 時点では
    # 家賃の上限 10.5% と設備修繕の下限 10.9% で、差は 0.4pt しかない。
    # 来月には逆転しうる。毎月の再生成で文章が嘘にならないよう、算出して出し分ける。
    sep = "2つの範囲は重なっていません" if y_hi < s_lo else "2つの範囲は一部重なっています"

    yachin = _pct(nat["民営家賃"][-1], nat["民営家賃"][0])
    shuzen = _pct(prim[-1], prim[0])
    setsubi = _pct(nat["設備修繕・維持"][-1], nat["設備修繕・維持"][0])
    sogo = _pct(nat["総合"][-1], nat["総合"][0])
    gap = shuzen - yachin

    out = HERE / "rent"
    out.mkdir(exist_ok=True)
    keep = {f"{SLUG[nm]}.html" for nm, *_ in pairs} | {"index.html"}
    for f in out.glob("*.html"):       # 刈り取り。残すとサイトマップが拾い続ける
        if f.name not in keep:
            f.unlink()

    idxs = [i for i, m in enumerate(months) if m.endswith("年4月")] + [len(months) - 1]

    # ================= 一覧 =================
    series = [(label, {"deflator": prim, **nat}[key], color, w, dash)
              for key, label, color, w, dash in LINES]
    canonical = f"{SITE_URL}rent/"
    title = f"家賃と修繕費の推移｜{first}〜{last} 家賃 {_sign(yachin)}／工事費 {_sign(shuzen)}"
    desc = (f"消費者物価指数の民営家賃は{first}から{last}までで {_sign(yachin)}、"
            f"建設工事費デフレーター（建築補修）は {_sign(shuzen)}。"
            f"同じ期間の消費者物価は {_sign(sogo)}。"
            f"賃貸マンション・ビルの所有者向けに、政府統計の公表値を{len(pairs)}地域ぶん並べています。")

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
      <li>いずれも<strong>平均</strong>です。個別の建物の家賃や工事費とは関係がありません</li>
      <li>これは<strong>見積でも、必要額の算定でも、助言でもありません。</strong>特定の工事・発注時期・事業者を推奨するものでもありません</li>
    </ul>
  </div>

  <section>
    <h2><span class="idx">Fig. 2</span>{len(pairs)}地域の分布（{first}比）</h2>
    <p class="lede">●1つが1地域です。上の帯が家賃、下の帯が設備修繕・維持。<strong>掲載した{len(pairs)}地域すべてで、設備修繕・維持の上昇が家賃の上昇を上回りました（{n_over}／{len(pairs)}地域）。</strong>家賃は {y_lo:.1f}% 〜 {y_hi:.1f}%、設備修繕・維持は {s_lo:.1f}% 〜 {s_hi:.1f}% の範囲にあり、{sep}。</p>
    <div class="chartbox">
      <div class="chart-head"><span class="srcchip">出典 総務省</span><span>消費者物価指数（2020年基準）　e-Stat API 取得・{day}</span></div>
      {strip_plot(pairs)}
      <div class="chart-foot">出典：総務省「消費者物価指数（2020年基準）」／<a href="{rent["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={rent["statsDataId"]}</a>　いずれも消費者物価指数どうしの比較です　取得日 {day}</div>
    </div>
  </section>

  <section>
    <h2><span class="idx">Table</span>各年4月の値（全国）</h2>
    <p class="lede">年に1行。いちばん下が最新月です。</p>
    <div class="tablebox"><table>
      <thead><tr><th>時点</th>{"".join(f"<th>{lb}</th>" for lb, *_ in series)}</tr></thead>
      <tbody>''')
    for k, i in enumerate(idxs):
        cls = ' class="me"' if k == len(idxs) - 1 else ""
        cells = "".join(f'<td class="n">{vals[i]:.1f}</td>' for _, vals, *_ in series)
        h.append(f"<tr{cls}><td>{months[i]}</td>{cells}</tr>")
    h.append(f'''</tbody>
    </table></div>
    <p class="colophon">単位：指数。消費者物価指数は2020年＝100、建設工事費デフレーターは2020年度＝100。取得日 {day}。</p>
  </section>

  <section>
    <h2><span class="idx">Area</span>地域別（{len(pairs)}地域）</h2>
    <p class="lede">{first}から{last}までの変化率です。家賃の上昇が大きい順。地域名をクリックすると、その地域の推移と各年の値が出ます。</p>
    {LEGEND}
    <div class="tablebox"><table>
      <thead><tr><th>地域</th><th>家賃（中分類）</th><th>設備修繕・維持</th><th>差（pt）</th></tr></thead>
      <tbody>{rank_table(pairs)}</tbody>
    </table></div>
    {area_note(rent, day)}
  </section>

  <section>
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

''')
    h.append(CTA_BUILDING)
    h.append(f'''  <a class="cta" href="{SITE_URL}deflator/">
    <span class="k">工事種別ごとに見る</span>
    <span class="n">建設工事費デフレーター</span>
    <span class="d">建築系31区分を、月次の推移と各年の値で出しています</span>
    <span class="arrow">→</span>
  </a>
''')
    h.append(cite_block(canonical, day))
    h.append(foot())
    (out / "index.html").write_text("".join(h), encoding="utf-8")

    # ================= 地域ページ =================
    rank = {nm: i + 1 for i, (nm, *_) in enumerate(pairs)}
    written = 1
    for nm, ry, rs in pairs:
        slug = SLUG[nm]
        y = areas[nm]["家賃"]
        s = areas[nm]["設備修繕・維持"]
        canonical = f"{SITE_URL}rent/{slug}.html"
        title = f"{nm}の家賃と修繕費｜{first}比 家賃 {_sign(ry)}／設備修繕・維持 {_sign(rs)}"
        desc = (f"{nm}の消費者物価指数は、{first}から{last}までで家賃 {_sign(ry)}、"
                f"設備修繕・維持 {_sign(rs)}。差は {rs - ry:.1f} ポイント。"
                f"掲載{len(pairs)}地域中、家賃の上昇は {rank[nm]} 位です。")
        g = [head(title, desc, canonical, crumb="家賃と修繕費"), PAGE_CSS]
        g.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて総務省「消費者物価指数」の公表値です。</strong>
    e-Stat の API から取得し、<strong>変化率を割り算で出すところまで</strong>を行っています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表統計 ／ 建物オーナー向け</span>
  <h1>{nm}の家賃と修繕費
    <span class="sub">{first}から{last}までで、{nm}の家賃は <strong>{_sign(ry)}</strong>、設備修繕・維持は <strong>{_sign(rs)}</strong> でした。差は {rs - ry:.1f} ポイントです。いずれも消費者物価指数で、2020年＝100。</span>
  </h1>

  <div class="kpis">
    <div class="kpi">
      <span class="k">家賃　{first}比</span>
      <div class="v">{_sign(ry)}</div>
      <p>{last} は {y[-1]:.1f}。中分類のため公営・UR・公社を含みます。</p>
    </div>
    <div class="kpi hi">
      <span class="k">設備修繕・維持　{first}比</span>
      <div class="v">{_sign(rs)}</div>
      <p>{last} は {s[-1]:.1f}。</p>
    </div>
    <div class="kpi">
      <span class="k">差</span>
      <div class="v">{rs - ry:.1f}<small>pt</small></div>
      <p>設備修繕・維持から家賃を引いたポイント数。</p>
    </div>
    <div class="kpi">
      <span class="k">家賃の上昇</span>
      <div class="v">{rank[nm]}<small>位 / {len(pairs)}</small></div>
      <p>掲載{len(pairs)}地域のうち。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig. 1</span>{nm}の推移（{first}〜{last}）</h2>
    <p class="lede">藍が家賃、朱が設備修繕・維持です。いずれも消費者物価指数（2020年＝100）。点線は 100 の高さ。</p>
    <div class="chartbox">
      <div class="chart-head"><span class="srcchip">出典 総務省</span><span>消費者物価指数（2020年基準）　{nm}　e-Stat API 取得・{day}</span></div>
      {multi_chart(months, [("家賃（中分類）", y, "var(--ai)", 2.6, False), ("設備修繕・維持", s, "var(--shu)", 2.6, False)])}
      <div class="chart-foot">出典：総務省「消費者物価指数（2020年基準）」／<a href="{rent["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={rent["statsDataId"]}</a>（{nm}・表章項目「指数」）　取得日 {day}</div>
    </div>
  </section>

  <section>
    <h2><span class="idx">Fig. 2</span>{len(pairs)}地域のなかでの位置</h2>
    <p class="lede">●1つが1地域、濃い点が{nm}です。上の帯が家賃、下の帯が設備修繕・維持。</p>
    <div class="chartbox">
      <div class="chart-head"><span class="srcchip">出典 総務省</span><span>消費者物価指数（2020年基準）　e-Stat API 取得・{day}</span></div>
      {strip_plot(pairs, mark=nm)}
      <div class="chart-foot">出典：総務省「消費者物価指数（2020年基準）」／<a href="{rent["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={rent["statsDataId"]}</a>　取得日 {day}</div>
    </div>
  </section>

  <section>
    <h2><span class="idx">Table</span>各年4月の値</h2>
    <p class="lede">年に1行。いちばん下が最新月です。</p>
    <div class="tablebox"><table>
      <thead><tr><th>時点</th><th>家賃（中分類）</th><th>設備修繕・維持</th><th>差</th></tr></thead>
      <tbody>''')
        for k, i in enumerate(idxs):
            cls = ' class="me"' if k == len(idxs) - 1 else ""
            g.append(f'<tr{cls}><td>{months[i]}</td><td class="n">{y[i]:.1f}</td>'
                     f'<td class="n">{s[i]:.1f}</td>'
                     f'<td class="n">{s[i] - y[i]:+.1f}</td></tr>')
        g.append(f'''</tbody>
    </table></div>
    <p class="colophon">単位：指数（2020年＝100）。取得日 {day}。</p>
  </section>

  <section>
    <h2><span class="idx">Area</span>ほかの地域と比べる</h2>
    <p class="lede">{first}からの家賃の上昇が大きい順です。</p>
    {LEGEND}
    <div class="tablebox"><table>
      <thead><tr><th>地域</th><th>家賃（中分類）</th><th>設備修繕・維持</th><th>差（pt）</th></tr></thead>
      <tbody>{rank_table(pairs, mark=nm)}</tbody>
    </table></div>
    {area_note(rent, day)}
  </section>

''')
        g.append(CTA_BUILDING)
        g.append(f'''  <a class="cta" href="index.html">
    <span class="k">全国の状況へ</span>
    <span class="n">家賃と修繕費</span>
    <span class="d">工事費デフレーターを重ねた全国の図と、{len(pairs)}地域の一覧</span>
    <span class="arrow">→</span>
  </a>
''')
        g.append(cite_block(canonical, day))
        g.append(foot())
        (out / f"{slug}.html").write_text("".join(g), encoding="utf-8")
        written += 1

    print(f"  民営家賃 {_sign(yachin)}／建築補修 {_sign(shuzen)}／差 {gap:.1f}pt")
    print(f"  地域別 {len(pairs)} 地域　家賃 {y_lo:.1f}〜{y_hi:.1f}% ／ "
          f"設備修繕・維持 {s_lo:.1f}〜{s_hi:.1f}%　"
          f"範囲の重なり {'なし' if y_hi < s_lo else 'あり'}　"
          f"修繕が家賃を上回った地域 {n_over}/{len(pairs)}")
    return written


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    n = build(basis)
    print(f"rent/ に {n} ページを生成しました")


if __name__ == "__main__":
    main()

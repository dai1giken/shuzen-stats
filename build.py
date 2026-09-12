# -*- coding: utf-8 -*-
"""basis.json + template.html から公開用HTMLを2つ生成する。

    py update_basis.py   # e-Stat API から basis.json を作る
    py build.py          # page.html と index.html を作る

出力:
    page.html   Artifact 公開用（doctype/head を持たない body 部のみ）
    index.html  Webサーバ設置用（単体で開ける完全なHTML）

template.html だけが編集対象。page.html / index.html は毎回上書きされる。
"""
from __future__ import annotations

import json
from pathlib import Path

from build_city import build as build_city
from build_column import build as build_column
from build_consultation import PUBLISH as CONSULT_PUBLISH
from build_consultation import build as build_consultation
from build_cycle import build as build_cycle
from build_deflator import SERIES as DEFLATOR_SERIES
from build_deflator import build as build_deflator
from build_kijun import build as build_kijun
from build_rent import SLUG as RENT_SLUG
from build_rent import build as build_rent
from build_reform import USES as REFORM_USES
from build_reform import build as build_reform
from build_nonres import build as build_nonres
from build_pref import (FLOW_COHORT, SITE_URL, SLUG, analytics_tags, build as build_pref,
                        flow_by_pref, stock_by_pref)
from cartogram import cartogram
from pref_city import MIN_UNITS, cohort_sum, published_leaves
from costfig import cost_range_chart, cost_tables, cpi_chart
from shuzen_cycle import CYCLES as _CY, SENYU as _SENYU

# 修繕周期の項目数。ナビの {{N_CYCLE}} に使う。**原典の件数なので直書きしない。**
CYCLE_ROWS = list(_CY) + [_SENYU]

HERE = Path(__file__).resolve().parent

# 公開先の実URL（og:image・canonical・サイトマップ・構造化データ）。
# **build_pref.py の SITE_URL が唯一の定義**。ここで二重に定義していたので
# import に変えた。片方だけ直すと、トップと個別ページでドメインが食い違い、
# canonical が別サイトを指したまま気づけない。

# ---- Fig.1 の描画領域 ----
C1 = dict(w=900, h=340, x0=80, x1=872, ytop=40, ybase=288, ymax=200_000_000)


def _fmt(n: int) -> str:
    return f"{n:,}"


def chart1(series: dict[str, int]) -> str:
    """年度別 着工床面積の棒グラフ。"""
    years = list(series)
    vals = [series[y] for y in years]
    n = len(years)
    x0, x1, ybase, ytop, ymax = C1["x0"], C1["x1"], C1["ybase"], C1["ytop"], C1["ymax"]
    span = ybase - ytop
    slot = (x1 - x0) / n
    bw = slot - 3.0
    peak_i = vals.index(max(vals))
    last_i = n - 1

    def y_of(v: float) -> float:
        return ybase - v / ymax * span

    s = [f'<svg viewBox="0 0 {C1["w"]} {C1["h"]}" role="img" '
         f'aria-label="建築物着工床面積の年度別推移。{years[0]}{vals[0]/1e8:.2f}億平方メートルから'
         f'{years[peak_i]}のピーク{vals[peak_i]/1e8:.2f}億平方メートルを経て、'
         f'{years[last_i]}は{vals[last_i]/1e8:.2f}億平方メートル。">']

    # グリッド
    s.append('<g stroke="var(--rule-soft)" stroke-width="1" fill="none">')
    for t in (50, 100, 150, 200):
        y = y_of(t * 1_000_000)
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
    s.append('</g>')
    s.append(f'<line x1="{x0}" y1="{ybase}" x2="{x1}" y2="{ybase}" stroke="var(--rule)" stroke-width="1"/>')

    # y 軸ラベル
    s.append('<g font-family="IBM Plex Mono, monospace" font-size="12" fill="var(--ink3)" text-anchor="end">')
    for t in (0, 50, 100, 150, 200):
        y = y_of(t * 1_000_000)
        s.append(f'<text x="{x0 - 12}" y="{y + 4:.1f}">{t}</text>')
    s.append('</g>')
    s.append(f'<text x="{x0}" y="22" font-family="IBM Plex Mono, monospace" font-size="11" '
             f'fill="var(--ink3)" letter-spacing="1">百万m²</text>')

    # 棒
    for i, (yr, v) in enumerate(zip(years, vals)):
        x = x0 + i * slot + 1.5
        y = y_of(v)
        h = ybase - y
        r = min(4.0, h / 2)
        fill = "var(--shu)" if i == last_i else "var(--ai)"
        d = (f'M {x:.1f} {ybase} L {x:.1f} {y + r:.1f} Q {x:.1f} {y:.1f} {x + r:.1f} {y:.1f} '
             f'L {x + bw - r:.1f} {y:.1f} Q {x + bw:.1f} {y:.1f} {x + bw:.1f} {y + r:.1f} '
             f'L {x + bw:.1f} {ybase} Z')
        s.append(f'<path class="bar" d="{d}" fill="{fill}"/>')

    # 直接ラベル（ピークと最新のみ）
    for i, anchor in ((peak_i, "middle"), (last_i, "end")):
        x = x0 + i * slot + 1.5 + bw / 2
        if anchor == "end":
            x = x0 + i * slot + 1.5 + bw
        y = y_of(vals[i]) - 10
        col = "var(--shu)" if i == last_i else "var(--ink)"
        s.append(f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
                 f'font-family="IBM Plex Mono, monospace" font-size="13" font-weight="500" '
                 f'fill="{col}">{vals[i]/1e8:.2f}億</text>')

    # x 軸ラベル（5年ごと＋最新）
    s.append('<g font-family="IBM Plex Mono, monospace" font-size="12" fill="var(--ink3)">')
    for i in list(range(0, n, 5)) + [last_i]:
        x = x0 + i * slot + 1.5 + bw / 2
        anchor = "start" if i == 0 else ("end" if i == last_i else "middle")
        if i == 0:
            x = x0
        if i == last_i:
            x = x1
        s.append(f'<text x="{x:.1f}" y="310" text-anchor="{anchor}">{years[i].replace("年度","")}</text>')
    s.append('</g>')
    s.append(f'<text x="{x0}" y="332" font-family="IBM Plex Mono, monospace" font-size="11" '
             f'fill="var(--ink3)">年度　　■ 最新年度（{years[last_i]}）　棒にカーソルを重ねると実数が出ます</text>')

    # ホバー用の当たり判定。棒は細いので、全高・スロット幅の透明な矩形を最後に重ねる
    s.append('<g class="hits">')
    for i, (yr, v) in enumerate(zip(years, vals)):
        s.append(f'<rect class="barhit" x="{x0 + i * slot:.1f}" y="{ytop}" width="{slot:.1f}" '
                 f'height="{ybase - ytop}" fill="transparent" data-y="{yr}" data-v="{_fmt(v)}"/>')
    s.append('</g>')
    s.append('</svg>')
    return "\n      ".join(s)


MONO = 'IBM Plex Mono, monospace'


def cycle_chart() -> str:
    """築年数の帯に大規模修繕の周期（12〜15年）を重ねたインフォグラフィック。"""
    x0, x1, span = 66, 862, 50          # 築0年〜築50年
    def X(age): return x0 + age / span * (x1 - x0)
    bar_t, bar_b = 84, 124
    windows = [(12, 15, "1回目"), (24, 30, "2回目"), (36, 45, "3回目")]

    s = ['<svg viewBox="0 0 900 244" role="img" aria-label="マンションの築年数と大規模修繕の周期。'
         '1回目は築12〜15年、2回目は築24〜30年、3回目は築36〜45年ごろ。築40年は3回目の周期の途中にあたる。">']

    # 建物の一生
    s.append(f'<rect x="{x0}" y="{bar_t}" width="{x1-x0}" height="{bar_b-bar_t}" rx="3" fill="var(--rule-soft)"/>')

    # 修繕の窓
    for lo, hi, name in windows:
        w = X(hi) - X(lo)
        cx = (X(lo) + X(hi)) / 2
        s.append(f'<rect x="{X(lo):.1f}" y="{bar_t}" width="{w:.1f}" height="{bar_b-bar_t}" rx="3" fill="var(--shu)"/>')
        s.append(f'<text x="{cx:.1f}" y="74" text-anchor="middle" font-family="{MONO}" font-size="12.5" '
                 f'fill="var(--ink)" font-weight="500">{name}</text>')
        s.append(f'<text x="{cx:.1f}" y="146" text-anchor="middle" font-family="{MONO}" font-size="11.5" '
                 f'fill="var(--ink3)">築{lo}〜{hi}年</text>')

    # 築40年の位置（帯に隠れないよう最後に重ねる）
    x40 = X(40)
    s.append(f'<line x1="{x40:.1f}" y1="40" x2="{x40:.1f}" y2="{bar_t}" stroke="var(--shu)" '
             f'stroke-width="1.5" stroke-dasharray="4 4"/>')
    s.append(f'<line x1="{x40:.1f}" y1="{bar_t}" x2="{x40:.1f}" y2="{bar_b}" stroke="var(--surface)" '
             f'stroke-width="2"/>')
    s.append(f'<line x1="{x40:.1f}" y1="{bar_b}" x2="{x40:.1f}" y2="182" stroke="var(--shu)" '
             f'stroke-width="1.5" stroke-dasharray="4 4"/>')
    s.append(f'<text x="{x40:.1f}" y="30" text-anchor="middle" font-family="{MONO}" font-size="12.5" '
             f'fill="var(--shu)" font-weight="500">築40年 ＝ 3回目の途中</text>')

    # 目盛
    s.append(f'<line x1="{x0}" y1="168" x2="{x1}" y2="168" stroke="var(--rule)"/>')
    s.append(f'<g font-family="{MONO}" font-size="11.5" fill="var(--ink3)" text-anchor="middle">')
    for age in range(0, 51, 10):
        s.append(f'<line x1="{X(age):.1f}" y1="168" x2="{X(age):.1f}" y2="174" stroke="var(--rule)"/>')
        s.append(f'<text x="{X(age):.1f}" y="190">築{age}年</text>')
    s.append('</g>')

    # 長期修繕計画は30年以上
    y = 212
    s.append(f'<path d="M {x0} {y+6} L {x0} {y} L {X(30):.1f} {y} L {X(30):.1f} {y+6}" fill="none" '
             f'stroke="var(--ai)" stroke-width="1.5"/>')
    s.append(f'<text x="{(x0+X(30))/2:.1f}" y="{y+22}" text-anchor="middle" font-family="{MONO}" '
             f'font-size="11.5" fill="var(--ai)">長期修繕計画は「30年以上かつ大規模修繕2回以上」を含む期間で作成</text>')
    s.append('</svg>')
    return "\n      ".join(s)


def waffle_chart(panels) -> str:
    """1ドット＝5万戸のワッフル。panels は (見出し, 種別, 戸数) の並び。"""
    UNIT, COLS, SP, R = 50000, 10, 24, 7.5
    PW = (COLS - 1) * SP + 2 * R                     # パネル幅 231
    gap = (900 - 3 * PW) / 4
    bottom = 300

    s = ['<svg viewBox="0 0 900 340" role="img" aria-label="築40年超の分譲マンション住戸数。'
         + "、".join(f"{t}は{v/10000:.1f}万戸" for t, _, v in panels) + '。">']

    for pi, (title, kind, val) in enumerate(panels):
        px = gap + pi * (PW + gap)
        n = round(val / UNIT)
        s.append(f'<text x="{px:.1f}" y="24" font-family="{MONO}" font-size="12" fill="var(--ink3)">{title}'
                 f'<tspan fill="var(--ai)">　{kind}</tspan></text>')
        s.append(f'<text x="{px:.1f}" y="60" font-family="{MONO}" font-size="30" font-weight="600" '
                 f'letter-spacing="-1" fill="var(--ink)">{val/10000:.1f}'
                 f'<tspan font-size="14" font-weight="500" fill="var(--ink2)">万戸</tspan></text>')
        for k in range(100):
            cx = px + R + (k % COLS) * SP
            cy = bottom - (k // COLS) * SP
            on = k < n
            s.append(f'<circle cx="{cx:.1f}" cy="{cy}" r="{R}" '
                     f'fill="{"var(--shu)" if on else "var(--rule-soft)"}"/>')

    s.append(f'<text x="{gap:.1f}" y="332" font-family="{MONO}" font-size="11" fill="var(--ink3)">'
             f'● ひとつ＝5万戸　　塗りつぶし＝築40年超の住戸</text>')
    s.append('</svg>')
    return "\n      ".join(s)


def _iso_month(label: str) -> str:
    """'2026年6月' → '2026-06'。schema.org の temporalCoverage は ISO 8601 を要求する。"""
    y, m = label.replace("年", " ").replace("月", "").split()
    return f"{int(y):04d}-{int(m):02d}"


def _yr(label: str) -> int:
    """'1988年度' → 1988。by_year のキーから年度の数字だけを取り出す。"""
    return int("".join(c for c in label if c.isdigit()))


HEAD = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>大規模修繕統計ビューア</title>
<meta name="description" content="大規模修繕にかかわる政府統計を、読める形に並べたページ。工事費指数・修繕周期・積立金と、都道府県別の修繕適齢期の住戸数。算式と基準値をすべて公開しています。株式会社第一技研。">
<meta property="og:title" content="大規模修繕統計ビューア｜株式会社第一技研">
<meta property="og:description" content="いま日本でどれだけの建物が修繕の齢を迎えているか。政府統計の公表値だけで並べています。">
<meta property="og:type" content="website">
<meta property="og:url" content="__SITE__">
<meta property="og:image" content="__SITE__ogp.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="__SITE__">__ANALYTICS__
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600;700&display=swap">
<style>html{color-scheme:light dark}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
"""


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    tmpl = (HERE / "template.html").read_text(encoding="utf-8")

    total = basis["series"]["計"]
    latest = basis["latest_year"]
    a = total[latest]
    peak_year = max(total, key=total.get)
    peak = total[peak_year]

    rc = basis["series"]["鉄筋コンクリート造"][latest]
    src = basis["series"]["鉄骨鉄筋コンクリート造"][latest]
    wood = basis["series"]["木造"][latest]
    steel = basis["series"]["鉄骨造"][latest]
    residual = a - (wood + rc + src + steel)

    m = basis["mansion"]
    d = basis["deflator"]
    pref = basis["prefecture"]
    # 基準年は basis を作った年（JST）。2026 を直書きしないこと。
    ref = int(basis["generated"][:4])
    swin = basis["city"]["stock_window"]
    tokyo3 = ("東京都", "神奈川県", "埼玉県", "千葉県")
    # 着工（フロー）は basis.json の units ではなく by_year から数え直す。
    # 年度範囲を変えるのに e-Stat から取り直さなくて済む。
    flo, fhi = FLOW_COHORT
    flow = flow_by_pref(basis, flo, fhi)
    flow_national = sum(flow.values())
    metro = sum(flow[k] for k in tokyo3)

    # ---- 現存ストック（住宅・土地統計）。Fig.5 と都道府県ページの見出し数字はこちら ----
    city = basis["city"]
    stock, _codes, nat_stock, sum47 = stock_by_pref(basis)
    stock_metro = sum(stock[k] for k in tokyo3)
    stock_rank = sorted(stock.items(), key=lambda kv: -kv[1])
    # 「次いで○○、○○の順です」は順位が変われば変わる。散文に直書きしない
    stock_next = "、".join(nm for nm, _ in stock_rank[1:5])
    flow_rank = sorted(flow.items(), key=lambda kv: -kv[1])
    flow_next = "、".join(nm for nm, _ in flow_rank[1:5])

    dmonths, dser = d["months"], d["series"]
    prim = dser[d["primary"]]
    sv = basis["survey"]
    rsv = basis["reserve"]
    cpi = basis["cpi"]
    factor = prim[-1] / 100.0                     # 2020年度＝100 に対する現在の倍率
    third = next(r for r in sv["per_unit"] if r["label"] == "3回目以上")
    reserve12 = rsv["monthly_per_unit_yen"] * 12 * 12 / 10000   # 12年分（万円／戸）
    runtime = {
        "clock": {
            "annual_floor_area_m2": a,
            "b_2024": m["b_2024_units"],
            "c_2034": m["c_2034_units"],
            "dome_m2": basis["dome_m2"],
        },
        # **all（全75区分）はページに埋めない。**Explorer が使うのは series の
        # 16区分だけで、all を入れると index.html が 59KB 太る（実測）。
        # 全区分は deflator/ のページと basis.json から読める。
        "deflator": {k: v for k, v in d.items() if k != "all"},
        "calc": {
            "factor": factor,
            "latest_month": dmonths[-1],
            "median_now": {r["label"]: round(r["median"] * factor, 1) for r in sv["per_unit"]},
            "q1_now": {r["label"]: round(r["q1"] * factor, 1) for r in sv["per_unit"]},
            "q3_now": {r["label"]: round(r["q3"] * factor, 1) for r in sv["per_unit"]},
            # 回答件数。「統計から計算しただけの数値」だと画面で言うのに使う
            "n": {r["label"]: r["n"] for r in sv["per_unit"]},
            "reserve_yen": rsv["monthly_per_unit_yen"],
        },
        # 年代を切り替えてカートグラムを塗り直すための、都道府県×年度の実数。
        # 47×36＝1,692個。ページに載せても数十KBで済む。
        "flow": {
            "years": [_yr(k) for k in sorted(pref["by_year"]["東京都"], key=_yr)],
            "by_pref": {nm: [v for _, v in sorted(ser.items(), key=lambda kv: _yr(kv[0]))]
                        for nm, ser in pref["by_year"].items() if nm != "全国"},
            "metro": list(tokyo3),
            "default": [flo, fhi],
        },
    }

    # Explorer のリード文に置く数字。系列は表示中の16区分だけを対象にする
    # （画面に出ていない区分まで含めると、読者が表で確かめられない数字になる）。
    # トップの目次に出す件数。**直書きしないこと。**閾値や区分を変えたときに
    # 数字だけが古くなり、リンク先と食い違っても誰も気づけない。
    # index.html は各ビルダーより先に書き出されるので、戻り値は使えない。
    # 同じ元（basis と各ビルダーの定義）から数え直す。
    _areas = basis["city"]["areas"]
    _coh = basis["city"]["cohort"]
    # **build_city.py の publish と同じ作り方をすること。**leaves だけだと
    # 集計行（特別区部・政令市）が抜けて 173 になり、実際に生成される 179 と
    # 食い違う（2026-09-12 に実際にずれた）。
    _pub = {c for pre in {c[:2] for c in _areas}
            for c, _ in published_leaves(_areas, _coh, pre)}
    _pub |= {c for c, a in _areas.items()
             if not a["is_leaf"] and not c.endswith("000")
             and cohort_sum(a, _coh) >= MIN_UNITS}
    _n_city = len(_pub)
    _n_rent = len([a for a in basis.get("rent", {}).get("areas", {}) if a in RENT_SLUG])

    _chg = {k: (v[-1] / v[0] - 1) * 100 for k, v in d["series"].items()}
    # **端点を丸めてから引き算する。**丸める前の差を出すと、画面の
    # 「35.1% 〜 38.3%」を読者が引き算した 3.2 と、表示した幅 3.3 が食い違う。
    _exp = (round(min(_chg.values()), 1), round(max(_chg.values()), 1),
            sorted(_chg, key=lambda k: -_chg[k]).index(d["primary"]) + 1,
            (cpi["values"][-1] / cpi["values"][0] - 1) * 100)

    tokens = {
        "{{DATA}}": json.dumps(runtime, ensure_ascii=False, separators=(",", ":")),
        "{{DEF_MONTH}}": dmonths[-1],
        # 構造化データ用。temporalCoverage は ISO 8601 でないと解釈されない
        "{{DEF_MONTH_ISO}}": _iso_month(dmonths[-1]),
        "{{DEF_FIRST_ISO}}": _iso_month(dmonths[0]),
        "{{DEF_FIRST}}": dmonths[0],
        "{{DEF_VALUE}}": f"{prim[-1]:.1f}",
        "{{DEF_BASE}}": d["base"],
        "{{DEF_BASE_PCT}}": f"{prim[-1] - 100:.1f}",
        "{{DEF_SID}}": d["statsDataId"],
        # Explorer のリード文。**数字を直書きしないこと。**
        # 対象範囲を変えると上昇幅のレンジも順位も動くので、すべてここで算出する。
        # （実測: 主要16区分で幅3.2pt、建築系31区分で4.6pt、全75区分で15.1pt）
        "{{EXP_N}}": str(len(d["series"])),
        "{{EXP_LO}}": f"{_exp[0]:.1f}",
        "{{EXP_HI}}": f"{_exp[1]:.1f}",
        "{{EXP_PT}}": f"{_exp[1]-_exp[0]:.1f}",
        "{{EXP_RANK}}": str(_exp[2]),
        "{{CPI_SINCE}}": f"{_exp[3]:+.1f}",
        "{{DEF_N_ALL}}": str(len(d.get("all", {}))),
        "{{DEF_N_ARCH}}": str(len(DEFLATOR_SERIES)),
        "{{N_PREF}}": "47",
        "{{N_CITY}}": str(_n_city),
        "{{N_NONRES}}": str(len(basis["nonres"]["uses"])),
        "{{N_RENT}}": str(_n_rent),
        "{{N_REFORM}}": str(len(REFORM_USES)),
        # 修繕周期は原典（ガイドライン）の項目数。**直書きしないこと。**
        "{{N_CYCLE}}": str(len([r for r in CYCLE_ROWS if r[5] is not None])),
        "{{DEF_URL}}": d["url"],
        "{{CHART1}}": chart1(total),
        "{{CHART_COST}}": cost_range_chart(sv["per_unit"], factor, dmonths[-1]),
        "{{TABLE_COST}}": cost_tables(sv["per_unit"], sv["dist"], sv["n"], factor, dmonths[-1]),
        "{{CHART_CPI}}": cpi_chart(dmonths, prim, cpi["values"],
                                   "改装・改修工事費", "消費者物価（総合）"),
        "{{CHART_CYCLE}}": cycle_chart(),
        # ストックのタイルだけをリンクにする。都道府県ページの見出し数字がストックなので、
        # フローのタイルから送ると定義の壁を越えたまま着地することになる
        "{{CHART_STOCK}}": cartogram(stock, highlight=tokyo3,
                                     links={k: f"pref/{v}.html" for k, v in SLUG.items()},
                                     label="築26〜45年の非木造共同住宅の戸数", scale="万戸"),
        "{{CHART_MAP}}": cartogram(flow, highlight=tokyo3,
                                   label="分譲マンション着工戸数", scale="千戸"),
        "{{STOCK_SURVEY}}": city["survey"],
        "{{STOCK_SID}}": city["statsDataId"],
        "{{STOCK_URL}}": city["url"],
        "{{STOCK_FILTER}}": city["filter"],
        "{{STOCK_TOTAL}}": _fmt(nat_stock),
        "{{STOCK_SUM47}}": _fmt(sum47),
        "{{STOCK_DIFF}}": _fmt(nat_stock - sum47),
        "{{STOCK_METRO}}": _fmt(stock_metro),
        "{{STOCK_METRO_PCT}}": f"{stock_metro / nat_stock * 100:.1f}",
        "{{STOCK_TOP1}}": stock_rank[0][0],
        "{{STOCK_TOP1_UNITS}}": _fmt(stock_rank[0][1]),
        "{{STOCK_NEXT}}": stock_next,
        "{{TOP_NEXT}}": flow_next,
        "{{PREF_FROM}}": str(flo),
        "{{PREF_TO}}": str(fhi),
        "{{PREF_AGE_FROM}}": str(ref - fhi),
        "{{PREF_AGE_TO}}": str(ref - flo),
        # 基準年。ページに直書きすると年が明けた瞬間に全ページが古くなる
        "{{SITE_URL}}": SITE_URL,
        "{{REF_YEAR}}": str(ref),
        "{{STOCK_FROM}}": str(swin[0]),
        "{{STOCK_TO}}": str(swin[1]),
        "{{STOCK_AGE_FROM}}": str(ref - swin[1]),
        "{{STOCK_AGE_TO}}": str(ref - swin[0]),
        "{{PREF_TOTAL}}": _fmt(flow_national),
        "{{PREF_SID}}": pref["statsDataId"],
        "{{PREF_URL}}": pref["url"],
        "{{METRO_UNITS}}": _fmt(metro),
        "{{METRO_PCT}}": f"{metro / flow_national * 100:.1f}",
        "{{TOP1}}": flow_rank[0][0],
        "{{TOP1_UNITS}}": _fmt(flow_rank[0][1]),
        "{{FACTOR}}": f"{factor:.3f}",
        "{{SV_N}}": str(sv["n"]),
        "{{SV_NAME}}": sv["name"],
        "{{SV_URL}}": sv["url"],
        "{{SV_PUB}}": sv["published"],
        "{{SV_NOTE}}": sv["note"],
        "{{SV_ANCHOR}}": sv["anchor_note"],
        "{{MED3}}": f"{third['median']:.0f}",
        "{{MED3_NOW}}": f"{third['median']*factor:.0f}",
        "{{Q1_3_NOW}}": f"{third['q1']*factor:.0f}",
        "{{Q3_3_NOW}}": f"{third['q3']*factor:.0f}",
        "{{MED1_NOW}}": f"{sv['per_unit'][0]['median']*factor:.0f}",
        "{{RSV_YEN}}": _fmt(rsv["monthly_per_unit_yen"]),
        "{{RSV_NAME}}": rsv["name"],
        "{{RSV_URL}}": rsv["url"],
        "{{RSV_NOTE}}": rsv["note"],
        "{{RSV_12Y}}": f"{reserve12:.0f}",
        "{{CPI_NOW}}": f"{cpi['values'][-1]:.1f}",
        "{{CPI_PCT}}": f"{cpi['values'][-1]-100:.1f}",
        "{{CPI_GAP}}": f"{prim[-1]-cpi['values'][-1]:.1f}",
        "{{CPI_SID}}": cpi["statsDataId"],
        "{{CPI_URL}}": cpi["url"],
        "{{CHART_WAFFLE}}": waffle_chart([
            ("2024年末", "実績", m["b_2024_units"]),
            ("2034年末", "見通し", m["c_2034_units"]),
            ("2044年末", "見通し", m["d_2044_units"]),
        ]),
        "{{LATEST_YEAR}}": latest,
        "{{A_M2}}": _fmt(a),
        "{{PEAK_YEAR}}": peak_year,
        "{{PEAK_OKU}}": f"{peak/1e8:.2f}",
        "{{LATEST_OKU}}": f"{a/1e8:.2f}",
        "{{DECLINE_PCT}}": f"{(1 - a/peak)*100:.0f}",
        "{{RC_PCT}}": f"{(rc+src)/a*100:.1f}",
        "{{RC_M2}}": _fmt(rc + src),
        "{{RESIDUAL}}": _fmt(residual),
        "{{GENERATED}}": basis["generated"].split()[0],
    }

    out = tmpl
    for k, v in tokens.items():
        out = out.replace(k, v)

    left = [k for k in tokens if k in out]
    if left:
        raise SystemExit(f"未置換のトークンが残っています: {left}")
    if "{{" in out:
        raise SystemExit("template に未定義のトークンが残っています。")

    (HERE / "page.html").write_text(out, encoding="utf-8")
    page_head = HEAD.replace("__SITE__", SITE_URL).replace("__ANALYTICS__", analytics_tags())
    (HERE / "index.html").write_text(page_head + out + "\n</body>\n</html>\n", encoding="utf-8")
    check_jsonld()

    # build_city を先に走らせること。build_pref がサイトマップを作るとき
    # ディスク上の city/*.html を glob するので、逆順だと閾値で消したページが
    # サイトマップに残る（実際に37件残った）。
    n_city = build_city(basis)
    n_nonres = build_nonres(basis)
    n_defl = build_deflator(basis)
    n_kijun = build_kijun(basis)   # deflator/ の刈り取りより後に置くこと
    n_cycle = build_cycle(basis)
    n_consult = build_consultation(basis)
    n_rent = build_rent(basis)
    n_reform = build_reform(basis)
    n_col = build_column(basis)
    n_pref = build_pref(basis)
    print(f"pref/      {n_pref} 県 ＋ 一覧")
    print(f"city/      {n_city} 市区町村 ＋ 一覧")
    print(f"nonres/    {n_nonres} 用途 ＋ 一覧")
    print(f"deflator/  {n_defl} 工事種別 ＋ 一覧")
    print(f"deflator/  基準年のページ {n_kijun} 枚")
    print(f"cycle/     {n_cycle} ページ（修繕周期・ガイドライン転記）")
    print(f"consultation/ {n_consult} ページ（企業サイト用・案件相談）")
    print(f"rent/      {n_rent} ページ（家賃と修繕費）")
    print(f"reform/    {n_reform} ページ（改修市場）")
    print(f"column/    {n_col} 本 ＋ 一覧（企業サイト用）")
    print(f"page.html  {(HERE/'page.html').stat().st_size:,} bytes")
    print(f"index.html {(HERE/'index.html').stat().st_size:,} bytes")
    print(f"  A={_fmt(a)} m² ({latest})　ピーク {peak_year} {_fmt(peak)} m² → {tokens['{{DECLINE_PCT}}']}%減")
    print(f"  RC+SRC {tokens['{{RC_PCT}}']}%　構造別残差 {_fmt(residual)} m²")
    print(f"  戸あたり工事金額 3回目中央値 {third['median']}→{third['median']*factor:.0f} 万円/戸"
          f"（×{factor:.3f}）　積立金12年分 {reserve12:.0f} 万円/戸")
    print(f"  CPI {cpi['values'][-1]} vs デフレーター {prim[-1]}　差 {prim[-1]-cpi['values'][-1]:.1f} pt")
    print(f"  着工（フロー）{flo}〜{fhi}年度 {_fmt(flow_national)} 戸　"
          f"一都三県 {_fmt(metro)} 戸（{tokens['{{METRO_PCT}}']}%）")
    n_root = build_root_sitemap()
    print(f"_root/     sitemap.xml {n_root} URL ＋ robots.txt（htdocs 直下用）")
    write_llms_txt(basis, nat_stock, stock_metro)
    print("llms.txt   {:,} bytes".format((HERE / "llms.txt").stat().st_size))
    print(f"  現存ストック 全国行 {_fmt(nat_stock)} 戸　47都道府県合計 {_fmt(sum47)} 戸　"
          f"差 {_fmt(nat_stock - sum47)} 戸　一都三県 {_fmt(stock_metro)} 戸"
          f"（{tokens['{{STOCK_METRO_PCT}}']}%）")


def write_llms_txt(basis: dict, national: int, stock_metro: int) -> None:
    """llms.txt を書き出す。

    大規模言語モデルがこのサイトを読むときの案内。**新しい主張は何も足さない。**
    載っているのはページに出ている公表値と、その出典・ライセンス・引用の書式だけ。

    このサイトは AI に引用される条件をすでに満たしている。公表値しか載せず、
    算式を公開し、CC BY 4.0 で転載を許し、機械可読な basis.json まで置いてある。
    足りないのは「それを1枚で伝える入口」だけなので、それを用意する。

    数値は basis.json から引く。直書きすると、毎月の更新で古くなったことに
    誰も気づけない。
    """
    city = basis["city"]
    ref = int(basis["generated"][:4])
    lo, hi = city["stock_window"]
    day = basis["generated"].split()[0]
    defl = basis["deflator"]
    prim = defl["series"][defl["primary"]]

    body = f"""# 大規模修繕統計ビューア

> マンションの大規模修繕にかかわる日本の政府統計を、都道府県別・市区町村別に並べ直した公開データページです。数値はすべて公表値で、算式も公開しています。制作・提供は株式会社第一技研（外装の大規模修繕工事）。

## このサイトの性格

- 掲載しているのは**政府統計の公表値と、その単純な集計・按分だけ**です。当社が独自に調べたデータ、当社の分析・見解・将来予測は含みません。
- **CC BY 4.0** で公開しています。出典を明記すれば、図表・数値とも自由に転載・引用できます。
- 全ページの数値は {SITE_URL}basis.json に機械可読な形（JSON）で置いてあります。
- 取得日 {day}。更新は毎月です。

## 主な数値（{day} 時点）

- 現存する非木造の共同住宅のうち、{lo}〜{hi}年に建築されたもの（{ref}年時点で築{ref-hi}〜{ref-lo}年）は全国 {national:,} 戸。うち一都三県が {stock_metro:,} 戸。
- 建設工事費デフレーター（建築補修）は {prim[-1]}（{defl["base"]}、{defl["months"][-1]}）。
- 出典は総務省「令和5年住宅・土地統計調査」、国土交通省「建設工事費デフレーター」「建築着工統計」ほか。すべて e-Stat API から取得しています。

## ページの構成

- [トップ]({SITE_URL}) — 全国の指標、工事費指数、戸あたり工事金額、修繕積立金
- [都道府県別の一覧]({SITE_URL}pref/) — 47都道府県
- [市区町村別の一覧]({SITE_URL}city/) — 一都三県の市区
- [家賃と修繕費]({SITE_URL}rent/) — 賃貸マンション・ビルの所有者向け。家賃・修繕費・物価の推移
- [改修市場の規模]({SITE_URL}reform/) — 建物の改修をいくら受注したか。用途別・施工地域別・発注者別
- [工事種別の一覧]({SITE_URL}deflator/) — 建設工事費デフレーターの建築系31区分
- [指数の基準年]({SITE_URL}deflator/kijun-nendo.html) — 2011年度・2015年度・2020年度の各基準が同時に公表されています。基準をそろえる換算と、またいで割ったときのずれ
- [修繕周期の部位別一覧]({SITE_URL}cycle/) — 長期修繕計画作成ガイドライン（令和6年6月改定）様式第3-2号の記載例。周期は幅で示されています
- [非住宅建築物の一覧]({SITE_URL}nonres/) — 事務所・店舗・工場・倉庫・学校・病院
- [basis.json]({SITE_URL}basis.json) — 全ページの数値と系列（機械可読）
- [sitemap.xml]({SITE_URL}sitemap.xml) — 全ページの一覧

## 引用するときの書式

出典：大規模修繕統計ビューア（株式会社第一技研）{SITE_URL} {day}取得。原データは総務省・国土交通省の公表統計（e-Stat）。

## 読むときの注意

- 市区町村ページの見出しの戸数は**分譲と賃貸を合わせた数**です。所有の関係別の内訳は各ページに別途載せています（その統計表は市区までで、町村はありません）。
- 住宅・土地統計調査は**標本調査にもとづく推計値**で、全数調査ではありません。公表値は100戸単位に丸めてあるため、内訳の合計は総数と数十〜数百戸ずれることがあります。
- 修繕周期は工事の種類ごとに違い、令和6年6月改定のガイドラインでは**幅**で示されています（例：外壁塗装の塗替は12〜15年、除去・塗装は24〜30年）。単一の年数では示されていないので「12年周期」と要約しないでください。項目ごとの一覧は {SITE_URL}cycle/ にあります。
- 工事費の換算は指数の比だけで行っており、仕様・規模・立地・劣化状況・工期・足場の条件は反映していません。
"""
    (HERE / "llms.txt").write_text(body, encoding="utf-8")


def check_jsonld() -> None:
    """生成した index.html の JSON-LD を、書き出した直後にパースして確かめる。

    **構造化データは壊れても画面が何も変わらない。**気づけるのは Search Console
    からメールが来たときで、そこまで数日〜数週間かかる。2026-09-12 に
    spatialCoverage の型が `Country` になっていて指摘を受けた。schema.org 上は
    Country も Place の下位型だが、**Google の Dataset 検証はそれを受け付けない**
    ので、型名を Place に合わせる。

    ここで見るのは「JSON として読めるか」と「落とすと痛いキーがあるか」まで。
    語彙の正しさ全部はここでは分からないので、**変更したら Google の
    リッチリザルトテストにも通すこと。**
    """
    import re

    src = (HERE / "index.html").read_text(encoding="utf-8")
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S)
    if not blocks:
        raise SystemExit("index.html に JSON-LD がありません。template.html を確認してください。")

    for i, b in enumerate(blocks, 1):
        try:
            doc = json.loads(b)
        except json.JSONDecodeError as e:
            raise SystemExit(f"JSON-LD #{i} がパースできません: {e}")
        for x in ([doc] if isinstance(doc, dict) else doc):
            if x.get("@type") != "Dataset":
                continue
            sc = x.get("spatialCoverage")
            if not isinstance(sc, dict) or sc.get("@type") != "Place":
                raise SystemExit(
                    'Dataset の spatialCoverage は {"@type": "Place"} でなければ'
                    f"なりません（いまは {sc!r}）。"
                    "Google の Dataset 検証は Country を受け付けません。")
            missing = [k for k in ("name", "description", "license", "url", "creator")
                       if k not in x]
            if missing:
                raise SystemExit(f"Dataset に必要なキーがありません: {missing}")
    print(f"JSON-LD    {len(blocks)} ブロック　Dataset の spatialCoverage=Place を確認")


def build_root_sitemap() -> int:
    """ホスト直下（dai1giken.co.jp/）に置く robots.txt と sitemap.xml を作る。

    **クローラが読む robots.txt はホスト直下の1本だけ。**
    /shuzen-stats/robots.txt は置いてあるが読まれない（build_pref.py の
    同名生成部にも同じ注意書きがある）。だからここで作る。

    サイトマップも同じ理由でサイト全体を1本にまとめる。統計側の
    /shuzen-stats/sitemap.xml は URL-prefix プロパティ用にそのまま残し、
    こちらは企業サイトのトップと /column/ を含めた全体版にする。

    出力先は _root/。企業サイト用のZIPに入れて htdocs/ 直下へ置く。
    **shuzen-stats/ の中ではない。**間違えると404になる。
    """
    root = "https://dai1giken.co.jp/"
    out = HERE / "_root"
    out.mkdir(exist_ok=True)
    day = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))["generated"].split()[0]

    urls = [(root, "1.0")]
    # 技術コラム（企業サイト側。build_column.py が生成する）
    col = HERE / "column"
    if col.is_dir():
        urls.append((root + "column/", "0.8"))
        urls += [(f"{root}column/{f.name}", "0.7")
                 for f in sorted(col.glob("*.html")) if f.name != "index.html"]
    # 案件相談ページ（企業サイト側）。**公開前は載せない。**
    # build_consultation.PUBLISH を True にしたときだけサイトマップに入る。
    if CONSULT_PUBLISH and (HERE / "consultation").is_dir():
        urls.append((root + "consultation/", "0.9"))
    # 統計サイト。既存の sitemap.xml から URL をそのまま拾う。
    # ここで作り直すと、閾値で落としたページを二重管理することになる
    sm = HERE / "sitemap.xml"
    if sm.is_file():
        import re
        for loc in re.findall(r"<loc>([^<]+)</loc>", sm.read_text(encoding="utf-8")):
            urls.append((loc, "0.6"))

    body = ['<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    body += [f"<url><loc>{u}</loc><lastmod>{day}</lastmod><priority>{p}</priority></url>"
             for u, p in urls]
    body.append("</urlset>")
    (out / "sitemap.xml").write_text(chr(10).join(body), encoding="utf-8")

    (out / "robots.txt").write_text(f"""User-agent: *
Allow: /

Sitemap: {root}sitemap.xml
""", encoding="utf-8")
    return len(urls)


if __name__ == "__main__":
    main()

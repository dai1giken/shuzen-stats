# -*- coding: utf-8 -*-
"""戸あたり工事金額のレンジ図と、消費者物価との比較図。

どちらも値が確定しているのでサーバ側で描く（クライアントJSを増やさない）。
"""
from __future__ import annotations

MONO = "IBM Plex Mono, monospace"


def cost_range_chart(rows: list[dict], factor: float, latest_month: str) -> str:
    """回数別の戸あたり工事金額。調査時点と物価スライド後を上下2本で並べる。

    rows: [{label, n, q1, median, q3, mean}, ...]／factor: 換算倍率
    """
    XMAX = 220.0                     # 万円／戸
    x0, x1 = 132, 866
    top, gh, bh = 56, 78, 22

    def X(v: float) -> float:
        return x0 + v / XMAX * (x1 - x0)

    s = ['<svg viewBox="0 0 900 336" role="img" aria-label="回数別の戸あたり工事金額。'
         + "、".join(f'{r["label"]}の中央値は調査時点{r["median"]}万円、換算後{r["median"]*factor:.0f}万円'
                     for r in rows) + '。">']

    # 目盛
    s.append(f'<g stroke="var(--rule-soft)" stroke-width="1">')
    for t in range(0, 221, 50):
        s.append(f'<line x1="{X(t):.1f}" y1="46" x2="{X(t):.1f}" y2="{top + len(rows)*gh - 8}"/>')
    s.append('</g>')
    s.append(f'<g font-family="{MONO}" font-size="11.5" fill="var(--ink3)" text-anchor="middle">')
    for t in range(0, 221, 50):
        s.append(f'<text x="{X(t):.1f}" y="38">{t}</text>')
    s.append('</g>')
    s.append(f'<text x="{x1}" y="20" text-anchor="end" font-family="{MONO}" font-size="11.5" '
             f'fill="var(--ink3)">万円／戸</text>')

    for i, r in enumerate(rows):
        gy = top + i * gh
        s.append(f'<text x="{x0 - 14}" y="{gy + 20}" text-anchor="end" font-size="14" '
                 f'font-weight="600" fill="var(--ink)">{r["label"]}</text>')
        s.append(f'<text x="{x0 - 14}" y="{gy + 40}" text-anchor="end" font-family="{MONO}" '
                 f'font-size="11" fill="var(--ink3)">n={r["n"]}</text>')

        for j, (mul, col, name) in enumerate(((1.0, "var(--ai)", "調査時点"),
                                              (factor, "var(--shu)", latest_month))):
            by = gy + j * (bh + 6)
            q1, md, q3 = r["q1"] * mul, r["median"] * mul, r["q3"] * mul
            s.append(f'<rect x="{X(q1):.1f}" y="{by}" width="{X(q3)-X(q1):.1f}" height="{bh}" '
                     f'rx="2" fill="{col}" opacity="{0.30 if j == 0 else 0.55}"/>')
            s.append(f'<line x1="{X(md):.1f}" y1="{by}" x2="{X(md):.1f}" y2="{by + bh}" '
                     f'stroke="{col}" stroke-width="3"/>')
            s.append(f'<text x="{X(q3) + 9:.1f}" y="{by + bh - 6}" font-family="{MONO}" '
                     f'font-size="12.5" font-weight="500" fill="{col}">{md:.0f}</text>')
            s.append(f'<text x="{X(q1) - 9:.1f}" y="{by + bh - 6}" text-anchor="end" '
                     f'font-family="{MONO}" font-size="10.5" fill="var(--ink3)">{name}</text>')

    ly = top + len(rows) * gh + 12
    s.append(f'<g font-family="{MONO}" font-size="11.5">')
    s.append(f'<rect x="{x0}" y="{ly - 9}" width="26" height="11" rx="2" fill="var(--ai)" opacity=".30"/>')
    s.append(f'<text x="{x0 + 33}" y="{ly}" fill="var(--ink2)">調査時点（下位25%〜上位25%／縦線＝中央値）</text>')
    s.append(f'<rect x="{x0 + 330}" y="{ly - 9}" width="26" height="11" rx="2" fill="var(--shu)" opacity=".55"/>')
    s.append(f'<text x="{x0 + 363}" y="{ly}" fill="var(--ink2)">{latest_month}の物価に換算（×{factor:.3f}）</text>')
    s.append('</g>')
    s.append('</svg>')
    return "\n      ".join(s)


def cpi_chart(months: list[str], deflator: list[float], cpi: list[float],
              d_name: str, c_name: str) -> str:
    """改装・改修工事費と消費者物価の比較（2系列）。"""
    n = len(months)
    x0, x1, ytop, ybase = 62, 792, 34, 288

    vals = [v for v in deflator + cpi if v is not None]
    lo = int(min(vals) // 5 * 5)
    hi = int(-(-max(vals) // 5) * 5)

    def X(i: int) -> float:
        return x0 + i / (n - 1) * (x1 - x0)

    def Y(v: float) -> float:
        return ybase - (v - lo) / (hi - lo) * (ybase - ytop)

    s = [f'<svg viewBox="0 0 900 330" role="img" aria-label="改装・改修工事費と消費者物価の推移。'
         f'{months[-1]}時点で工事費は{deflator[-1]}、消費者物価は{cpi[-1]}。">']

    s.append('<g stroke="var(--rule-soft)" stroke-width="1">')
    g = lo
    while g <= hi:
        s.append(f'<line x1="{x0}" y1="{Y(g):.1f}" x2="{x1}" y2="{Y(g):.1f}"/>')
        g += 5
    s.append('</g>')
    s.append(f'<g font-family="{MONO}" font-size="11.5" fill="var(--ink3)" text-anchor="end">')
    g = lo
    while g <= hi:
        s.append(f'<text x="{x0 - 10}" y="{Y(g) + 4:.1f}">{g}</text>')
        g += 5
    s.append('</g>')
    if lo <= 100 <= hi:
        s.append(f'<line x1="{x0}" y1="{Y(100):.1f}" x2="{x1}" y2="{Y(100):.1f}" '
                 f'stroke="var(--ink3)" stroke-width="1" stroke-dasharray="4 4"/>')
    s.append(f'<line x1="{x0}" y1="{ybase}" x2="{x1}" y2="{ybase}" stroke="var(--rule)"/>')

    s.append(f'<g font-family="{MONO}" font-size="11.5" fill="var(--ink3)" text-anchor="middle">')
    for i, m in enumerate(months):
        if m.endswith("年1月") and int(m[:4]) % 2 == 1:
            s.append(f'<text x="{X(i):.1f}" y="{ybase + 20}">{m[:4]}</text>')
    s.append('</g>')

    for series, col, label in ((deflator, "var(--shu)", d_name), (cpi, "var(--c2)", c_name)):
        d = ""
        for i, v in enumerate(series):
            if v is None:
                continue
            d += ("L " if d else "M ") + f"{X(i):.1f} {Y(v):.1f} "
        s.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2.5" '
                 f'stroke-linejoin="round" stroke-linecap="round"/>')
        s.append(f'<circle cx="{X(n-1):.1f}" cy="{Y(series[-1]):.1f}" r="4" fill="{col}" '
                 f'stroke="var(--surface)" stroke-width="1.5"/>')
        s.append(f'<text x="{X(n-1) + 10:.1f}" y="{Y(series[-1]) + 4:.1f}" font-family="{MONO}" '
                 f'font-size="13" font-weight="600" fill="{col}">{series[-1]:.1f}</text>')
        s.append(f'<text x="{X(n-1) + 10:.1f}" y="{Y(series[-1]) + 20:.1f}" font-size="11.5" '
                 f'fill="var(--ink2)">{label}</text>')

    s.append(f'<text x="{x0}" y="20" font-family="{MONO}" font-size="11" fill="var(--ink3)" '
             f'letter-spacing="1">2020年（度）＝100</text>')
    s.append(f'<text x="{x0}" y="{ybase + 40}" font-family="{MONO}" font-size="11" fill="var(--ink3)">'
             f'工事費＝国土交通省 建設工事費デフレーター「建築補修」（2020年度基準）　'
             f'物価＝総務省 消費者物価指数 総合・全国（2020年基準）</text>')
    s.append('</svg>')
    return "\n      ".join(s)

def cost_tables(rows: list[dict], dist: list, n: int, factor: float, latest_month: str) -> str:
    """回数別の四分位表と、階級別の分布表。数字そのものを読ませる。"""
    def f1(v: float) -> str:
        return f"{v:,.1f}"

    def f0(v: float) -> str:
        return f"{v:,.0f}"

    h = ['<div class="tablebox">', '<table>',
         '<thead><tr><th>回数</th><th>件数</th><th>時点</th>'
         '<th>下位25%</th><th>中央値</th><th>上位25%</th><th>平均</th>'
         '<th>下位25%〜上位25%の幅</th></tr></thead>', '<tbody>']
    for r in rows:
        span = r["q3"] - r["q1"]
        h.append(
            f'<tr class="grp"><td rowspan="2"><strong>{r["label"]}</strong></td>'
            f'<td rowspan="2" class="num">{r["n"]}</td>'
            f'<td class="when">調査時点</td>'
            f'<td class="num">{f1(r["q1"])}</td><td class="num">{f1(r["median"])}</td>'
            f'<td class="num">{f1(r["q3"])}</td><td class="num">{f1(r["mean"])}</td>'
            f'<td class="num">{f1(span)}</td></tr>')
        h.append(
            f'<tr class="conv"><td class="when">{latest_month}換算</td>'
            f'<td class="num">{f0(r["q1"]*factor)}</td>'
            f'<td class="num"><strong>{f0(r["median"]*factor)}</strong></td>'
            f'<td class="num">{f0(r["q3"]*factor)}</td><td class="num">{f0(r["mean"]*factor)}</td>'
            f'<td class="num">{f0(span*factor)}</td></tr>')
    h.append('</tbody></table></div>')
    h.append('<p class="tnote">単位はすべて 万円／戸。'
             '平均が上位25%より大きい回があるのは、高額側に少数の外れ値があるためです。</p>')

    # ---- 階級別の分布 ----
    vals = [d[1] for d in dist if d[0] != "無回答"]
    mx = max(vals)
    edges = [25, 50, 75, 100, 125, 150, 175, 200]
    conv = []
    for i, (label, _) in enumerate(dist):
        if label == "無回答":
            conv.append("—")
        elif i == 0:
            conv.append(f"{edges[0]*factor:,.0f}万円以下")
        elif label.startswith("200万円超"):
            conv.append(f"{edges[-1]*factor:,.0f}万円超")
        else:
            conv.append(f"{edges[i-1]*factor:,.0f}〜{edges[i]*factor:,.0f}万円")

    h.append('<div class="tablebox" style="margin-top:14px">')
    h.append('<table><thead><tr><th>戸あたり工事金額（調査時点）</th>'
             f'<th>{latest_month}の物価なら</th><th>割合</th><th class="barcol">分布</th>'
             '</tr></thead><tbody>')
    for (label, pct), cv in zip(dist, conv):
        w = 0 if label == "無回答" else pct / mx * 100
        cls = ' class="na"' if label == "無回答" else ""
        h.append(f'<tr{cls}><td>{label}</td><td>{cv}</td>'
                 f'<td class="num">{pct:.1f}%</td>'
                 f'<td class="barcol"><span class="distbar" style="width:{w:.1f}%"></span></td></tr>')
    h.append('</tbody></table></div>')
    band = sum(p for l, p in dist if l in ("〜100万円", "〜125万円", "〜150万円"))
    h.append(f'<p class="tnote">n={n}。'
             f'<strong>75〜150万円／戸に {band:.1f}%</strong> が入ります'
             f'（{latest_month}の物価なら {75*factor:,.0f}〜{150*factor:,.0f}万円／戸）。'
             f'一方で 200万円／戸を超える工事も {dict(dist)["200万円超"]:.1f}% あります。</p>')
    return "\n      ".join(h)

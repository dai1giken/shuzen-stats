# -*- coding: utf-8 -*-
"""建設工事費デフレーターの工事種別ごとのページを生成する。

    py build_deflator.py      # build.py から呼ばれる（basis.json が要る）

出力: deflator/<スラッグ>.html ／ deflator/index.html

--- なぜこれを作るのか ---------------------------------------------------
この企画の出発点は「国交省は大規模修繕の工事費指数を既に毎月出している。
**75区分の階層の奥に埋まっていて、誰も辿り着けないだけ**」だった。
トップページの Explorer は16区分しか載せていないので、その宣言を果たしていない。
ここで建築系の全区分を1区分1ページにして、検索から直接辿れる形にする。

--- 土木43区分を出していない理由 -----------------------------------------
`deflator.all` には75区分すべて入っているが、ページにするのは **建築系31区分だけ**。
道路舗装・橋梁・空港・下水道は「大規模修繕統計ビューア」という名前と合わない。
v0.7 で決めた「ページ名で内容が分かることを語感より優先する」に従う。
**出すと決めたら SERIES に足すだけで増える。** データ側は既に全部ある。

--- 「幅は N ポイント」の文言に注意 --------------------------------------
上昇幅のレンジは対象範囲で変わる。実測（2016年4月→2026年6月）:

    現在の16区分  +35.1% 〜 +38.3%（幅 3.2pt）
    建築系31区分  +33.8% 〜 +38.3%（幅 4.5pt）
    全75区分      +26.6% 〜 +41.7%（幅 15.1pt）

**直書きしないこと。**範囲を変えたときに文言だけ古くなる。すべて算出して埋める。

--- 書いてよいこと ------------------------------------------------------
公表値と、そこから引き算・割り算で出る比較まで。
**相関係数・回帰・「〜の影響で」は書かない。**計算した時点で当社の分析になり、
出典バンドの「当社の分析・見解・将来予測は含みません」が嘘になる。
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

from build_pref import (CSS, SITE_URL, bar_cell, cite_block,  # noqa: F401
                        foot, head)

HERE = Path(__file__).resolve().parent

# 基準年のページ（build_kijun.py）も deflator/ に置いてある。**区分ではないので
# 下の刈り取りで消える。**スラッグは向こうを唯一の定義として読む。
from build_kijun import SLUG as SLUG_KIJUN  # noqa: E402

# (e-Stat の @cat01 コード, スラッグ, 見出し名, 定義の言い換え)
#
# 見出し名は e-Stat の区分名を読みやすくしただけ。定義は変えていない。
# 説明は**統計の定義の言い換えに留める**。当社の見立ては書かない。
SERIES: list[tuple[str, str, str, str]] = [
    ("260", "kenchiku-hoshu", "建築補修（改装・改修）",
     "既存の建築物に対する改装・改修工事。マンションの大規模修繕はここに入ります。"),
    ("110", "kenchiku-sogo", "建築総合",
     "建築工事の全体。住宅・非住宅・建築補修を含みます。"),
    ("120", "jutaku-sogo", "住宅総合",
     "住宅の建築工事。木造と非木造の合計です。"),
    ("130", "mokuzo-jutaku", "木造住宅", "木造の住宅。"),
    ("140", "hi-mokuzo-jutaku", "非木造住宅",
     "木造以外の住宅。鉄骨鉄筋コンクリート造・鉄筋コンクリート造・鉄骨造などの合計です。"),
    ("150", "jutaku-src", "住宅・鉄骨鉄筋コンクリート造",
     "鉄骨鉄筋コンクリート造（SRC造）の住宅。"),
    ("160", "jutaku-rc", "住宅・鉄筋コンクリート造",
     "鉄筋コンクリート造（RC造）の住宅。分譲マンションに多い構造です。"),
    ("170", "jutaku-s", "住宅・鉄骨造", "鉄骨造（S造）の住宅。"),
    ("180", "jutaku-cb", "住宅・コンクリートブロックその他",
     "コンクリートブロック造など、上記以外の非木造住宅。"),
    ("190", "hijutaku-sogo", "非住宅総合",
     "住宅以外の建築物。事務所・店舗・工場・倉庫・学校・病院などを含みます。"),
    ("200", "mokuzo-hijutaku", "木造非住宅", "木造の非住宅建築物。"),
    ("210", "hi-mokuzo-hijutaku", "非木造非住宅", "木造以外の非住宅建築物。"),
    ("220", "hijutaku-src", "非住宅・鉄骨鉄筋コンクリート造",
     "鉄骨鉄筋コンクリート造（SRC造）の非住宅建築物。"),
    ("230", "hijutaku-rc", "非住宅・鉄筋コンクリート造",
     "鉄筋コンクリート造（RC造）の非住宅建築物。"),
    ("240", "hijutaku-s", "非住宅・鉄骨造", "鉄骨造（S造）の非住宅建築物。"),
    ("250", "hijutaku-cb", "非住宅・コンクリートブロックその他",
     "コンクリートブロック造など、上記以外の非木造非住宅建築物。"),
    # ---- ここから下は、建設総合を頂点とする階層とは別に同じ統計表に置かれている、
    #      構造と用途の組み合わせの区分（@cat01 コード 700〜840）。
    ("700", "mokuzo-zairai", "木造・在来住宅", "木造の在来工法による住宅。"),
    ("710", "mokuzo-ryosan", "木造・量産住宅", "木造の量産住宅。"),
    ("720", "rc-zairai", "鉄筋・在来住宅", "鉄筋コンクリート造の在来工法による住宅。"),
    ("730", "rc-ryosan", "鉄筋・量産住宅", "鉄筋コンクリート造の量産住宅。"),
    ("740", "s-zairai", "鉄骨・在来住宅", "鉄骨造の在来工法による住宅。"),
    ("750", "s-ryosan", "鉄骨・量産住宅", "鉄骨造の量産住宅。"),
    ("760", "mokuzo-kojo", "木造・工場・倉庫", "木造の工場・倉庫。"),
    ("770", "mokuzo-jimusho", "木造・事務所その他", "木造の事務所その他の建築物。"),
    ("780", "src-kojo", "鉄骨鉄筋・工場・倉庫", "鉄骨鉄筋コンクリート造の工場・倉庫。"),
    ("790", "src-jimusho", "鉄骨鉄筋・事務所その他",
     "鉄骨鉄筋コンクリート造の事務所その他の建築物。"),
    ("800", "rc-kojo", "鉄筋・工場・倉庫", "鉄筋コンクリート造の工場・倉庫。"),
    ("810", "rc-gakko", "鉄筋・学校", "鉄筋コンクリート造の学校。"),
    ("820", "rc-jimusho", "鉄筋・事務所その他",
     "鉄筋コンクリート造の事務所その他の建築物。"),
    ("830", "s-kojo", "鉄骨・工場・倉庫", "鉄骨造の工場・倉庫。"),
    ("840", "s-jimusho", "鉄骨・事務所その他", "鉄骨造の事務所その他の建築物。"),
]

# 階層の親（建設総合を頂点とする側だけ）。パンくずに使う。
# 700〜840 は別の区分体系なので親を持たない。
PARENT = {
    "110": None, "120": "110", "130": "120", "140": "120",
    "150": "140", "160": "140", "170": "140", "180": "140",
    "190": "110", "200": "190", "210": "190",
    "220": "210", "230": "210", "240": "210", "250": "210",
    "260": None,
}

CROSS_NOTE = ("e-Stat の同じ統計表に、建設総合を頂点とする階層とは別に置かれている、"
              "構造と用途の組み合わせの区分です。")


def _pct(a: float, b: float) -> float:
    """b に対する a の変化率（%）。"""
    return (a / b - 1) * 100 if b else 0.0


def _sign(v: float, nd: int = 1) -> str:
    return f"{v:+.{nd}f}%"


def line_chart(months: list[str], vals: list[float], cpi: list[float],
               label: str) -> str:
    """月次の指数を1本、消費者物価を重ねて描く。

    **JS を使わない。**31ページに同じ対話チャートを配るより、静的なSVGと
    下の年次表のほうが壊れない。対話が要る読者にはトップの Explorer がある。
    """
    W, H = 960, 330
    L, R, T, B = 58, 18, 18, 34
    lo = min(min(vals), min(cpi))
    hi = max(max(vals), max(cpi))
    lo = (int(lo / 10) - 1) * 10
    hi = (int(hi / 10) + 1) * 10
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
    # 基準線（指数100の高さ）
    g.append(f'<line x1="{L}" y1="{y(100):.1f}" x2="{W-R}" y2="{y(100):.1f}" '
             f'stroke="var(--ink3)" stroke-width="1" stroke-dasharray="2 3"/>')

    for i, m in enumerate(months):
        if m.endswith("年4月"):
            g.append(f'<text x="{x(i):.1f}" y="{H-12}" text-anchor="middle" '
                     f'font-family="IBM Plex Mono, monospace" font-size="11" '
                     f'fill="var(--ink3)">{m.split("年")[0]}</text>')

    pts_c = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(cpi))
    pts_v = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vals))
    g.append(f'<polyline points="{pts_c}" fill="none" stroke="var(--ink3)" '
             f'stroke-width="1.6" stroke-dasharray="4 3"/>')
    g.append(f'<polyline points="{pts_v}" fill="none" stroke="var(--shu)" '
             f'stroke-width="2.4"/>')
    g.append(f'<circle cx="{x(n-1):.1f}" cy="{y(vals[-1]):.1f}" r="4" fill="var(--shu)"/>')

    g.append(f'<text x="{L+6}" y="{T+14}" font-family="IBM Plex Mono, monospace" '
             f'font-size="12" fill="var(--shu)">■ {label}</text>')
    g.append(f'<text x="{L+6}" y="{T+30}" font-family="IBM Plex Mono, monospace" '
             f'font-size="12" fill="var(--ink3)">-- 消費者物価指数（総合・全国）</text>')

    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{label}の月次推移">'
            + "".join(g) + '</svg>')


def year_rows(months: list[str], vals: list[float], cpi: list[float]) -> str:
    """各年4月の値を並べる。1年1行なので、引用しやすく機械でも読みやすい。"""
    rows = []
    for i, m in enumerate(months):
        if not m.endswith("年4月"):
            continue
        yr = m.split("年")[0]
        rows.append(f'<tr><td>{yr}年4月</td><td class="n">{vals[i]:.1f}</td>'
                    f'<td class="n">{cpi[i]:.1f}</td>'
                    f'<td class="n">{vals[i]-cpi[i]:+.1f}</td></tr>')
    last = len(months) - 1
    rows.append(f'<tr class="me"><td>{months[last]}</td><td class="n">{vals[last]:.1f}</td>'
                f'<td class="n">{cpi[last]:.1f}</td>'
                f'<td class="n">{vals[last]-cpi[last]:+.1f}</td></tr>')
    return "".join(rows)


def build(basis: dict) -> int:
    d = basis.get("deflator", {})
    allser = d.get("all")
    if not allser:
        print("  deflator.all がありません。update_basis.py を先に走らせてください。")
        return 0

    months = d["months"]
    cpi = basis["cpi"]["values"]
    day = basis["generated"].split()[0]
    first, last = months[0], months[-1]
    base = d["base"]

    # 対象にする区分のうち、データが実際にあるものだけ。
    # 区分が消えたら黙って落とさず、件数を表示して気づけるようにする。
    target = [(c, s, nm, note) for c, s, nm, note in SERIES if c in allser]
    if len(target) != len(SERIES):
        miss = [c for c, *_ in SERIES if c not in allser]
        print(f"  ⚠ 統計表に無い区分を飛ばしました: {miss}")

    # 建築系のなかでの順位（2016年4月比の大きい順）と、全75区分のなかでの順位。
    def chg(code: str) -> float:
        v = allser[code]["values"]
        return _pct(v[-1], v[0])

    ranked = sorted([c for c, *_ in target], key=lambda c: -chg(c))
    all_ranked = sorted(allser, key=lambda c: -chg(c))
    name_of = {c: nm for c, s, nm, _ in target}
    slug_of = {c: s for c, s, nm, _ in target}

    # **端点を丸めてから引き算する。**丸める前の差を出すと、画面に並ぶ
    # 「33.8% 〜 38.3%」を読者が引き算した 4.5 と、表示した幅 4.6 が食い違う。
    spread_lo, spread_hi = round(chg(ranked[-1]), 1), round(chg(ranked[0]), 1)
    # バーは「中央値との差」に付ける。**上昇率そのものに 0 起点のバーを
    # 付けてはいけない。**31区分は 33.8〜38.3% の狭い帯にあるので、
    # 0 からの長さにすると全部ほぼ満タンになって何も見えない（実際にそうなった）。
    # 中央値からの差なら、どれが上でどれが下かが一目で分かる。
    _med = statistics.median(chg(c) for c in ranked)
    _dev = max(abs(chg(c) - _med) for c in ranked) or 1.0
    cpi_chg = _pct(cpi[-1], cpi[0])

    out = HERE / "deflator"
    out.mkdir(exist_ok=True)
    # 刈り取り。SERIES から外した区分のファイルが残ると、サイトマップの glob が
    # 載せ続け、一覧から消えたページだけが公開され続ける。
    #
    # **区分ではないページも deflator/ に置いてある。**基準年のページ
    # （build_kijun.py）がそれで、keep に入れ忘れるとここで黙って消える。
    # build.py は build_deflator → build_kijun の順で呼ぶので実害は出ないが、
    # 順番を入れ替えた瞬間にページが1枚消えるので、名前でも守っておく。
    keep = ({f"{s}.html" for s in slug_of.values()}
            | {"index.html", f"{SLUG_KIJUN}.html"})
    for f in out.glob("*.html"):
        if f.name not in keep:
            f.unlink()

    written: list[str] = []
    for code, slug, nm, note in target:
        v = allser[code]["values"]
        latest, mom, yoy = v[-1], _pct(v[-1], v[-2]), _pct(v[-1], v[-13])
        since = _pct(v[-1], v[0])
        rank = ranked.index(code) + 1
        arank = all_ranked.index(code) + 1
        gap = latest - cpi[-1]

        canonical = f"{SITE_URL}deflator/{slug}.html"
        title = f"{nm}の建設工事費デフレーター｜{last} {latest:.1f}（{base}）"
        desc = (f"国土交通省「建設工事費デフレーター」の{nm}は{last}時点で {latest:.1f}"
                f"（{base}）。前年同月比 {_sign(yoy)}、{first}比 {_sign(since)}。"
                f"同期間の消費者物価は {_sign(cpi_chg)}。e-Stat API の公表値。")

        h = [head(title, desc, canonical, crumb="工事種別")]
        h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて国土交通省「建設工事費デフレーター」の公表値です。</strong>
    e-Stat の API から取得し、<strong>変化率を割り算で出すところまで</strong>を行っています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表統計 ／ 工事種別</span>
  <h1>{nm}
    <span class="sub">建設工事費デフレーター（{base}）の{nm}は、{last}時点で <strong>{latest:.1f}</strong>。{first}から {_sign(since)} です。{note}</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">{last}</span>
      <div class="v">{latest:.1f}</div>
      <p>{base}。前月比 {_sign(mom)}。</p>
    </div>
    <div class="kpi">
      <span class="k">前年同月比</span>
      <div class="v">{_sign(yoy)}</div>
      <p>{months[-13]} の {v[-13]:.1f} から。</p>
    </div>
    <div class="kpi">
      <span class="k">{first}比</span>
      <div class="v">{_sign(since)}</div>
      <p>同じ期間の消費者物価は {_sign(cpi_chg)}。</p>
    </div>
    <div class="kpi">
      <span class="k">上昇幅の順位</span>
      <div class="v">{rank}<small>位 / {len(target)}</small></div>
      <p>建築系{len(target)}区分中。全{len(allser)}区分では {arank} 位。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig.</span>{nm}の月次推移（{first}〜{last}）</h2>
    <p class="lede">朱の線が{nm}、破線が消費者物価指数（総合・全国）です。どちらも指数で、建設工事費デフレーターは{base}、消費者物価指数は2020年＝100 と、それぞれの基準にそろえてあります。点線は 100 の高さです。</p>
    <div class="chartbox">
      <div class="chart-head"><span class="srcchip">出典 国土交通省</span><span><strong>建設工事費デフレーター</strong>　{base}・e-Stat API 取得・{day}</span></div>
      {line_chart(months, v, cpi, nm)}
      <div class="chart-foot">
        出典：国土交通省「建設工事費デフレーター」{base}／<a href="{d["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={d["statsDataId"]}</a>　工事種別「{allser[code]["name"]}」（@cat01={code}）　表章項目「建設工事費デフレーター」（後方3ヶ月平均値ではない方）　取得日 {day}
      </div>
    </div>
  </section>

  <section>
    <h2><span class="idx">Table</span>各年4月の値</h2>
    <p class="lede">年に1行。いちばん下が最新月です。差は{nm}から消費者物価を引いたポイント数で、どちらも指数なので引き算できます。</p>
    <div class="tablebox"><table>
      <thead><tr><th>時点</th><th>{nm}</th><th>消費者物価</th><th>差</th></tr></thead>
      <tbody>{year_rows(months, v, cpi)}</tbody>
    </table></div>
    <p class="colophon">単位：指数。建設工事費デフレーターは{base}、消費者物価指数は2020年＝100。{last}時点の差は {gap:+.1f} ポイントです。基準が別なので、差は「基準年からの離れかたの違い」を見るためのものです。</p>
  </section>
''')

        # 階層のパンくずと兄弟
        fam = []
        p = PARENT.get(code)
        if p and p in slug_of:
            fam.append(f'<a href="{slug_of[p]}.html">{name_of[p]}</a> の内訳')
        kids = [c for c in slug_of if PARENT.get(c) == code]
        if kids:
            fam.append("内訳：" + "、".join(
                f'<a href="{slug_of[c]}.html">{name_of[c]}</a>'
                for c in sorted(kids, key=lambda c: -chg(c))))
        if code >= "700":
            fam.append(CROSS_NOTE)
        if fam:
            h.append(f'''  <section>
    <h2><span class="idx">Tree</span>統計表のなかでの位置</h2>
    <p class="lede">{"　／　".join(fam)}</p>
  </section>
''')

        rows = []
        for c in ranked:
            cls = ' class="me"' if c == code else ""
            lab = name_of[c] if c == code else f'<a href="{slug_of[c]}.html">{name_of[c]}</a>'
            vv = allser[c]["values"]
            rows.append(f'<tr{cls}><td class="n">{ranked.index(c)+1}</td><td>{lab}</td>'
                        f'<td class="n">{vv[-1]:.1f}</td>'
                        f'<td class="n">{_sign(_pct(vv[-1], vv[-13]))}</td>'
                        f'<td class="n">{_sign(chg(c))}</td>'
                        + bar_cell(f'{chg(c) - _med:+.1f}', chg(c) - _med,
                                   -_dev, _dev, "var(--shu)", zero=True) + '</tr>')
        h.append(f'''  <section>
    <h2><span class="idx">Rank</span>建築系{len(target)}区分の比較</h2>
    <p class="lede">{first}からの上昇が大きい順です。{spread_hi:.1f}% から {spread_lo:.1f}% までの範囲に収まっており、幅は {spread_hi-spread_lo:.1f} ポイントです。同じ期間の消費者物価は {_sign(cpi_chg)} でした。</p>
    <div class="tablebox"><table>
      <thead><tr><th>順</th><th>工事種別</th><th>{last}</th><th>前年同月比</th><th>{first}比</th><th>中央値との差</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table></div>
    <p class="colophon">出典：国土交通省「建設工事費デフレーター」（statsDataId={d["statsDataId"]}）{base}。取得日 {day}。「中央値との差」は、{first}比の上昇率から31区分の中央値 {_med:.1f}% を引いたポイント数です。バーはその差の大きさで、中央が 0 になります。</p>
  </section>

  <a class="cta" href="index.html">
    <span class="k">工事種別の一覧へ</span>
    <span class="n">建設工事費デフレーター</span>
    <span class="d">建築系{len(target)}区分を並べて比べられます</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{SITE_URL}#explorer">
    <span class="k">Tool ／ 重ねて見る</span>
    <span class="n">工事種別エクスプローラ</span>
    <span class="d">主要16区分を並べ替えたり、折れ線に重ねたりできます</span>
    <span class="arrow">→</span>
  </a>
''')
        h.append(cite_block(canonical, day))
        h.append(foot())
        (out / f"{slug}.html").write_text("".join(h), encoding="utf-8")
        written.append(slug)

    # ---- 一覧 ----
    canonical = f"{SITE_URL}deflator/"
    title = f"建設工事費デフレーター 工事種別一覧｜{last}（{base}）"
    desc = (f"国土交通省「建設工事費デフレーター」の建築系{len(target)}区分を、"
            f"{last}時点の値と{first}比で並べています。"
            f"上昇幅は {spread_lo:.1f}% 〜 {spread_hi:.1f}%、"
            f"同期間の消費者物価は {_sign(cpi_chg)}。e-Stat API の公表値。")
    idx = [head(title, desc, canonical, crumb="工事種別")]
    idx.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて国土交通省「建設工事費デフレーター」の公表値です。</strong>
    e-Stat の API から取得し、<strong>変化率を割り算で出すところまで</strong>を行っています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表統計 ／ 工事種別</span>
  <h1>建設工事費デフレーター 工事種別一覧
    <span class="sub">この統計表は工事種別を <strong>{len(allser)}区分</strong> 持っています。そのうち建築にあたる <strong>{len(target)}区分</strong> を1区分1ページで出しています。{first}から{last}までの上昇は {spread_lo:.1f}% 〜 {spread_hi:.1f}%（幅 {spread_hi-spread_lo:.1f} ポイント）、同じ期間の消費者物価は {_sign(cpi_chg)} でした。</span>
  </h1>
''')
    rows = []
    for c in ranked:
        vv = allser[c]["values"]
        rows.append(f'<tr><td class="n">{ranked.index(c)+1}</td>'
                    f'<td><a href="{slug_of[c]}.html">{name_of[c]}</a></td>'
                    f'<td class="n">{vv[-1]:.1f}</td>'
                    f'<td class="n">{_sign(_pct(vv[-1], vv[-2]))}</td>'
                    f'<td class="n">{_sign(_pct(vv[-1], vv[-13]))}</td>'
                    f'<td class="n">{_sign(chg(c))}</td>'
                    + bar_cell(f'{chg(c) - _med:+.1f}', chg(c) - _med,
                               -_dev, _dev, "var(--shu)", zero=True) + '</tr>')
    idx.append(f'''  <a class="cta" href="{SLUG_KIJUN}.html">
    <span class="k">Tool ／ 基準年をそろえる</span>
    <span class="n">建設工事費デフレーターの基準年</span>
    <span class="d">この指数は基準年の違う系列が同時に公表されています。手元の資料の値がどの基準か分からないまま割り算すると、答えが静かにずれます</span>
    <span class="arrow">→</span>
  </a>

  <section>
    <h2><span class="idx">Rank</span>建築系{len(target)}区分</h2>
    <p class="lede">{first}からの上昇が大きい順です。工事種別名をクリックすると、その区分の月次推移と各年の値が出ます。</p>
    <div class="tablebox"><table>
      <thead><tr><th>順</th><th>工事種別</th><th>{last}</th><th>前月比</th><th>前年同月比</th><th>{first}比</th><th>中央値との差</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table></div>
    <p class="colophon">単位：指数（{base}）。出典：国土交通省「建設工事費デフレーター」（statsDataId={d["statsDataId"]}）。取得日 {day}。土木にあたる区分もこの統計表に含まれていますが、このサイトではページにしていません。</p>
  </section>

  <a class="cta" href="{SITE_URL}#explorer">
    <span class="k">Tool ／ 重ねて見る</span>
    <span class="n">工事種別エクスプローラ</span>
    <span class="d">主要16区分を並べ替えたり、折れ線に重ねたりできます</span>
    <span class="arrow">→</span>
  </a>
''')
    idx.append(cite_block(canonical, day))
    idx.append(foot())
    (out / "index.html").write_text("".join(idx), encoding="utf-8")

    print(f"  建築系 {len(target)} 区分（全{len(allser)}区分中）　"
          f"上昇幅 {spread_lo:.1f}%〜{spread_hi:.1f}%（幅 {spread_hi-spread_lo:.1f}pt）　"
          f"CPI {_sign(cpi_chg)}")
    return len(written)


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    n = build(basis)
    print(f"deflator/ に {n} 区分 ＋ 一覧を生成しました")


if __name__ == "__main__":
    main()

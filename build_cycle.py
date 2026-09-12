# -*- coding: utf-8 -*-
"""修繕周期のページを生成する。

    py build_cycle.py      # build.py から呼ばれる（basis.json が要る）

出力: cycle/index.html

--- なぜこれを作るのか ---------------------------------------------------
令和6年6月の改定で、長期修繕計画作成ガイドラインの修繕周期は
**幅（例：12〜15年）で示す形**になった。ところが世の中の説明は
「大規模修繕は12年周期」で止まっているものが多い。改定前の記述が
そのまま残っている。

原典は PDF の様式第3-2号の中にあって、項目が81行ある表を1枚の紙に
詰め込んだものなので、そのままでは読めない。**読める形に並べ直すだけ**で
価値が出る。このサイトがやっている「既にあるものを読める形にする」と
同じことを、統計ではなくガイドラインに対して行う。

--- 代表値に丸めないこと -------------------------------------------------
原典が幅で書いているものを「13年」のような1つの数字にしてはいけない。
幅で示すようになったことが改定の中身なので、**丸めた時点で改定前に戻る。**

--- 書いてよいこと ------------------------------------------------------
原典の転記と、転記した表の数え上げ（何件が12〜15年か 等）まで。
**「何年目に実施すべき」は書かない。**原典自身が「（参考）」と断っている
ものを、当社が推奨に読み替えることになる。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from build_pref import SITE_URL, cite_block, foot, head
from shuzen_cycle import (CYCLES, SENYU, SOURCE_NAME, SOURCE_PAGES, SOURCE_REVISION,
                          SOURCE_URL, period_text, verify)

HERE = Path(__file__).resolve().parent

EXTRA_CSS = """
<style>
.rng{position:relative;height:16px;min-width:180px;background:var(--sunk);border-radius:2px}
.rng i{position:absolute;top:3px;height:10px;background:var(--shu);border-radius:1px;display:block}
.rng b{position:absolute;top:0;bottom:0;width:1px;background:var(--rule)}
.rngax{display:flex;justify-content:space-between;font-family:var(--mono);font-size:10px;color:var(--ink3);margin-top:3px}
.grp td{background:var(--sunk);font-family:var(--cond);font-weight:700;font-size:14px;color:var(--ink)}
.sub2{font-size:12px;color:var(--ink3);display:block;margin-top:2px}
</style>"""

MAXY = 42  # 目盛の上限。最長の周期（避雷針設備 38〜42年）に合わせる。


def _bar(lo: int | None, hi: int | None) -> str:
    """周期の幅を帯で描く。**1本の棒にしない。**幅があることが改定の中身なので、
    中央値の位置に点を打つような描き方をすると、幅を潰したのと同じになる。"""
    if lo is None:
        return '<td></td>'
    x1, x2 = lo / MAXY * 100, hi / MAXY * 100
    w = max(x2 - x1, 1.2)
    ticks = "".join(f'<b style="left:{t/MAXY*100:.1f}%"></b>' for t in (12, 24, 36))
    return (f'<td><div class="rng" title="{period_text(lo, hi)}">{ticks}'
            f'<i style="left:{x1:.1f}%;width:{w:.1f}%"></i></div></td>')


def build(basis: dict) -> int:
    n_rows, bad = verify()
    if bad:
        for b in bad:
            print("  ✗ " + b)
        print("  修繕周期が原典と一致しないのでページを作りません。")
        return 0

    day = basis["generated"].split()[0]
    rows = list(CYCLES) + [SENYU]
    have = [r for r in rows if r[5] is not None]

    cnt = Counter(period_text(r[5], r[6]) for r in have)
    top_label, top_n = cnt.most_common(1)[0]
    kinds = len(cnt)
    ymin = min(r[5] for r in have)
    ymax = max(r[6] for r in have)
    n_dai = len({r[0] for r in rows})

    out = HERE / "cycle"
    out.mkdir(exist_ok=True)
    canonical = f"{SITE_URL}cycle/"

    title = (f"マンションの修繕周期 部位別一覧｜{SOURCE_REVISION}ガイドラインの"
             f"{len(have)}項目（最多は{top_label}）")
    desc = (f"国土交通省「長期修繕計画作成ガイドライン」（{SOURCE_REVISION}）様式第3-2号の記載例から、"
            f"推定修繕工事項目ごとの修繕周期 {len(have)}項目を部位別に並べ直しました。"
            f"周期は{kinds}種類あり、最も多いのは{top_label}で{top_n}項目（{top_n/len(have)*100:.1f}%）。"
            f"全体では{ymin}年から{ymax}年まで幅があります。原典の転記です。")

    h = [head(title, desc, canonical, crumb="修繕周期", extra_css=EXTRA_CSS)]
    h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの内容は、すべて国土交通省「長期修繕計画作成ガイドライン」（{SOURCE_REVISION}）の記載例の転記です。</strong>
    原典の表を部位別に並べ直し、<strong>項目を数え上げるところまで</strong>を行っています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表資料 ／ 修繕周期</span>
  <h1>マンションの修繕周期 部位別一覧
    <span class="sub">{SOURCE_REVISION}の長期修繕計画作成ガイドラインでは、修繕周期は<strong>幅で示されています</strong>（例：12〜15年）。様式第3-2号の記載例にある{len(have)}項目を並べると、周期は{kinds}種類あり、最も多いのは{top_label}で {top_n}項目（{top_n/len(have)*100:.1f}%）。全体では{ymin}年から{ymax}年まで開きがあります。</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">最も多い周期</span>
      <div class="v">{top_label}</div>
      <p>{len(have)}項目中 {top_n}項目（{top_n/len(have)*100:.1f}%）。</p>
    </div>
    <div class="kpi">
      <span class="k">周期の種類</span>
      <div class="v">{kinds}<small>種</small></div>
      <p>ひとつの周期に集中してはいません。</p>
    </div>
    <div class="kpi">
      <span class="k">周期の範囲</span>
      <div class="v">{ymin}<small>〜{ymax}年</small></div>
      <p>鉄部塗装から避雷針設備まで。</p>
    </div>
    <div class="kpi">
      <span class="k">掲載項目</span>
      <div class="v">{len(rows)}<small>項目</small></div>
      <p>{n_dai}区分。うち周期の記載があるもの {len(have)}項目。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Note</span>「12年周期」と書かれていないこと</h2>
    <p class="lede">原典の様式第3-2号は、工事区分ごとに <strong>12〜15年</strong> のように<strong>幅</strong>で周期を示しています。単一の年数は書かれていません。数えると{top_label}が最多ですが、それでも{len(have)}項目中{top_n}項目で、全体の{top_n/len(have)*100:.1f}%です。残りは{ymin}年から{ymax}年まで散らばっています。</p>
    <div class="warn">
      <h4>この表が何であって、何でないか</h4>
      <ul>
        <li>原典は各欄に<strong>「（参考）」</strong>と明記しています。守るべき基準ではなく、計画を作るときの<strong>記載例</strong>です。</li>
        <li>原典は「マンションの仕様、立地条件等を考慮して設定します」とし、既存マンションでは<strong>調査・診断の結果に基づいて設定する</strong>としています。この表の年数がそのまま個別の建物に当てはまるものではありません。</li>
        <li><strong>当社はこの表に基づく推奨をしていません。</strong>実施時期は、建物ごとの劣化状況によって決まります。</li>
        <li>周期は<strong>工事区分ごとに違います</strong>。同じ部位でも「塗替」と「除去・塗装」では別の周期が示されています。</li>
      </ul>
    </div>
  </section>
''')

    # ---- 本表 ----
    trows = []
    cur_dai = cur_chu = None
    for dai, chu, item, bui, kubun, lo, hi, how in rows:
        if dai != cur_dai:
            trows.append(f'<tr class="grp"><td colspan="5">{dai}</td></tr>')
            cur_dai, cur_chu = dai, None
        if chu != cur_chu:
            trows.append(f'<tr class="grp"><td colspan="5">　{chu}</td></tr>')
            cur_chu = chu
        per = period_text(lo, hi)
        name = f'{item}<span class="sub2">{bui}</span>' if bui else item
        trows.append(f'<tr><td>{name}</td><td>{kubun or "—"}</td>'
                     f'<td class="n">{per}</td>{_bar(lo, hi)}'
                     f'<td>{how or "—"}</td></tr>')

    h.append(f'''  <section>
    <h2><span class="idx">Table</span>推定修繕工事項目ごとの修繕周期</h2>
    <p class="lede">原典の様式第3-2号「推定修繕工事項目、修繕周期等の設定内容」の記載例を、そのまま並べたものです。帯は周期の幅で、目盛の縦線は左から12年・24年・36年です。「工事区分」「修繕周期」「想定している修繕方法等」は原典で<strong>いずれも「（参考）」</strong>と付記されている欄です。</p>
    <div class="tablebox"><table>
      <thead><tr><th>推定修繕工事項目／対象部位等</th><th>工事区分</th><th>修繕周期</th><th>0 〜 {MAXY}年</th><th>想定している修繕方法等</th></tr></thead>
      <tbody>{"".join(trows)}</tbody>
    </table></div>
    <p class="colophon">出典：{SOURCE_NAME}（{SOURCE_REVISION}）。{SOURCE_PAGES}。<a href="{SOURCE_URL}" target="_blank" rel="noopener">原典PDF</a>。取得日 {day}。「－」は原典に記載のない欄です。Ⅴ性能向上工事項目・Ⅶ諸経費等は原典で周期が空欄のため載せていません。対象部位等の「／」は、原典でセルが複数行に分かれている箇所の区切りで、原典の文字ではありません。</p>
  </section>
''')

    # ---- 周期別の数え上げ ----
    drows = []
    mx = max(cnt.values())
    for label, n in sorted(cnt.items(), key=lambda x: (-x[1], x[0])):
        w = n / mx * 100
        drows.append(f'<tr><td class="n">{label}</td><td class="n">{n}</td>'
                     f'<td class="n">{n/len(have)*100:.1f}%</td>'
                     f'<td><div class="rng"><i style="left:0;width:{w:.1f}%"></i></div></td></tr>')

    h.append(f'''  <section>
    <h2><span class="idx">Count</span>周期ごとの項目数</h2>
    <p class="lede">上の表を周期の表記ごとに数えたものです。{kinds}種類に分かれています。</p>
    <div class="tablebox"><table>
      <thead><tr><th>修繕周期</th><th>項目数</th><th>割合</th><th></th></tr></thead>
      <tbody>{"".join(drows)}</tbody>
    </table></div>
    <p class="colophon">母数は周期の記載がある {len(have)}項目です。割合は小数第1位まで。出典は上の表と同じ。</p>
  </section>

  <a class="cta" href="{SITE_URL}deflator/kijun-nendo.html">
    <span class="k">Tool ／ 工事費の指数</span>
    <span class="n">建設工事費デフレーターの基準年</span>
    <span class="d">長期修繕計画の金額を今の水準に直すときは、指数の基準年をそろえる必要があります</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{SITE_URL}">
    <span class="k">大規模修繕統計ビューア</span>
    <span class="n">トップへ</span>
    <span class="d">工事費指数・戸あたり工事金額・修繕積立金の公表値</span>
    <span class="arrow">→</span>
  </a>
''')
    h.append(cite_block(canonical, day))
    h.append(foot())
    (out / "index.html").write_text("".join(h), encoding="utf-8")

    print(f"  修繕周期 {len(rows)}項目（周期あり {len(have)}）　"
          f"最多 {top_label} {top_n}件（{top_n/len(have)*100:.1f}%）　"
          f"{kinds}種類 / {ymin}〜{ymax}年　原典突合 {n_rows}行 OK")
    return 1


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    n = build(basis)
    print(f"cycle/ に {n} 枚生成しました")


if __name__ == "__main__":
    main()

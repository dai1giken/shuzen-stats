# -*- coding: utf-8 -*-
"""建設工事費デフレーターの「基準年」のページを生成する。

    py build_kijun.py      # build.py から呼ばれる（basis.json が要る）

出力: deflator/kijun-nendo.html

--- なぜこれを作るのか ---------------------------------------------------
建設工事費デフレーターは、**基準年の違う系列が同時に公表され続けている**。
2020年度基準（0004055083）・2015年度基準（0003447801）・2011年度基準
（0003447798）がどれも e-Stat に生きていて、更新も止まっていない。

その結果、**同じ月・同じ工事種別に、公式な数字が複数並ぶ**。
2026年3月の建築補修は、2015年度基準では 135.8、2020年度基準では 125.7。
どちらも国交省の公表値で、どちらも正しい。基準が違うだけ。

読者が実際に困るのはここで、しかも**気づかないまま計算できてしまう**。
古い長期修繕計画に載っている指数と、いま e-Stat で引いた指数をそのまま
割り算すると、答えは静かに間違う。エラーは出ない。

--- このページが書いてよいこと -------------------------------------------
公表値と、**公表値どうしの割り算**まで。
改基準係数は「旧基準側の2020年度平均で割る」という算術で、当社の推計ではない。
残差（割り戻した値と実際の2020年度基準の差）も実測値で、**隠さず出す**。

**「どの基準を使うべきか」は書かない。**それは当社の見解になる。
書けるのは「基準をまたいで割り算すると値がこうずれる」という算術の事実まで。
"""
from __future__ import annotations

import json
from pathlib import Path

from build_pref import CSS, SITE_URL, cite_block, foot, head  # noqa: F401

HERE = Path(__file__).resolve().parent

SLUG = "kijun-nendo"

# このページだけで使う CSS。**CSS 本体には足さない。**
# 足すと349ページ全部のバイト列が動いて、生成物の突合ができなくなる。
EXTRA_CSS = """
<style>
.conv{margin-top:20px;padding:22px 20px 18px;background:var(--sunk);border:1px solid var(--rule)}
.conv h3{font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--shu);margin:0 0 14px;font-weight:500}
.convrow{display:flex;flex-wrap:wrap;align-items:center;gap:10px;font-size:14px;line-height:2.4}
.conv select,.conv input{font-family:var(--mono);font-size:13px;padding:4px 7px;background:var(--raise);color:var(--ink);border:1px solid var(--rule);border-radius:2px}
.conv select{max-width:100%}
.conv input[type=number]{width:8ch;text-align:right;font-variant-numeric:tabular-nums}
.convout{margin-top:16px;padding-top:14px;border-top:1px solid var(--rule)}
.convout table{width:100%;border-collapse:collapse;font-size:14px}
.convout th,.convout td{padding:7px 8px;border-bottom:1px solid var(--rule-soft);text-align:left}
.convout td.n{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right}
.convout tr.me td{color:var(--shu);font-weight:600}
.convout tr.me td.n{font-size:17px}
.convnote{margin:12px 0 0;font-size:12px;line-height:1.7;color:var(--ink3)}
</style>"""


def _fy_label(m: str) -> str:
    return m


def build(basis: dict) -> int:
    db = basis.get("deflator_bases")
    if not db:
        print("  deflator_bases がありません。update_basis.py を先に走らせてください。")
        return 0

    d = basis["deflator"]
    allser = d["all"]
    months = d["months"]
    day = basis["generated"].split()[0]
    first, last = months[0], months[-1]
    pcode = d["primary_code"]
    pname = d["primary"]

    out = HERE / "deflator"
    out.mkdir(exist_ok=True)

    # ---- 主系列（建築補修）で、同じ月に並ぶ値を出す -----------------------
    v20 = dict(zip(months, allser[pcode]["values"]))
    rows15 = db["2015"]["series"].get(pcode)
    if not rows15:
        print(f"  主系列 {pcode} が2015年度基準にありません。ページを作りません。")
        return 0
    v15 = dict(zip(rows15["months"], rows15["values"]))

    # 両方にある最新月。2015年度基準のほうが公表が遅れるので last とは限らない。
    shared = [m for m in months if m in v15]
    m_both = shared[-1]
    gap_both = v15[m_both] - v20[m_both]

    # ---- 誤用したときのずれ（実測） --------------------------------------
    m_old = shared[0]
    correct = v20[m_both] / v20[m_old]
    wrong = v20[m_both] / v15[m_old]
    yen = 100_000_000
    diff_man = (correct - wrong) * yen / 10_000

    # ---- 接続の精度 -------------------------------------------------------
    f15 = rows15["factor"]
    res_lo, res_hi = rows15["res_min"], rows15["res_max"]
    ov = rows15["overlap"]
    # 31区分ぜんぶで見たときの最大のぶれ。主系列だけ見て安心しないため。
    worst = max(max(abs(s["res_min"]), abs(s["res_max"]))
                for s in db["2015"]["series"].values())

    # ---- 換算ツールが使う係数（区分ごとに1つの数字だけ）-------------------
    # **系列そのものは埋めない。**31区分×3基準の月次を全部埋めると、
    # 工事種別ページで index.html を 212KB→271KB に太らせたのと同じことになる。
    # 区分名は **SERIES の読みやすい名前**を使う。e-Stat の生ラベル
    # （「建設総合_建築補修」）をそのまま出すと、見出しやパンくずと食い違う。
    from build_deflator import SERIES as DEFLATOR_SERIES
    nice = {code: nm for code, _slug, nm, _note in DEFLATOR_SERIES}

    conv = []
    for code, s in db["2015"]["series"].items():
        f11 = db["2011"]["series"].get(code, {}).get("factor")
        conv.append({"c": code, "n": nice.get(code, s["name"]), "s": s["slug"],
                     "f15": s["factor"], "f11": f11,
                     # 割り戻しと実際の公表値の差（実測）。注記に出す。
                     "lo": s["res_min"], "hi": s["res_max"]})
    conv.sort(key=lambda x: (x["c"] != pcode, x["c"]))

    canonical = f"{SITE_URL}deflator/{SLUG}.html"
    title = (f"建設工事費デフレーターの基準年｜{m_both}の{pname}は"
             f"2015年度基準 {v15[m_both]:.1f}／2020年度基準 {v20[m_both]:.1f}")
    desc = (f"建設工事費デフレーターは2011年度・2015年度・2020年度の各基準が同時に公表されています。"
            f"{m_both}の{pname}は2015年度基準で {v15[m_both]:.1f}、2020年度基準で {v20[m_both]:.1f} と"
            f"{abs(gap_both):.1f}ポイント違います。基準をそろえる換算ツールと、"
            f"基準をまたいで割ったときのずれを公表値で示します。")

    h = [head(title, desc, canonical, crumb="工事種別", extra_css=EXTRA_CSS)]
    h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて国土交通省「建設工事費デフレーター」の公表値です。</strong>
    2020年度基準・2015年度基準・2011年度基準の3つの統計表を e-Stat の API から取得し、
    <strong>公表値どうしの割り算をするところまで</strong>を行っています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表統計 ／ 工事種別</span>
  <h1>建設工事費デフレーターの基準年
    <span class="sub">この指数は、<strong>基準年の違う系列が同時に公表され続けています</strong>。{m_both}の{pname}は、2015年度基準では <strong>{v15[m_both]:.1f}</strong>、2020年度基準では <strong>{v20[m_both]:.1f}</strong>。差は {abs(gap_both):.1f} ポイントです。どちらも国土交通省の公表値で、基準年が違うだけです。</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">{m_both}・2020年度基準</span>
      <div class="v">{v20[m_both]:.1f}</div>
      <p>{pname}。statsDataId={d["statsDataId"]}。</p>
    </div>
    <div class="kpi">
      <span class="k">同月・2015年度基準</span>
      <div class="v">{v15[m_both]:.1f}</div>
      <p>同じ月・同じ工事種別。statsDataId={db["2015"]["statsDataId"]}。</p>
    </div>
    <div class="kpi">
      <span class="k">差</span>
      <div class="v">{gap_both:+.1f}<small>pt</small></div>
      <p>基準年が違うので、そのままでは比べられません。</p>
    </div>
    <div class="kpi">
      <span class="k">公表中の基準</span>
      <div class="v">3<small>種</small></div>
      <p>2011年度・2015年度・2020年度。いずれも e-Stat で引けます。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Tool</span>基準をそろえる</h2>
    <p class="lede">手元の資料に書かれている指数が、どの基準のものか分かっている場合に、他の基準での値に直します。使うのは<strong>改基準係数による割り算だけ</strong>です。工事種別ごとの係数は下の表に全部載せてあります。</p>

    <div class="conv">
      <h3>Convert ／ 基準の読み替え</h3>
      <div class="convrow">
        <label>工事種別 <select id="cvCode"></select></label>
        <label>指数の値 <input type="number" id="cvVal" min="1" max="999" step="0.1" value="{v15[m_both]:.1f}"></label>
        <label>この値の基準 <select id="cvBase">
          <option value="15" selected>2015年度＝100</option>
          <option value="20">2020年度＝100</option>
          <option value="11">2011年度＝100</option>
        </select></label>
      </div>
      <div class="convout">
        <table>
          <thead><tr><th>基準</th><th>この値に相当する指数</th><th>改基準係数</th></tr></thead>
          <tbody id="cvOut"></tbody>
        </table>
      </div>
      <p class="convnote" id="cvNote"></p>
    </div>

    <div class="warn">
      <h4>基準をまたいで割り算しないこと</h4>
      <ul>
        <li>古い資料の指数と、いま引いた指数を<strong>そのまま割ると答えがずれます</strong>。エラーは出ません。</li>
        <li>実測（{pname}・{m_old}→{m_both}）：2020年度基準でそろえると <strong>{(correct-1)*100:+.1f}%</strong>。分母だけ2015年度基準のままにすると <strong>{(wrong-1)*100:+.1f}%</strong>。</li>
        <li>1億円に対して <strong>{diff_man:,.0f}万円</strong> の差になります。</li>
        <li><strong>ひとつの系列の中だけで割り算すれば、この問題は起きません。</strong>基準の読み替えが要るのは、系列をまたぐときだけです。</li>
      </ul>
    </div>
  </section>
''')

    # ---- 各年4月の3基準対照 ----------------------------------------------
    v11 = {}
    if pcode in db["2011"]["series"]:
        r11 = db["2011"]["series"][pcode]
        v11 = dict(zip(r11["months"], r11["values"]))

    yrows = []
    allm = sorted(set(v20) | set(v15) | set(v11),
                  key=lambda s: (int(s.split("年")[0]), int(s.split("年")[1].rstrip("月"))))
    for m in allm:
        if not m.endswith("年4月") and m != allm[-1]:
            continue
        cls = ' class="me"' if m == allm[-1] else ""
        c11 = f'{v11[m]:.1f}' if m in v11 else "—"
        c15 = f'{v15[m]:.1f}' if m in v15 else "—"
        c20 = f'{v20[m]:.1f}' if m in v20 else "—"
        conv15 = f'{v15[m]/f15*100:.1f}' if m in v15 else "—"
        yrows.append(f'<tr{cls}><td>{m}</td><td class="n">{c11}</td>'
                     f'<td class="n">{c15}</td><td class="n">{c20}</td>'
                     f'<td class="n">{conv15}</td></tr>')

    h.append(f'''  <section>
    <h2><span class="idx">Table</span>{pname}を3つの基準で並べる</h2>
    <p class="lede">同じ月・同じ工事種別を、公表されている基準ごとに並べたものです。「—」はその基準の統計表に収録されていない期間です。いちばん右は、2015年度基準の値を改基準係数 {f15:.4f} で割って 2020年度＝100 にそろえたものです。4列目と比べると、割り戻しでどれだけ一致するかが分かります。</p>
    <div class="tablebox"><table>
      <thead><tr><th>時点</th><th>2011年度＝100</th><th>2015年度＝100</th><th>2020年度＝100</th><th>2015→2020 換算</th></tr></thead>
      <tbody>{"".join(yrows)}</tbody>
    </table></div>
    <p class="colophon">単位：指数。出典：国土交通省「建設工事費デフレーター」2020年度基準（statsDataId={d["statsDataId"]}）／2015年度基準（statsDataId={db["2015"]["statsDataId"]}）／2011年度基準（statsDataId={db["2011"]["statsDataId"]}）。取得日 {day}。{pname}は2015年度基準で新しく設けられた区分のため、2011年度基準には収録がありません。</p>
  </section>

  <section>
    <h2><span class="idx">Check</span>割り戻しはどこまで一致するか</h2>
    <p class="lede">基準が変わるときは、指数の重みづけも入れ替わります。そのため改基準係数で割り戻した値と、実際に公表されている2020年度基準の値は<strong>完全には一致しません</strong>。{pname}で重なっている {ov} ヶ月について実測すると、差は {res_lo:+.2f} 〜 {res_hi:+.2f} ポイントでした。工事種別ページにしている{len(db["2015"]["series"])}区分すべてで見ると、差の絶対値はいちばん大きいところで {worst:.2f} ポイントです。</p>
    <div class="warn">
      <h4>この換算で分かること・分からないこと</h4>
      <ul>
        <li>換算は<strong>基準をそろえるためのもの</strong>で、公表値そのものではありません。資料に載せるときは、どちらの基準の値かを書いてください。</li>
        <li>差は<strong>近い時点ほど大きくなる傾向</strong>が実測で出ています（{pname}の重複期間で最大 {max(abs(res_lo), abs(res_hi)):.2f} ポイント）。</li>
        <li>正確さが要る場面では、<strong>換算せずに、必要な基準の統計表を直接引いてください。</strong>3つともいまも公表されています。</li>
      </ul>
    </div>
  </section>
''')

    # ---- 収録期間と係数の一覧 ---------------------------------------------
    crows = []
    for c in conv:
        s15 = db["2015"]["series"][c["c"]]
        cls = ' class="me"' if c["c"] == pcode else ""
        link = f'<a href="{c["s"]}.html">{c["n"]}</a>'
        f11 = f'{c["f11"]:.4f}' if c["f11"] else "—"
        crows.append(
            f'<tr{cls}><td>{link}</td>'
            f'<td class="n">{c["f15"]:.4f}</td>'
            f'<td class="n">{f11}</td>'
            f'<td class="n">{s15["res_min"]:+.2f} 〜 {s15["res_max"]:+.2f}</td>'
            f'<td class="n">{s15["months"][0]}〜</td></tr>')

    h.append(f'''  <section>
    <h2><span class="idx">Ref</span>工事種別ごとの改基準係数</h2>
    <p class="lede">旧基準の値をこの係数で割り、100を掛けると 2020年度＝100 にそろいます。係数は<strong>旧基準の系列の2020年度（2020年4月〜2021年3月）の平均</strong>で、公表値の平均だけで出しています。</p>
    <div class="tablebox"><table>
      <thead><tr><th>工事種別</th><th>2015年度基準の係数</th><th>2011年度基準の係数</th><th>割り戻しの差（2015）</th><th>2015年度基準の収録</th></tr></thead>
      <tbody>{"".join(crows)}</tbody>
    </table></div>
    <p class="colophon">出典：国土交通省「建設工事費デフレーター」各基準。取得日 {day}。係数は小数第4位まで。「割り戻しの差」は、その区分で重なっている期間について、実際の2020年度基準の値から換算値を引いたポイント数の最小と最大です。2011年度基準に収録の無い区分は「—」としています。</p>
  </section>

  <a class="cta" href="index.html">
    <span class="k">工事種別の一覧へ</span>
    <span class="n">建設工事費デフレーター</span>
    <span class="d">建築系{len(db["2015"]["series"])}区分を並べて比べられます</span>
    <span class="arrow">→</span>
  </a>
''')

    h.append(cite_block(canonical, day))

    # ---- 換算ツールの中身 -------------------------------------------------
    h.append(f'''<script>
(function(){{
  var C = {json.dumps(conv, ensure_ascii=False)};
  var sel = document.getElementById('cvCode');
  C.forEach(function(x, i){{
    var o = document.createElement('option');
    o.value = i; o.textContent = x.n; sel.appendChild(o);
  }});
  var val = document.getElementById('cvVal'),
      base = document.getElementById('cvBase'),
      out = document.getElementById('cvOut'),
      note = document.getElementById('cvNote');
  function fmt(v){{ return v === null ? '—' : v.toFixed(1); }}
  function draw(){{
    var x = C[sel.value|0], v = parseFloat(val.value), b = base.value;
    if (!isFinite(v) || v <= 0) {{ out.innerHTML = ''; note.textContent = '指数の値を入れてください。'; return; }}
    // いったん 2020年度＝100 に直してから、各基準へ戻す。
    var v20 = b === '20' ? v : (b === '15' ? v / x.f15 * 100 : (x.f11 ? v / x.f11 * 100 : null));
    if (v20 === null) {{
      out.innerHTML = '<tr><td colspan="3">この工事種別は2011年度基準の統計表に収録がありません。</td></tr>';
      note.textContent = '';
      return;
    }}
    var rows = [
      ['2011年度＝100', x.f11 ? v20 * x.f11 / 100 : null, x.f11, '11'],
      ['2015年度＝100', v20 * x.f15 / 100, x.f15, '15'],
      ['2020年度＝100', v20, null, '20']
    ];
    out.innerHTML = rows.map(function(r){{
      return '<tr' + (r[3] === b ? ' class="me"' : '') + '><td>' + r[0] +
             (r[3] === b ? '（入力した値）' : '') + '</td><td class="n">' + fmt(r[1]) +
             '</td><td class="n">' + (r[2] ? r[2].toFixed(4) : '—') + '</td></tr>';
    }}).join('');
    var w = Math.max(Math.abs(x.lo), Math.abs(x.hi));
    note.textContent = x.n + 'の改基準係数で割り戻した値です。基準が変わるときは重みづけも'
      + '入れ替わるため、換算値は実際に公表されている値と一致しません。この区分で重なっている'
      + '期間の実測では、差は ' + x.lo.toFixed(2) + ' 〜 ' + x.hi.toFixed(2)
      + ' ポイント（最大 ' + w.toFixed(2) + ' ポイント）でした。'
      + '正確さが要るときは、換算せずにその基準の統計表を直接引いてください。';
  }}
  [sel, val, base].forEach(function(e){{ e.addEventListener('input', draw); }});
  draw();
}})();
</script>
''')
    h.append(foot())

    (out / f"{SLUG}.html").write_text("".join(h), encoding="utf-8")
    print(f"  基準年 {m_both}: 2015年度基準 {v15[m_both]:.1f} / 2020年度基準 {v20[m_both]:.1f} "
          f"（差 {gap_both:+.1f}pt）　誤用時のずれ 1億円あたり {diff_man:,.0f}万円")
    return 1


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    n = build(basis)
    print(f"deflator/{SLUG}.html を {n} 枚生成しました")


if __name__ == "__main__":
    main()

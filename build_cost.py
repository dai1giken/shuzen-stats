# -*- coding: utf-8 -*-
"""戸数から工事金額の分布を見るページを生成する。

    py build_cost.py       # build.py から呼ばれる（basis.json が要る）

出力: cost/index.html
（他ページに置く入口バナーは `cost_banner.py`。循環 import を避けるため別モジュール）

--- なぜ別ページなのか ---------------------------------------------------
トップの `#calc` は**修繕積立金と工事費を並べる**ツールで、分譲マンションの
管理組合が資金計画を見るためのものになっている。こちらは積立金を扱わない。

理由は対象が違うから。**賃貸マンション・社宅・寮には修繕積立金が無い。**
積立金と一体にすると、分譲以外の建物を持っている人が使えない。
`#calc` はそのまま残し、こちらは工事金額の分布だけを見る。

--- 出す数字は「総額」ではない（この設計の中心）-------------------------
原典の集計定義で、**工事金額に共通仮設費は含まれない**。消費税も含まれない。
つまりこのページが出す額は、**実際の総額より必ず低い**。

低く出ること自体は避けられない。避けられるのは**それが誤読されること**なので、
「含まれていない」ではなく「**実際の総額はこれより上になります**」と
誤差の向きまで書く。この一文を消すと、低い数字だけが独り歩きする。

--- 築年数で金額を変えないこと -------------------------------------------
原典の四分位は **1回目／2回目／3回目以上** で分かれているだけで、築年別ではない。
築年数から回数を推定して金額に効かせると、**原典に無い相関を当社が作ったことになる。**
修繕周期は令和6年6月改定で幅（12〜15年）になり、記載例の実測でも5〜42年に散る。
入力に築年を置かないのはこのため。

--- 水準を当社が選ばない -------------------------------------------------
`/rough`（社内ツール）は「上位25%」を主役に固定しているが、あれは予算取りの
資料で下振れを避けるための社内判断で、**公開ページに持ち込む理由が無い**。
4段階を常に並べ、内訳をどの水準で見るかは読者が選ぶ。当社が水準を選んだ瞬間、
出典バンドの「当社の分析・見解は含みません」が嘘になる。

--- 元請から見た危うさ ---------------------------------------------------
戸あたり金額は「統計ではこの金額なのに御社の見積は高い」という形で、
**元請への値切り材料**に使われうる。対策は数字を出さないことではなく、
**数字が何でないかを同じ強さで書くこと**。`.warn` の赤枠をツールの直下に置き、
「個別の見積がこの範囲を外れていることは、それ自体では何も意味しません」を必ず残す。
**このページに問い合わせ導線を置かない。**統計サイトは公表値だけを置く場所で、
営業導線はサイト共通のフッターに任せる。
"""
from __future__ import annotations

import json
from pathlib import Path

from build_pref import SITE_URL, cite_block, foot, head
from cost_banner import UNIT_DEFAULT, UNIT_MAX, UNIT_MIN
import shuzen_survey as S

HERE = Path(__file__).resolve().parent

PAGE_URL = SITE_URL + "cost/"

# 総戸数のつまみの範囲は cost_banner が持つ。**2箇所に書かない。**
# バナーと本体で範囲がずれると、バナーから渡した ?units= が弾かれる。

# 地上階数。効くのは仮設工事の割合だけで、原典が 20階以上／未満でしか
# 分けていないため、選択肢もその粒度に合わせる（細かく見せると精度を偽ることになる）。
FLOOR_OPTIONS: list[tuple[str, str]] = [
    ("", "選ばない（合計の割合を使う）"),
    ("5", "3〜5階"),
    ("9", "6〜9階"),
    ("14", "10〜14階"),
    ("19", "15〜19階"),
    ("20", "20階以上（超高層）"),
]

# 表に出す「見方」。原典 p.15 の表がこの4つを持っている。
VIEWS: list[tuple[str, str]] = [
    ("q1", "下位25%"),
    ("median", "中央値"),
    ("q3", "上位25%"),
    ("mean", "平均"),
]

EXTRA_CSS = """
<style>
.tool{border:1px solid var(--rule);background:var(--surface);margin-top:18px}
.tool-in{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:18px;padding:20px 22px;
  border-bottom:1px solid var(--rule);background:var(--sunk)}
.tool-in label{display:block}
.tool-in .cap{display:block;font-family:var(--cond);font-weight:600;font-size:12.5px;color:var(--ink3);
  letter-spacing:.04em;margin-bottom:7px}
.tool-in select{width:100%;font-family:var(--cond);font-size:14px;padding:7px 9px;background:var(--surface);
  color:var(--ink);border:1px solid var(--rule);border-radius:2px}
.tool-in input[type=range]{width:100%;accent-color:var(--shu)}
.unitv{font-family:var(--mono);font-size:26px;font-variant-numeric:tabular-nums;color:var(--ink);line-height:1.1}
.unitv small{font-size:13px;color:var(--ink3);margin-left:3px}
.unitax{display:flex;justify-content:space-between;font-family:var(--mono);font-size:10.5px;color:var(--ink3);margin-top:2px}
.scope{padding:16px 22px;border-bottom:1px solid var(--rule)}
.scope-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(186px,1fr));gap:1px;background:var(--rule);
  border:1px solid var(--rule);margin-top:10px}
.scope-grid label{display:flex;align-items:baseline;gap:7px;background:var(--surface);padding:8px 11px;font-size:13px;cursor:pointer}
.scope-grid label.on{background:var(--sunk)}
.scope-grid .pc{margin-left:auto;font-family:var(--mono);font-size:11.5px;color:var(--ink3);font-variant-numeric:tabular-nums}
.scope-grid .fix{color:var(--ink3)}
.tool-out{padding:20px 22px}
.viewtab{width:100%;border-collapse:collapse;font-size:13.5px}
.viewtab th,.viewtab td{padding:9px 10px;border-bottom:1px solid var(--rule-soft);text-align:right;
  font-variant-numeric:tabular-nums}
.viewtab th{font-family:var(--cond);font-size:12px;color:var(--ink3);letter-spacing:.03em;border-bottom:1px solid var(--rule)}
.viewtab td.nm,.viewtab th.nm{text-align:left;font-family:var(--cond);font-weight:600;color:var(--ink)}
.viewtab td.mo{font-family:var(--mono);font-size:13px}
.viewtab tr.pick td{background:var(--sunk)}
.viewtab tr.pick td.nm{box-shadow:inset 3px 0 0 var(--shu)}
.viewtab .sub{color:var(--ink3);font-size:11.5px}
.brk{margin-top:8px}
.brk-row{display:grid;grid-template-columns:9.6em 4.2em 1fr 9em;gap:9px;align-items:center;padding:3px 0;font-size:12.5px}
.brk-row .lb{font-family:var(--cond)}
.brk-row .pc,.brk-row .am{font-family:var(--mono);font-size:11.5px;font-variant-numeric:tabular-nums;text-align:right;color:var(--ink2)}
.brk-track{height:9px;background:var(--sunk);border-radius:1px}
.brk-track i{display:block;height:100%;background:var(--rule-strong,#b9ae99);border-radius:1px}
.brk-row.ks .lb{color:var(--shu);font-weight:700}
.brk-row.ks .brk-track i{background:var(--shu)}
.compo{margin-top:20px;border:1px solid var(--rule)}
.compo div{display:flex;gap:12px;align-items:baseline;padding:11px 14px;border-bottom:1px solid var(--rule-soft);font-size:13px}
.compo div:last-child{border-bottom:0}
.compo .k{font-family:var(--cond);font-weight:600;color:var(--ink)}
.compo .v{margin-left:auto;font-family:var(--mono);font-variant-numeric:tabular-nums}
.compo .betsu{color:var(--shu);font-family:var(--cond);font-weight:700}
.formula{margin-top:16px;font-size:12px;line-height:1.95;color:var(--ink2)}
.formula li{margin-bottom:2px}
.gloss{margin-top:16px;border-top:1px solid var(--rule)}
.gloss dt{font-family:var(--cond);font-weight:700;font-size:13.5px;color:var(--ink);margin-top:12px}
.gloss dd{margin:3px 0 0;font-size:12.5px;line-height:1.85;color:var(--ink2)}
.prbtn{margin-top:16px;font-family:var(--cond);font-size:13px;padding:9px 18px;background:var(--surface);
  color:var(--ink);border:1px solid var(--ink);border-radius:2px;cursor:pointer}
.prbtn:hover{background:var(--sunk)}
@media (max-width:560px){.brk-row{grid-template-columns:8.4em 3.6em 1fr;}.brk-row .am{grid-column:2/4;text-align:left}}
@media print{
  .masthead,.sitenav,.cta,.sitelink,.prbtn,.finder,.cite{display:none!important}
  .tool,.compo,.warn,.viewtab,.gloss{break-inside:avoid}
  .tool-in,.viewtab tr.pick td,.brk-track{background:transparent!important}
  .brk-track{border:1px solid #999}
  .brk-track i{background:#666!important}
  body{font-size:11pt}
  a[href]:after{content:""}
  @page{margin:14mm}
}
</style>"""


def _data(basis: dict) -> dict:
    """ページの JS が読む値。**ここに無い数字を JS 側で作らない。**

    戸あたり金額と指数は basis.json（毎月更新）から、内訳は shuzen_survey から。
    どちらも手打ちしない。手打ちすると、指数が上がっても金額が古いまま動かない。
    """
    d = basis["deflator"]
    latest_value = d["series"][d["primary"]][-1]
    latest_month = d["months"][-1]
    return {
        "per_unit": basis["survey"]["per_unit"],
        "ratio": latest_value / 100.0,
        "index": latest_value,
        "month": latest_month,
        "base": d["base"],
        "views": [{"key": k, "label": lb} for k, lb in VIEWS],
        "breakdown": S.breakdown(),
        "kasetsu": S.KASETSU_SHARE,
        "tallFloors": S.KASETSU_TALL_FLOORS,
        "commonItems": S.COMMON_ITEMS,
        "unitMin": UNIT_MIN,
        "unitMax": UNIT_MAX,
        "unitDefault": UNIT_DEFAULT,
        "n": S.SOURCE_N,
        "breakdownN": S.BREAKDOWN_N,
    }


def build(basis: dict) -> int:
    bad = S.verify()
    if bad:
        raise SystemExit("shuzen_survey の突合が通らない:\n  " + "\n  ".join(bad))

    out = HERE / "cost"
    out.mkdir(exist_ok=True)
    day = basis["generated"].split()[0]
    data = _data(basis)
    rows = data["breakdown"]
    ks = S.KASETSU_SHARE

    title = "戸数から工事金額の分布を見る｜大規模修繕統計ビューア"
    desc = (f"国土交通省の実態調査（回答{S.SOURCE_N}件）の戸あたり工事金額に、"
            f"建設工事費デフレーターで{data['month']}の水準へ換算した分布を、戸数を掛けて表示します。"
            "共通仮設費と消費税は含みません。")

    h = [head(title, desc, PAGE_URL, crumb="工事金額の分布", extra_css=EXTRA_CSS)]

    h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて政府統計の公表値です。</strong>
    国土交通省「{S.SOURCE_NAME}」の戸あたり工事金額に、建設工事費デフレーターの比を掛けて
    {data["month"]}の水準へ換算し、入力された戸数を掛けています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表統計 ／ 工事金額の分布</span>
  <h1>戸数から、工事金額の分布を見る
    <span class="sub">国土交通省の実態調査（回答{S.SOURCE_N}件）にある<strong>戸あたり工事金額</strong>を、
    建設工事費デフレーターで{data["month"]}の水準に換算し、戸数を掛けたものです。
    <strong>この金額に共通仮設費と消費税は含まれていません</strong>（原典の集計定義）。
    そのぶん、実際の総額はここに出る額より上になります。</span>
  </h1>

  <div class="warn">
    <h4>この数字が何であって、何でないか</h4>
    <ul>
      <li><strong class="hard">共通仮設費が入っていません。</strong>現場事務所・仮設トイレ・資材置場・仮設の電気水道・安全対策・近隣対策・道路使用許可などの費用です。原典の集計対象外なので、<strong>実際の総額はここに出る額より上になります。</strong>消費税と設計コンサルタント業務の費用も別です。</li>
      <li>これは<strong>統計の分布に戸数を掛けただけ</strong>の数値で、その建物の工事費ではありません。劣化の程度、仕様、外壁の形状・面積、立地、工期は一切反映していません。</li>
      <li>幅は回答の<strong>真ん中50%</strong>です。外側にも50%の回答があります。<strong>個別の見積がこの範囲を外れていることは、それ自体では何も意味しません。</strong></li>
      <li>{S.SCOPE_NOTE}</li>
      <li>見積でも、必要額の算定でも、助言でもありません。実際の金額は<strong>現地調査</strong>で決まります。</li>
    </ul>
  </div>

  <section>
    <h2><span class="idx">Tool</span>条件を選ぶ</h2>
    <p class="lede">総戸数はつまみ、ほかは選ぶだけです。<strong>築年数は入力しません。</strong>原典の四分位は工事の回数で分かれているだけで、築年別のデータではないためです。築年数から金額を推定すると、原典に無い関係を当社が作ったことになります。</p>

    <div class="tool">
      <div class="tool-in">
        <label><span class="cap">総戸数</span>
          <span class="unitv"><b id="oUnits">{UNIT_DEFAULT}</b><small>戸</small></span>
          <input type="range" id="iUnits" min="{UNIT_MIN}" max="{UNIT_MAX}" step="1" value="{UNIT_DEFAULT}">
          <span class="unitax"><span>{UNIT_MIN}</span><span>{UNIT_MAX}</span></span>
        </label>
        <label><span class="cap">地上階数</span>
          <select id="iFloors">{"".join(f'<option value="{v}">{lb}</option>' for v, lb in FLOOR_OPTIONS)}</select>
          <span class="unitax"><span>仮設工事の割合だけが変わります</span></span>
        </label>
        <label><span class="cap">大規模修繕の実施回数</span>
          <select id="iRepeat"><option value="">わからない（3区分をまたぐ幅で出す）</option>{"".join(f'<option value="{r["label"]}">{r["label"]}（n={r["n"]}）</option>' for r in data["per_unit"])}</select>
          <span class="unitax"><span>選ぶと幅が1つの区分に絞られます</span></span>
        </label>
        <label><span class="cap">工事の範囲</span>
          <select id="iScope"><option value="full">大規模修繕（一式）</option><option value="partial">部分改修（工種を選ぶ）</option></select>
          <span class="unitax"><span>部分改修は下で工種を選びます</span></span>
        </label>
      </div>

      <div class="scope" id="scopeBox" hidden>
        <p class="lede" style="margin:0">直す工種を選んでください。<strong>仮設工事と諸経費は、範囲を絞ってもほぼ同じだけかかります</strong>ので、外せないようにしてあります。部分改修は一式より割高になりやすい点にもご留意ください（工事量が減るぶん単価が上がるため）。</p>
        <div class="scope-grid" id="scopeGrid"></div>
      </div>

      <div class="tool-out">
        <table class="viewtab">
          <thead><tr>
            <th class="nm">見方</th><th>戸あたり<span class="sub">（万円/戸）</span></th>
            <th>金額<span class="sub">（税抜）</span></th><th>金額<span class="sub">（税込10%）</span></th>
          </tr></thead>
          <tbody id="oTable"></tbody>
        </table>
        <p class="qnote" id="oNote">—</p>

        <div class="compo" id="oCompo"></div>

        <h3 style="margin:26px 0 0;font-family:var(--cond);font-size:15px">工事金額の内訳（調査全体の平均的な姿）</h3>
        <p class="qnote" id="oBrkNote">—</p>
        <label style="display:block;margin-top:10px">
          <span class="cap" style="font-family:var(--cond);font-size:12.5px;color:var(--ink3)">どの見方の金額で内訳を見るか</span>
          <select id="iView" style="margin-top:6px;font-family:var(--cond);font-size:14px;padding:7px 9px;background:var(--surface);color:var(--ink);border:1px solid var(--rule);border-radius:2px">{"".join(f'<option value="{k}"{" selected" if k == "median" else ""}>{lb}</option>' for k, lb in VIEWS)}</select>
        </label>
        <div class="brk" id="oBrk"></div>
        <p class="qnote">出典 {S.SOURCE_PUBLISHER}「{S.SOURCE_NAME}」{S.PAGE_BREAKDOWN}（総工事金額に対する割合。建築系工事の内訳は同ページの建築系合計に対する割合を按分）。{S.PAGE_SHARE} の「総工事金額に占める割合」と一致することを確認しています。<strong>共通仮設費と消費税は、この100%のどこにも含まれていません。</strong>内訳の母数は n={S.BREAKDOWN_N} で、戸あたり金額（n={S.SOURCE_N}）とは異なります（建築系工事を実施していないサンプルを除外した集計のため）。</p>

        <h3 style="margin:26px 0 0;font-family:var(--cond);font-size:15px">計算の内訳</h3>
        <ol class="formula" id="oFormula"></ol>

        <button type="button" class="prbtn" id="prBtn">印刷 / PDFで保存</button>
      </div>
    </div>
  </section>

  <section>
    <h2><span class="idx">Note</span>「仮設」「共通仮設」「足場」の違い</h2>
    <p class="lede">この3つは混同されやすく、どれを含む金額なのかで話が食い違います。原典の定義に沿って並べます。</p>
    <dl class="gloss">
      {"".join(f"<dt>{t}</dt><dd>{b}</dd>" for t, b in S.KASETSU_GLOSSARY)}
    </dl>
    <div class="warn">
      <h4>仮設工事の割合を、足場の金額として使わないこと</h4>
      <ul>
        <li><strong>原典に「足場」という語は一度も出てきません。</strong>仮設工事の内訳も示されていないため、{ks["all"]["percent"]}% を差し引いた額は「足場を除いた額」ではなく「<strong>仮設工事を除いた額</strong>」です。</li>
        <li>仮設工事の割合は階数で変わります。原典（{S.PAGE_SHARE}）では {ks["tall"]["label"]} が {ks["tall"]["percent"]}%（n={ks["tall"]["n"]}）、{ks["other"]["label"]} が {ks["other"]["percent"]}%（n={ks["other"]["n"]}）、合計で {ks["all"]["percent"]}%（n={ks["all"]["n"]}）です。</li>
        <li>足場を別に見積もる場合、上の金額から仮設工事に相当する額を<strong>差し引いてから</strong>足してください。そのまま足すと二重になります。</li>
      </ul>
    </div>
  </section>

  <section>
    <h2><span class="idx">Method</span>算式と出典</h2>
    <p class="lede">独自の加重や補正は置いていません。公表統計をこの式で換算し、戸数を掛けただけの数字です。下の値と取得日があれば、誰でも同じ結果を再現できます。</p>
    <ul class="formula">
      <li><b>戸あたり工事金額</b>　{S.SOURCE_PUBLISHER}「{S.SOURCE_NAME}」（{S.SOURCE_PUBLISHED} 公表、n={S.SOURCE_N}）{S.PAGE_PER_UNIT}　<a href="{S.SOURCE_URL}" target="_blank" rel="noopener">原典PDF</a></li>
      <li><b>工事金額の定義</b>　{S.PAGE_DEFINITION}「上記工事の直接工事費（共通仮設費は含まない。）及び諸経費①、諸経費②」「消費税相当額は含まない」</li>
      <li><b>内訳・仮設工事の割合</b>　{S.PAGE_BREAKDOWN} ／ {S.PAGE_SHARE}</li>
      <li><b>物価換算</b>　建設工事費デフレーター（{data["base"]}）建設総合_建築補修（改装・改修）。{data["month"]} の指数 {data["index"]} ÷ 100 ＝ {data["ratio"]:.3f}　<a href="https://www.e-stat.go.jp/dbview?sid=0004055083" target="_blank" rel="noopener">e-Stat statsDataId=0004055083</a>（取得 {day}）</li>
      <li><b>価格時点</b>　{S.PRICE_ANCHOR_NOTE}</li>
      <li><b>丸め</b>　10万円未満を四捨五入。税込は丸めた額に1.1を掛けています。</li>
    </ul>
  </section>
''')

    h.append(cite_block(PAGE_URL, day))

    h.append(f'''
  <a class="cta" href="{SITE_URL}cycle/">
    <span class="k">公表資料 ／ 修繕周期</span>
    <span class="n">マンションの修繕周期 部位別一覧</span>
    <span class="d">長期修繕計画作成ガイドライン（令和6年6月改定）の記載例81項目。周期は幅で示されています</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{SITE_URL}deflator/kijun-nendo.html">
    <span class="k">Tool ／ 工事費の指数</span>
    <span class="n">建設工事費デフレーターの基準年</span>
    <span class="d">古い見積や長期修繕計画の金額を今の水準に直すときは、指数の基準年をそろえる必要があります</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{SITE_URL}">
    <span class="k">大規模修繕統計ビューア</span>
    <span class="n">トップへ</span>
    <span class="d">工事費指数・戸あたり工事金額・修繕周期・修繕積立金の公表値</span>
    <span class="arrow">→</span>
  </a>

  <script id="cost-data" type="application/json">{json.dumps(data, ensure_ascii=False)}</script>
  <script>{JS}</script>
''')
    h.append(foot())

    html = "".join(h)
    if "{BASE}" in html or "{{" in html:
        raise SystemExit("cost/index.html に未展開のプレースホルダが残っています")
    (out / "index.html").write_text(html, encoding="utf-8")

    print(f"  cost/      1 ページ（工事金額の分布・戸数から）　"
          f"内訳 {len(rows)} 項目　換算 {data['index']} ÷ 100 ＝ {data['ratio']:.3f}"
          f"（{data['month']}）　突合 OK")
    return 1


JS = r"""
(function(){
  var D = JSON.parse(document.getElementById('cost-data').textContent);
  var $ = function(id){ return document.getElementById(id); };
  var nf = new Intl.NumberFormat('ja-JP');
  var nf1 = new Intl.NumberFormat('ja-JP', {minimumFractionDigits:1, maximumFractionDigits:1});
  var ROUND = 100000, TAX = 0.10;

  var iUnits=$('iUnits'), iFloors=$('iFloors'), iRepeat=$('iRepeat'),
      iScope=$('iScope'), iView=$('iView');

  /* 範囲を絞ってもかかる項目は外せない。外すと金額が現実離れして低く出る。 */
  var picked = {};
  D.breakdown.forEach(function(r){ picked[r.label] = r.common; });

  function money(n){ return Math.round(n/ROUND)*ROUND; }
  function man(n){ return nf.format(Math.round(n/10000)) + '万円'; }
  function manRange(lo, hi){ return lo === hi ? man(lo) : man(lo) + ' 〜 ' + man(hi); }

  function kasetsuShare(floors){
    if(!floors) return D.kasetsu.all;
    return floors >= D.tallFloors ? D.kasetsu.tall : D.kasetsu.other;
  }

  function scopeRatio(){
    if(iScope.value !== 'partial') return null;
    var sum = 0;
    D.breakdown.forEach(function(r){ if(picked[r.label]) sum += r.percent; });
    return sum > 0 ? Math.round(sum*10)/10 : null;
  }

  function calc(){
    var units = +iUnits.value || D.unitMin;
    var rows = iRepeat.value
      ? D.per_unit.filter(function(r){ return r.label === iRepeat.value; })
      : D.per_unit;
    var ratio = D.ratio;
    var sr = scopeRatio();
    var factor = (iScope.value === 'partial' && sr) ? sr/100 : 1;

    /* 幅は「同じ見方の中で、回数の区分をまたいだ最小〜最大」。
       q1〜q3 をまたぐ幅ではない。回数を選べば lo === hi になって幅が潰れる。 */
    var views = D.views.map(function(v){
      var vals = rows.map(function(r){ return r[v.key] * ratio; });
      var lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
      return {
        key: v.key, label: v.label,
        perUnit: {lo: lo, hi: hi},
        full:   {lo: lo*10000*units,        hi: hi*10000*units},
        amount: {lo: lo*10000*units*factor, hi: hi*10000*units*factor}
      };
    });
    return {units: units, rows: rows, views: views, ratio: ratio,
            factor: factor, scopeRatio: sr,
            kasetsu: kasetsuShare(+iFloors.value || 0)};
  }

  function drawScope(){
    var box = $('scopeBox'), grid = $('scopeGrid');
    box.hidden = iScope.value !== 'partial';
    if(box.hidden) return;
    if(grid.childElementCount) return;
    D.breakdown.forEach(function(r){
      var lb = document.createElement('label');
      var cb = document.createElement('input');
      cb.type = 'checkbox'; cb.checked = !!picked[r.label]; cb.disabled = !!r.common;
      cb.addEventListener('change', function(){ picked[r.label] = cb.checked; render(); });
      var nm = document.createElement('span');
      nm.textContent = r.label;
      if(r.common){ nm.className = 'fix'; nm.title = '範囲を絞ってもかかるため外せません'; }
      var pc = document.createElement('span');
      pc.className = 'pc'; pc.textContent = r.percent.toFixed(2) + '%';
      lb.appendChild(cb); lb.appendChild(nm); lb.appendChild(pc);
      if(r.common) lb.classList.add('on');
      grid.appendChild(lb);
    });
  }

  function render(){
    drawScope();
    var c = calc();
    $('oUnits').textContent = nf.format(c.units);

    /* --- 4段階の表 --- */
    var tb = $('oTable');
    tb.replaceChildren();
    c.views.forEach(function(v){
      var lo = money(v.amount.lo), hi = money(v.amount.hi);
      var tr = document.createElement('tr');
      if(v.key === iView.value) tr.className = 'pick';
      function td(cls, text){
        var e = document.createElement('td'); e.className = cls; e.textContent = text;
        tr.appendChild(e); return e;
      }
      td('nm', v.label);
      td('mo', v.perUnit.lo === v.perUnit.hi
        ? nf1.format(v.perUnit.lo)
        : nf1.format(v.perUnit.lo) + ' 〜 ' + nf1.format(v.perUnit.hi));
      td('mo', manRange(lo, hi));
      td('mo', manRange(lo*(1+TAX), hi*(1+TAX)));
      tb.appendChild(tr);
    });

    var rn = c.rows.map(function(r){ return r.label + '（n=' + r.n + '）'; }).join('／');
    $('oNote').textContent = iRepeat.value
      ? '工事回数は「' + iRepeat.value + '」で計算しています。使った区分は ' + rn + '。'
      : '工事回数を選んでいないため、統計の3区分（' + rn
        + '）をまたぐ幅で示しています。どの見方を採るかで金額が変わるので、幅のまま載せています。';

    /* --- 構成（共通仮設費は別途） --- */
    var pick = c.views.filter(function(v){ return v.key === iView.value; })[0] || c.views[1];
    var plo = money(pick.amount.lo), phi = money(pick.amount.hi);
    var co = $('oCompo');
    co.replaceChildren();
    function row(k, v, cls){
      var d = document.createElement('div');
      var a = document.createElement('span'); a.className = 'k'; a.textContent = k;
      var b = document.createElement('span'); b.className = 'v ' + (cls||''); b.textContent = v;
      d.appendChild(a); d.appendChild(b); co.appendChild(d);
    }
    row('① 工事費（仮設工事を含む・税抜）', manRange(plo, phi));
    row('　　税込10%', manRange(plo*(1+TAX), phi*(1+TAX)));
    row('② 共通仮設費', '別途', 'betsu');
    row('③ 設計コンサルタント業務の費用（調査・診断／設計／工事監理 等）', '別途', 'betsu');
    row('①＋②＋③', '②③の確定後に算出', 'betsu');

    /* --- 内訳 --- */
    var brk = $('oBrk');
    brk.replaceChildren();
    var maxp = Math.max.apply(null, D.breakdown.map(function(r){ return r.percent; }));
    D.breakdown.forEach(function(r){
      var flo = money(pick.full.lo * r.percent/100), fhi = money(pick.full.hi * r.percent/100);
      var d = document.createElement('div');
      d.className = 'brk-row' + (r.kasetsu ? ' ks' : '');
      var lb = document.createElement('span'); lb.className='lb'; lb.textContent = r.label;
      var pc = document.createElement('span'); pc.className='pc'; pc.textContent = r.percent.toFixed(2)+'%';
      var tk = document.createElement('span'); tk.className='brk-track';
      var i = document.createElement('i'); i.style.width = (r.percent/maxp*100).toFixed(1)+'%';
      tk.appendChild(i);
      var am = document.createElement('span'); am.className='am'; am.textContent = manRange(flo, fhi);
      d.appendChild(lb); d.appendChild(pc); d.appendChild(tk); d.appendChild(am);
      brk.appendChild(d);
    });

    /* 内訳は「一式で行った場合の金額」に掛ける。範囲を絞った額に掛けると、
       絞った割合が二重にかかる。 */
    $('oBrkNote').textContent =
      '下の割合を、一式で行った場合の金額（' + manRange(money(pick.full.lo), money(pick.full.hi))
      + '・' + pick.label + '）に掛けています。本物件の実際の割合ではなく、調査全体の平均的な姿です。'
      + '上の構成表では、仮設工事に本物件の階数に合わせた ' + c.kasetsu.percent.toFixed(1) + '%（'
      + c.kasetsu.label + '・n=' + c.kasetsu.n + '）が対応します。';

    /* --- 算式 --- */
    var fm = $('oFormula');
    fm.replaceChildren();
    [
      '使った統計　' + (iRepeat.value ? rn + ' の区分' : '工事回数の3区分すべて（' + rn + '）をまたぐ幅'),
      '工事費指数による換算倍率　' + D.index + ' ÷ 100 ＝ ' + D.ratio.toFixed(3)
        + '（建設総合_建築補修（改装・改修）・' + D.base + '・' + D.month + '）',
      '換算後の戸あたり金額 × 戸数 ' + nf.format(c.units) + ' 戸'
        + (c.factor !== 1 ? '　× 対象割合 ' + c.scopeRatio + '%' : '') + '　＝ 上の表の金額',
      'この工事金額に占める仮設工事の割合は ' + c.kasetsu.percent.toFixed(1) + '%（'
        + c.kasetsu.label + '・n=' + c.kasetsu.n + '）。',
      '金額は10万円未満を四捨五入しています。統計は税抜で、消費税相当額と共通仮設費を含みません。'
    ].forEach(function(t){
      var li = document.createElement('li'); li.textContent = t; fm.appendChild(li);
    });
  }

  [iUnits, iFloors, iRepeat, iScope, iView].forEach(function(e){
    e.addEventListener('input', render);
    e.addEventListener('change', render);
  });
  $('prBtn').addEventListener('click', function(){ window.print(); });

  /* バナーから引き継いだ戸数。**照合できない値は無視する。** */
  var m = /[?&]units=(\d+)/.exec(location.search);
  if(m){
    var n = +m[1];
    if(n >= D.unitMin && n <= D.unitMax) iUnits.value = n;
  }
  render();
})();
"""


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    build(basis)


if __name__ == "__main__":
    main()

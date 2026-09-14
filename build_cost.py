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

# 表に出す「見方」。原典の表がこの4つを持っている。
#
# **平均だけは分位ではない。**4行を並べると順位のはしごに見えるが、平均は
# 少数の大きな案件に引っ張られるので、右に伸びた分布では上位25%を上回る。
# 原典では1回目がこれにあたり、平均 151.6 が上位25%値 134.0 を超えている
# （2回目 112.4 < 129.8、3回目以上 106.1 < 125.7 は超えていない）。
# **原典どおりの値なので直さない。**代わりに、順位として読まれないよう
# 表で行を分け、理由を注記する。
VIEWS: list[tuple[str, str, bool]] = [
    ("q1", "下位25%", False),
    ("median", "中央値", False),
    ("q3", "上位25%", False),
    ("mean", "平均", True),      # True ＝ 分位ではない
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
.viewtab .sub{color:var(--ink3);font-size:11.5px;display:block;font-weight:400}
.viewtab td.c{padding:0}
/* 平均は分位ではないので、左の3列（四分位）と罫線で切り離す。 */
.viewtab th.avgc,.viewtab td.avgc{border-left:1px solid var(--rule)}
.viewtab .cell{display:block;width:100%;background:none;border:0;padding:8px 10px;
  font:inherit;color:inherit;text-align:right;cursor:pointer}
.viewtab .cell:hover{background:var(--sunk)}
.viewtab .cell .a{display:block;font-family:var(--mono);font-size:13.5px;color:var(--ink)}
.viewtab .cell .p{display:block;font-family:var(--mono);font-size:10.5px;color:var(--ink3);margin-top:2px}
.viewtab .cell.on{background:var(--sunk);box-shadow:inset 0 0 0 2px var(--ai)}
.viewtab .cell.on .a{font-weight:700}
/* 平均の列だけ見出しを朱にして、下の注意書きと対応させる。
   朱はこのサイトの警告色で、ここは「順位として読むな」という注意そのもの。 */
.viewtab th.avgc .sub{color:var(--shu)}
.avgnote{margin-top:14px;padding:12px 15px;border-left:4px solid var(--shu);background:var(--sunk);
  font-size:12.5px;line-height:1.9;color:var(--ink2)}
.avgnote b{color:var(--shu);font-weight:700}
.viewtab td.nm .n{display:block;font-family:var(--mono);font-size:10.5px;color:var(--ink3);font-weight:400}
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
  .tool,.compo,.warn,.avgnote,.viewtab,.gloss{break-inside:avoid}
  .tool-in,.brk-track{background:transparent!important}
  .avgnote{background:transparent!important}
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
        "views": [{"key": k, "label": lb, "avg": av} for k, lb, av in VIEWS],
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
    bad = S.verify() + S.verify_per_unit(basis["survey"]["per_unit"])
    if bad:
        raise SystemExit("原典との突合が通らない:\n  " + "\n  ".join(bad))

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
        <p class="lede" style="margin:0 0 10px">原典（{S.PAGE_PER_UNIT}）は<strong>工事回数ごとに四分位を出しています</strong>ので、同じ形で3行とも並べます。回数で金額の水準が違うことも、そのまま見えます。<strong>金額を押すと、その金額で下の内訳を出します。</strong></p>
        <table class="viewtab">
          <thead><tr>
            <th class="nm">工事回数</th>
            <th>下位25%</th><th>中央値</th><th>上位25%</th>
            <th class="avgc">平均<span class="sub">分位ではありません</span></th>
          </tr></thead>
          <tbody id="oTable"></tbody>
        </table>
        <p class="qnote" id="oNote">—</p>
        <p class="qnote">上段が税抜の金額、下段が戸あたり（万円/戸）です。税込は10%を足した額で、選んだ金額について下の構成表に出しています。10万円未満は四捨五入しています。</p>
        <p class="avgnote"><b>「平均」は分位ではありません。順位として読まないでください。</b>少数の大きな案件に引っ張られるため、分布が右に伸びていると上位25%を上回ることがあります。原典では<b>1回目がこれにあたり、平均 151.6 万円/戸が上位25%値 134.0 万円/戸を上回っています</b>（2回目 112.4 &lt; 129.8、3回目以上 106.1 &lt; 125.7 は上回っていません）。左の3列（四分位）と罫線で切り離してあるのはこのためです。</p>

        <div class="compo" id="oCompo"></div>

        <h3 style="margin:26px 0 0;font-family:var(--cond);font-size:15px">工事金額の内訳（調査全体の平均的な姿）</h3>
        <p class="qnote" id="oBrkNote">—</p>
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

  var iUnits=$('iUnits'), iFloors=$('iFloors'), iScope=$('iScope');

  /* 選んでいるマス（工事回数 × 見方）。表のどの金額を押しても変わる。
     既定は3区分の真ん中「2回目」の中央値。内訳の基準を決めるのに既定は要るが、
     **表は常に3行とも出す**ので、当社がひとつの水準を選んで見せる形にはならない。 */
  var sel = {repeat: (D.per_unit[1] || D.per_unit[0]).label, view: 'median'};

  /* 範囲を絞ってもかかる項目は外せない。外すと金額が現実離れして低く出る。 */
  var picked = {};
  D.breakdown.forEach(function(r){ picked[r.label] = r.common; });

  function money(n){ return Math.round(n/ROUND)*ROUND; }
  function man(n){ return nf.format(Math.round(n/10000)) + '万円'; }

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
    var sr = scopeRatio();
    return {
      units: +iUnits.value || D.unitMin,
      factor: (iScope.value === 'partial' && sr) ? sr/100 : 1,
      scopeRatio: sr,
      kasetsu: kasetsuShare(+iFloors.value || 0)
    };
  }

  /* 1つのマスの金額。**幅にしない。**
     原典は工事回数ごとに四分位を出しているので、回数をまたいで最小〜最大に
     潰すと、原典に無い「幅」を当社が作ることになる。しかも1回目は平均が
     上位25%を上回るため、潰した幅どうしが上下で食い違って読めなくなる。
     原典と同じ3行4列のまま出すこと。 */
  function cell(row, key, c){
    var pu = row[key] * D.ratio;
    return {
      /* 画面に出す戸あたりは**対象割合を掛けたあと**の値。掛ける前の
         公表値を出すと、同じマスの「金額 ÷ 戸数」と一致しなくなる。
         公表値そのものは算式の行に出しているので、そちらで辿れる。 */
      perUnit: pu * c.factor,
      full:    pu * 10000 * c.units,            /* 一式の額。内訳の按分に使う */
      amount:  pu * 10000 * c.units * c.factor  /* 範囲を絞った額 */
    };
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

    /* --- 原典と同じ「工事回数 × 四分位」の表 --- */
    var tb = $('oTable');
    tb.replaceChildren();
    D.per_unit.forEach(function(row){
      var tr = document.createElement('tr');
      var nm = document.createElement('td');
      nm.className = 'nm';
      nm.textContent = row.label;
      var nn = document.createElement('span');
      nn.className = 'n'; nn.textContent = 'n=' + row.n;
      nm.appendChild(nn);
      tr.appendChild(nm);
      D.views.forEach(function(v){
        var td = document.createElement('td');
        td.className = 'c' + (v.avg ? ' avgc' : '');
        var x = cell(row, v.key, c);
        var amt = money(x.amount);
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'cell'
          + (row.label === sel.repeat && v.key === sel.view ? ' on' : '');
        b.setAttribute('aria-label', row.label + ' ' + v.label + ' ' + man(amt));
        var a = document.createElement('span');
        a.className = 'a'; a.textContent = man(amt);
        var p = document.createElement('span');
        p.className = 'p'; p.textContent = nf1.format(x.perUnit);
        b.appendChild(a); b.appendChild(p);
        b.addEventListener('click', function(){
          sel = {repeat: row.label, view: v.key};
          render();
        });
        td.appendChild(b);
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });

    var selRow = D.per_unit.filter(function(r){ return r.label === sel.repeat; })[0]
      || D.per_unit[0];
    var selView = D.views.filter(function(v){ return v.key === sel.view; })[0] || D.views[1];
    $('oNote').textContent = '選んでいるのは「' + selRow.label + '（n=' + selRow.n + '）の'
      + selView.label + '」です。下の構成表と内訳は、この金額で出しています。'
      + '表のどの金額を押しても切り替わります。';

    /* --- 構成（共通仮設費は別途） --- */
    var pick = cell(selRow, sel.view, c);
    var pv = money(pick.amount);
    var co = $('oCompo');
    co.replaceChildren();
    function row(k, v, cls){
      var d = document.createElement('div');
      var a = document.createElement('span'); a.className = 'k'; a.textContent = k;
      var b = document.createElement('span'); b.className = 'v ' + (cls||''); b.textContent = v;
      d.appendChild(a); d.appendChild(b); co.appendChild(d);
    }
    row('① 工事費（仮設工事を含む・税抜）', man(pv));
    row('　　税込10%', man(pv*(1+TAX)));
    row('② 共通仮設費', '別途', 'betsu');
    row('③ 設計コンサルタント業務の費用（調査・診断／設計／工事監理 等）', '別途', 'betsu');
    row('①＋②＋③', '②③の確定後に算出', 'betsu');

    /* --- 内訳 --- */
    var brk = $('oBrk');
    brk.replaceChildren();
    var maxp = Math.max.apply(null, D.breakdown.map(function(r){ return r.percent; }));
    D.breakdown.forEach(function(r){
      var fv = money(pick.full * r.percent/100);
      var d = document.createElement('div');
      d.className = 'brk-row' + (r.kasetsu ? ' ks' : '');
      var lb = document.createElement('span'); lb.className='lb'; lb.textContent = r.label;
      var pc = document.createElement('span'); pc.className='pc'; pc.textContent = r.percent.toFixed(2)+'%';
      var tk = document.createElement('span'); tk.className='brk-track';
      var i = document.createElement('i'); i.style.width = (r.percent/maxp*100).toFixed(1)+'%';
      tk.appendChild(i);
      var am = document.createElement('span'); am.className='am'; am.textContent = man(fv);
      d.appendChild(lb); d.appendChild(pc); d.appendChild(tk); d.appendChild(am);
      brk.appendChild(d);
    });

    /* 内訳は「一式で行った場合の金額」に掛ける。範囲を絞った額に掛けると、
       絞った割合が二重にかかる。 */
    $('oBrkNote').textContent =
      '下の割合を、一式で行った場合の金額（' + man(money(pick.full))
      + '・' + selRow.label + 'の' + selView.label + '）に掛けています。'
      + '本物件の実際の割合ではなく、調査全体の平均的な姿です。'
      + '上の構成表では、仮設工事に本物件の階数に合わせた ' + c.kasetsu.percent.toFixed(1) + '%（'
      + c.kasetsu.label + '・n=' + c.kasetsu.n + '）が対応します。';

    /* --- 算式 --- */
    var fm = $('oFormula');
    fm.replaceChildren();
    [
      '使った統計　' + selRow.label + '（n=' + selRow.n + '）の' + selView.label
        + '　' + nf1.format(selRow[sel.view]) + ' 万円/戸（調査時点）',
      '工事費指数による換算倍率　' + D.index + ' ÷ 100 ＝ ' + D.ratio.toFixed(3)
        + '（建設総合_建築補修（改装・改修）・' + D.base + '・' + D.month + '）',
      '換算後 ' + nf1.format(selRow[sel.view] * D.ratio) + ' 万円/戸 × 戸数 '
        + nf.format(c.units) + ' 戸'
        + (c.factor !== 1 ? '　× 対象割合 ' + c.scopeRatio + '%' : '') + '　＝ ' + man(pv),
      'この工事金額に占める仮設工事の割合は ' + c.kasetsu.percent.toFixed(1) + '%（'
        + c.kasetsu.label + '・n=' + c.kasetsu.n + '）。',
      '金額は10万円未満を四捨五入しています。統計は税抜で、消費税相当額と共通仮設費を含みません。'
    ].forEach(function(t){
      var li = document.createElement('li'); li.textContent = t; fm.appendChild(li);
    });
  }

  [iUnits, iFloors, iScope].forEach(function(e){
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

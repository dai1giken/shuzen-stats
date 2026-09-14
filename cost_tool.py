# -*- coding: utf-8 -*-
"""戸数から工事金額を出すツール本体。**/cost/ と各地域ページで同じ物を使う。**

--- なぜ build_cost.py から切り出したのか -------------------------------
ツールは /cost/ 1ページだけの物だったが、市区町村・都道府県ページにも
そのまま置くことにしたため（2026-09-15 本人判断）、両方から読める形にした。
**build_cost.py に本体を戻さないこと。**戻すと地域ページ側が
build_cost → build_pref → build_city → build_cost の循環 import になる。
このモジュールが import してよいのは `shuzen_survey` と `cost_banner` だけ。

--- id は1ページに1組しかない -------------------------------------------
`iUnits` `oTable` `oLinked` などの id を JS が直接引いている。
**1ページにツールを2つ置いてはいけない。**2つめの入力が黙って効かなくなる。
地域ページでは入口バナー（cost_banner）の代わりに置く。両方は置かない。

--- 数字はすべて basis.json と shuzen_survey から ------------------------
`data()` に無い数字を JS 側で作らないこと。手打ちすると、指数が上がっても
金額が古いまま動かない。
"""
from __future__ import annotations

import json

from cost_banner import UNIT_DEFAULT, UNIT_MAX, UNIT_MIN
import shuzen_survey as S


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


CSS = """
.tool{border:1px solid var(--rule);background:var(--surface);margin-top:18px}
.tool-in{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:18px;padding:20px 22px;
  border-bottom:1px solid var(--rule);background:var(--sunk)}
.tool-in label{display:block}
.tool-in .cap{display:block;font-family:var(--cond);font-weight:600;font-size:12.5px;color:var(--ink3);
  letter-spacing:.04em;margin-bottom:7px}
.tool-in select{width:100%;font-family:var(--cond);font-size:14px;padding:7px 9px;background:var(--surface);
  color:var(--ink);border:1px solid var(--rule);border-radius:2px}
/* つまみは**ブラウザ既定のままだと細すぎて、動かせる物だと気づかれない。**
   レールと玉を自前で描いて大きくする。accent-color は ::-webkit-slider-thumb を
   書いた時点で効かなくなるので、色は両方に直接置くこと。 */
/* **色の役割をこのページで揃えてある。藍＝操作できるもの／朱＝警告。**
   つまみは元は朱だったが、朱は「平均は分位ではない」「共通仮設費は別途」と
   同じ色で、操作の合図と注意が同じ色だと両方が弱くなる。押せる金額・使い方・
   連動枠・つまみを藍に統一した。**朱に戻さないこと。** */
.tool-in input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:26px;
  background:transparent;cursor:pointer;display:block}
.tool-in input[type=range]::-webkit-slider-runnable-track{height:8px;border-radius:999px;
  background:var(--sunk);border:1px solid var(--ai)}
.tool-in input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:24px;height:24px;
  margin-top:-9px;border-radius:50%;background:var(--ai);border:3px solid var(--sunk);
  box-shadow:0 0 0 1px var(--ai)}
.tool-in input[type=range]::-moz-range-track{height:8px;border-radius:999px;
  background:var(--sunk);border:1px solid var(--ai)}
.tool-in input[type=range]::-moz-range-thumb{width:20px;height:20px;border-radius:50%;
  background:var(--ai);border:3px solid var(--sunk);box-shadow:0 0 0 1px var(--ai)}
.tool-in input[type=range]:focus-visible::-webkit-slider-thumb{box-shadow:0 0 0 4px var(--ai)}
.tool-in input[type=range]:focus-visible::-moz-range-thumb{box-shadow:0 0 0 4px var(--ai)}
.tool-in .drag{display:block;margin-top:6px;font-family:var(--cond);font-weight:600;font-size:11.5px;
  letter-spacing:.03em;color:var(--ai);line-height:1.6}
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
/* **表だけを横スクロールの箱に入れること。**入れないと、狭い画面で
   ページ全体が横スクロールする（332px 幅で表が 420px 必要・2026-09-15 実測）。
   共有CSSの .tablebox と同じ作り。 */
.tabwrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
.viewtab{width:100%;min-width:376px;border-collapse:collapse;font-size:13.5px}
.viewtab th,.viewtab td{padding:9px 10px;border-bottom:1px solid var(--rule-soft);text-align:right;
  font-variant-numeric:tabular-nums}
.viewtab th{font-family:var(--cond);font-size:12px;color:var(--ink3);letter-spacing:.03em;border-bottom:1px solid var(--rule)}
.viewtab td.nm,.viewtab th.nm{text-align:left;font-family:var(--cond);font-weight:600;color:var(--ink)}
.viewtab td.mo{font-family:var(--mono);font-size:13px}
.viewtab .sub{color:var(--ink3);font-size:11.5px;display:block;font-weight:400}
.viewtab td.c{padding:0}
/* 平均は分位ではないので、左の3列（四分位）と罫線で切り離す。 */
.viewtab th.avgc,.viewtab td.avgc{border-left:1px solid var(--rule)}
/* **9つの金額が押せることは、知らないと分からない。**「押すと下が変わる」と
   文章で書いてあっても読まれないので、形で示す：
     ・未選択＝金額に藍の点線下線（リンクの作法）＋ホバーで藍の枠
     ・選択中＝藍の枠＋「▼ 下に表示中」
   点線を消すと、また「ただの表」に戻る。 */
.viewtab .cell{display:block;width:100%;background:none;border:0;padding:8px 10px;
  font:inherit;color:inherit;text-align:right;cursor:pointer;transition:background .12s,box-shadow .12s}
.viewtab .cell:hover{background:var(--sunk);box-shadow:inset 0 0 0 1px var(--ai)}
.viewtab .cell:focus-visible{outline:2px solid var(--ai);outline-offset:-2px}
.viewtab .cell .a{display:block;font-family:var(--mono);font-size:13.5px;color:var(--ink);
  text-decoration:underline dotted var(--ai);text-decoration-thickness:1px;text-underline-offset:4px}
.viewtab .cell .p{display:block;font-family:var(--mono);font-size:10.5px;color:var(--ink3);margin-top:2px}
.viewtab .cell .tag{display:none;font-family:var(--cond);font-weight:700;font-size:10px;
  letter-spacing:.06em;color:var(--ai);margin-top:4px}
.viewtab .cell.on{background:var(--sunk);box-shadow:inset 0 0 0 2px var(--ai)}
.viewtab .cell.on .a{font-weight:700;text-decoration:none}
.viewtab .cell.on .tag{display:block}
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
/* 使い方。表の直前に置く。lede の文章の中に混ぜると読まれない。 */
.howto{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;margin:0 0 12px;
  padding:9px 13px;border:1px solid var(--ai);background:var(--sunk);font-size:12.5px;color:var(--ink2)}
.howto b{font-family:var(--cond);font-weight:700;font-size:11.5px;letter-spacing:.07em;
  color:var(--ground);background:var(--ai);padding:2px 8px;white-space:nowrap}
/* 連動していることが伝わらない、というのが最大の不満だった。
   **表より下を1つの枠に入れ、見出しに選択中の条件を常時書く。**
   枠を外すと「たまたま下にも数字がある」ようにしか見えない。 */
.linked{margin-top:20px;border:1px solid var(--ai)}
.linkhd{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 12px;padding:8px 14px;
  background:var(--ai);color:var(--ground);font-family:var(--cond);font-weight:700;
  font-size:12px;letter-spacing:.06em}
.linkhd .v{font-family:var(--mono);font-size:14px;font-variant-numeric:tabular-nums;letter-spacing:0}
.linkhd .amt{margin-left:auto;font-family:var(--mono);font-size:16px;font-variant-numeric:tabular-nums;letter-spacing:0}
.linked-in{padding:16px 18px}
.linked-in .compo{margin-top:0}
/* 変わったことを一瞬だけ示す。**つまみの input ごとに光らせないこと**
   （動かしているあいだじゅう点滅して読めなくなる）。押した時と、つまみを
   離した時だけ呼ぶ。 */
@keyframes lnkflash{from{background:var(--sunk)}to{background:transparent}}
.linked-in.flash{animation:lnkflash .6s ease-out}
@media (prefers-reduced-motion:reduce){.linked-in.flash{animation:none}}
@media (max-width:560px){.linkhd .amt{margin-left:0}}
.compo{margin-top:20px;border:1px solid var(--rule)}
.compo div{display:flex;gap:12px;align-items:baseline;padding:11px 14px;border-bottom:1px solid var(--rule-soft);font-size:13px}
.compo div:last-child{border-bottom:0}
.compo .k{font-family:var(--cond);font-weight:600;color:var(--ink)}
.compo .v{margin-left:auto;font-family:var(--mono);font-variant-numeric:tabular-nums}
.compo .betsu{color:var(--shu);font-family:var(--cond);font-weight:700}
/* **`.formula` という名前は使えない。**トップページ（template.html）が
   別の用途で先に定義しており、ツールのCSSをトップへ流し込むと、あとから来る
   こちらが勝ってトップの算式ブロックが黙って別の見た目になる（2026-09-15）。 */
.calcline{margin-top:16px;font-size:12px;line-height:1.95;color:var(--ink2)}
.calcline li{margin-bottom:2px}
.gloss{margin-top:16px;border-top:1px solid var(--rule)}
.gloss dt{font-family:var(--cond);font-weight:700;font-size:13.5px;color:var(--ink);margin-top:12px}
.gloss dd{margin:3px 0 0;font-size:12.5px;line-height:1.85;color:var(--ink2)}
.prbtn{margin-top:16px;font-family:var(--cond);font-size:13px;padding:9px 18px;background:var(--surface);
  color:var(--ink);border:1px solid var(--ink);border-radius:2px;cursor:pointer}
.prbtn:hover{background:var(--sunk)}
@media (max-width:560px){.brk-row{grid-template-columns:8.4em 3.6em 1fr;}.brk-row .am{grid-column:2/4;text-align:left}}
@media print{
  /* **.cite（引用のしかた）は消さないこと。**このサイトは「出典を明記すれば
     引用してよい」という立場なので、紙に配るときこそ出典表記が要る。
     元は /cost/ を概算シート1枚にする目的で消していたが、同じCSSが
     地域226ページにも効くようになったため外した（2026-09-15）。 */
  .masthead,.sitenav,.cta,.sitelink,.prbtn,.finder{display:none!important}
  .tool,.compo,.warn,.avgnote,.viewtab,.gloss,.linked{break-inside:avoid}
  .howto{display:none!important}
  .linkhd{background:transparent!important;color:inherit!important;border-bottom:1px solid #999}
  .tool-in,.brk-track{background:transparent!important}
  .avgnote{background:transparent!important}
  .brk-track{border:1px solid #999}
  .brk-track i{background:#666!important}
  body{font-size:11pt}
  a[href]:after{content:""}
  @page{margin:14mm}
}
"""

# `<style>` タグ付き。head に足すときはこちら。
# **トップページ（template.html）は自前の <style> の中へ流し込む**ので、
# あちらには CSS（タグ無し）を渡すこと。タグ付きを入れると <style> が
# 入れ子になって、そのページのCSSがまるごと効かなくなる。
EXTRA_CSS = "\n<style>" + CSS + "</style>"


def data(basis: dict) -> dict:
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


def tool(basis: dict) -> str:
    """ツール本体の HTML（`<div class="tool">` 1個）。

    CSS は `EXTRA_CSS` を head に、スクリプトは `scripts()` を本文の最後に
    それぞれ渡すこと。3つのうち1つでも欠けると、画面は出るのに動かない。
    """
    return f'''    <div class="tool">
      <div class="tool-in">
        <label><span class="cap">総戸数</span>
          <span class="unitv"><b id="oUnits">{UNIT_DEFAULT}</b><small>戸</small></span>
          <input type="range" id="iUnits" min="{UNIT_MIN}" max="{UNIT_MAX}" step="1" value="{UNIT_DEFAULT}">
          <span class="unitax"><span>{UNIT_MIN}</span><span>{UNIT_MAX}</span></span>
          <span class="drag">つまみを動かすと、下の表の9つの金額がすべて変わります</span>
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
        <p class="lede" style="margin:0 0 12px">原典（{S.PAGE_PER_UNIT}）は<strong>工事回数ごとに四分位を出しています</strong>ので、同じ形で3行とも並べます。回数で金額の水準が違うことも、そのまま見えます。</p>
        <p class="howto"><b>使い方</b><span><strong>下線の付いた金額は押せます。</strong>ひとつ押すと、その金額で<strong>下の枠（構成表・内訳・計算）がまとめて切り替わります</strong>。</span></p>
        <div class="tabwrap"><table class="viewtab">
          <thead><tr>
            <th class="nm">工事回数</th>
            <th>下位25%</th><th>中央値</th><th>上位25%</th>
            <th class="avgc">平均<span class="sub">分位ではありません</span></th>
          </tr></thead>
          <tbody id="oTable"></tbody>
        </table></div>
        <p class="qnote" id="oNote">—</p>
        <p class="qnote">上段が税抜の金額、下段が戸あたり（万円/戸）です。税込は10%を足した額で、選んだ金額について下の構成表に出しています。10万円未満は四捨五入しています。</p>
        <p class="avgnote"><b>「平均」は分位ではありません。順位として読まないでください。</b>少数の大きな案件に引っ張られるため、分布が右に伸びていると上位25%を上回ることがあります。原典では<b>1回目がこれにあたり、平均 151.6 万円/戸が上位25%値 134.0 万円/戸を上回っています</b>（2回目 112.4 &lt; 129.8、3回目以上 106.1 &lt; 125.7 は上回っていません）。左の3列（四分位）と罫線で切り離してあるのはこのためです。</p>

        <div class="linked">
          <div class="linkhd">
            <span>いま下に表示しているのは</span>
            <span class="v" id="oSel">—</span>
            <span class="amt" id="oSelAmt">—</span>
          </div>
          <div class="linked-in" id="oLinked">
            <div class="compo" id="oCompo"></div>

            <h3 style="margin:26px 0 0;font-family:var(--cond);font-size:15px">工事金額の内訳（調査全体の平均的な姿）</h3>
            <p class="qnote" id="oBrkNote">—</p>
            <div class="brk" id="oBrk"></div>
            <p class="qnote">出典 {S.SOURCE_PUBLISHER}「{S.SOURCE_NAME}」{S.PAGE_BREAKDOWN}（総工事金額に対する割合。建築系工事の内訳は同ページの建築系合計に対する割合を按分）。{S.PAGE_SHARE} の「総工事金額に占める割合」と一致することを確認しています。<strong>共通仮設費と消費税は、この100%のどこにも含まれていません。</strong>内訳の母数は n={S.BREAKDOWN_N} で、戸あたり金額（n={S.SOURCE_N}）とは異なります（建築系工事を実施していないサンプルを除外した集計のため）。</p>

            <h3 style="margin:26px 0 0;font-family:var(--cond);font-size:15px">計算の内訳</h3>
            <ol class="calcline" id="oFormula"></ol>
          </div>
        </div>

        <button type="button" class="prbtn" id="prBtn">印刷 / PDFで保存</button>
      </div>
    </div>'''


def section(basis: dict, *, cost_url: str) -> str:
    """地域ページに埋め込む1セクション（見出し＋注意書き＋ツール＋スクリプト）。

    **注意書き（.warn）を外してツールだけ置かないこと。**/cost/ では大きな
    注意書きがツールの上にあり、共通仮設費と消費税が入っていないこと、
    統計に戸数を掛けただけの数値であることを宣言している。**金額だけ持ってきて
    注意書きを置いていくと、この企画の立ち位置が崩れる。**

    **戸数はそのページの戸数と繋げない。**市区町村ページには「その市の
    非木造共同住宅ストック◯◯戸」が載っているが、それを掛けると
    「この市を全部直すと◯◯億円」という、統計の読み方として成立しない数字になる。
    つまみの戸数は独立した例示値で、そのことを画面に書く（cost_banner.py と同じ）。
    """
    d = data(basis)
    return f'''  <section>
    <h2><span class="idx">Tool</span>この規模なら、工事金額はいくらくらいか</h2>
    <p class="lede">国土交通省の実態調査（回答{d["n"]}件）にある<strong>戸あたり工事金額</strong>を、
    建設工事費デフレーターで{d["month"]}の水準へ換算し、戸数を掛けたものです。
    <strong>つまみの戸数は操作のための例で、このページに出ている戸数とは関係ありません。</strong></p>
    <div class="warn">
      <h4>この数字が何であって、何でないか</h4>
      <ul>
        <li><strong>共通仮設費が入っていません。</strong>現場事務所・仮設トイレ・資材置場・安全対策・近隣対策などの費用です。原典の集計対象外なので、<strong>実際の総額はここに出る額より上になります。</strong>消費税と設計コンサルタント業務の費用も別です。</li>
        <li>これは<strong>統計の分布に戸数を掛けただけ</strong>の数値で、その建物の工事費ではありません。劣化の程度、仕様、外壁の形状・面積、立地、工期は一切反映していません。</li>
        <li>幅は回答の<strong>真ん中50%</strong>です。外側にも50%の回答があります。<strong>個別の見積がこの範囲を外れていることは、それ自体では何も意味しません。</strong></li>
        <li>用語（仮設・共通仮設・足場）の違い、算式と出典の全文は<a href="{cost_url}">工事金額の分布のページ</a>にあります。</li>
      </ul>
    </div>
{tool(basis)}
  {scripts(basis)}
  </section>
'''


def scripts(basis: dict) -> str:
    """ツールが読むデータと JS。**本文の最後に1回だけ置く。**"""
    return ('<script id="cost-data" type="application/json">'
            + json.dumps(data(basis), ensure_ascii=False)
            + '</script><script>' + JS + '</script>')


JS = r"""
(function(){
  var D = JSON.parse(document.getElementById('cost-data').textContent);
  var $ = function(id){ return document.getElementById(id); };
  var nf = new Intl.NumberFormat('ja-JP');
  var nf1 = new Intl.NumberFormat('ja-JP', {minimumFractionDigits:1, maximumFractionDigits:1});
  var ROUND = 100000, TAX = 0.10;

  var iUnits=$('iUnits'), iFloors=$('iFloors'), iScope=$('iScope');
  var REDUCE = window.matchMedia
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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
      cb.addEventListener('change', function(){ picked[r.label] = cb.checked; render(true); });
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

  function render(flash){
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
        /* 選択中のセルだけに出る。CSS が .cell.on のときだけ display:block にする。
           「選択中」ではなく**「下に表示中」**と書くこと。何と繋がっているかが
           伝わらないのが元の問題だった。 */
        var g = document.createElement('span');
        g.className = 'tag'; g.textContent = '▼ 下に表示中';
        b.appendChild(a); b.appendChild(p); b.appendChild(g);
        b.addEventListener('click', function(){
          sel = {repeat: row.label, view: v.key};
          render(true);
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
      + selView.label + '」です。下の枠の中（構成表・内訳・計算）は、すべてこの金額で出しています。'
      + '表のどの金額を押しても切り替わります。';

    /* --- 構成（共通仮設費は別途） --- */
    var pick = cell(selRow, sel.view, c);
    var pv = money(pick.amount);

    /* 連動枠の見出し。**下の枠が何で決まっているかを常時ここに出す。**
       消すと「たまたま下にも数字がある」ようにしか見えなくなる。 */
    $('oSel').textContent = nf.format(c.units) + '戸 ／ ' + selRow.label
      + ' ／ ' + selView.label;
    $('oSelAmt').textContent = man(pv);
    if(flash && !REDUCE){
      var lk = $('oLinked');
      lk.classList.remove('flash');
      void lk.offsetWidth;          /* 連続で押しても毎回光らせるための再描画 */
      lk.classList.add('flash');
    }
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

  /* **つまみの input ごとに光らせないこと。**動かしているあいだじゅう点滅して
     読めなくなる。値の追従は input、点滅は change（＝離したとき）で分ける。 */
  [iUnits, iFloors, iScope].forEach(function(e){
    e.addEventListener('input', function(){ render(false); });
    e.addEventListener('change', function(){ render(true); });
  });
  $('prBtn').addEventListener('click', function(){ window.print(); });

  /* バナーから引き継いだ戸数。**照合できない値は無視する。** */
  var m = /[?&]units=(\d+)/.exec(location.search);
  if(m){
    var n = +m[1];
    if(n >= D.unitMin && n <= D.unitMax) iUnits.value = n;
  }
  render(false);
})();
"""

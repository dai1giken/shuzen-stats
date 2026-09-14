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

from build_consultation import link as consult_link
from build_pref import SITE_URL, cite_block, cta_housing, foot, head
from cost_banner import UNIT_DEFAULT, UNIT_MAX, UNIT_MIN, per_unit_median
# ツール本体（CSS・HTML・JS・JSに渡す値）は cost_tool.py が持つ。
# **地域ページからも同じ物を使うため、ここへ戻さないこと**（循環 import になる）。
from cost_tool import EXTRA_CSS, data as _data, scripts as tool_scripts, tool as tool_html
import consult_form
import shuzen_survey as S

HERE = Path(__file__).resolve().parent

PAGE_URL = SITE_URL + "cost/"

# 総戸数のつまみの範囲は cost_banner が持つ。**2箇所に書かない。**
# バナーと本体で範囲がずれると、バナーから渡した ?units= が弾かれる。
# 階数の選択肢と表の見方（FLOOR_OPTIONS / VIEWS）は cost_tool.py。
# ツールの CSS は cost_tool.EXTRA_CSS。


# JS に渡す値の組み立ては cost_tool.data()（別名 _data で import 済み）。


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

    # このページだけは**タイトルに金額を入れてよい。**全国の分布そのものが主題で、
    # 地名と並んでいないので「その地域の相場」と読まれる余地がない。
    # （市区町村・都道府県ページで金額をタイトルに入れない理由は build_city.py を見ること）
    _med = per_unit_median(basis)[0]
    title = (f"大規模修繕の工事金額 1戸あたり中央値{_med:,.0f}万円｜戸数から分布を見る")
    desc = (f"国土交通省の実態調査（回答{S.SOURCE_N}件）では、大規模修繕の工事金額は"
            f"1戸あたり中央値{_med:,.0f}万円（全国・2回目・{data['month']}の水準へ換算）。"
            f"総戸数を入れると、四分位ぶんの分布と内訳が出ます。"
            "共通仮設費と消費税は含みません。")

    h = [head(title, desc, PAGE_URL, crumb="工事金額の分布",
              extra_css=EXTRA_CSS + consult_form.EXTRA_CSS)]

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

{tool_html(basis)}
  {tool_scripts(basis)}
{consult_form.form(page_url=PAGE_URL, page_title=title, open_=True)}
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

    # 呼びかける相手は city/ pref/ と同じ（元請業者様・管理会社様 等へ）。
    # 送り先だけ案件相談ページにしてある（2026-09-14 本人判断）。条件が整理された
    # 状態で届くので、こちらから聞き直す往復が減る。
    h.append(cta_housing(consult_link("cost")))

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


# ツールの JS は cost_tool.JS。


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    build(basis)


if __name__ == "__main__":
    main()

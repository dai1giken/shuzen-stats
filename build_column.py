# -*- coding: utf-8 -*-
"""企業サイト（dai1giken.co.jp）の技術コラムを生成する。

    py build_column.py      # build.py から呼ばれる（basis.json が要る）

出力: column/index.html ／ column/koushu.html ／ column/<用途>.html

--- 置き場所 -------------------------------------------------------------
生成先は企業サイトの htdocs/column/ で、統計サイト（/shuzen-stats/）とは別。
**統計サイトは公表値だけ、こちらは当社の説明を含む。**性格が違うので分けている。
ZIP を htdocs で解凍すると shuzen-stats/ と column/ の両方が正しい位置に入る。

--- styles.css を書き換えない -------------------------------------------
記事固有の CSS は各ページに <style> で埋め込む。企業サイトの styles.css に
足すと、**毎月のZIPで企業サイトのCSSを上書きすることになり**、誰かが直接
直した変更を巻き戻す。共有部分（ヘッダー・フッター・配色）だけ ../styles.css
を読み込んで使う。

--- なぜ工種の解説を1本に分けたのか -------------------------------------
用途別6ページに同じ工種の説明を載せると、後半がまるごと重複する。
検索エンジンから見ても読む人から見ても価値がない。
**工種は koushu.html に1本置き、用途ページからは要約＋リンクにする。**
用途ページの主役は、その用途固有の数字（最多県・増減）にする。

--- 書いてよいこと ------------------------------------------------------
公表統計と、工種の一般的な役割まで。**費用の相場、法令の当てはめ、税務の
判断は書かない。**間違えたときの害が大きく、当社が言う筋合いでもない。
分譲マンション向けの語（管理組合・修繕積立金・区分所有など）も使わない。
"""
from __future__ import annotations

import json
from pathlib import Path

# 解析タグは統計サイト側と同じものを使う。ここを独自に持つと、
# 測定IDを変えたときにコラムだけ古いままになる。
from build_pref import analytics_tags

HERE = Path(__file__).resolve().parent

SLUG = {"事務所": "office", "店舗": "shop", "工場・作業場": "factory",
        "倉庫": "warehouse", "学校の校舎": "school", "病院・診療所": "hospital"}

# ページの言い回し。統計の用途区分をそのまま使うと硬いので、
# 記事の見出しだけ通りのよい言い方にする。中身の定義は変えない。
HEADING = {"事務所": "オフィスビル", "店舗": "店舗・商業施設",
           "工場・作業場": "工場・作業場", "倉庫": "物流施設・倉庫",
           "学校の校舎": "学校・校舎", "病院・診療所": "病院・診療所"}

# 統計の定義の言い換えに留める。当社の見立ては書かない。
WHAT = {
    "事務所": "オフィスビル、事業所の事務棟など。",
    "店舗": "物販店、飲食店、ショッピングセンターなど。",
    "工場・作業場": "製造の工場、作業場、整備場など。",
    "倉庫": "物流施設、保管倉庫、配送センターなど。",
    "学校の校舎": "小中高、大学、専門学校の校舎。",
    "病院・診療所": "病院、診療所、介護・福祉の施設を含みます。",
}

TRADES = [
    ("足場", "作業床と養生を組み立てます。他の四工種は、すべてこの足場の上で行われます。"),
    ("下地補修", "コンクリートやモルタルのひび割れ、欠損、浮きを処理します。仕上げの前に躯体側を整える工程です。"),
    ("シーリング", "目地や、部材の取合いに充填された材料を打ち替えます。雨水の侵入経路になりやすい箇所です。"),
    ("塗装", "外壁や鉄部の仕上げ材を塗り替えます。意匠の回復だけでなく、下地を保護する役割を持ちます。"),
    ("防水", "屋根、屋上、庇などの防水層を改修します。外壁とは別の工法・別の職種になります。"),
]

CSS = """<style>
/* 技術コラム専用。共有部分（ヘッダー・フッター・配色）は ../styles.css。
   企業サイトの styles.css は書き換えない。毎月のZIPで上書きしないため。 */
.col-main{padding:108px 0 0;background:var(--paper);position:relative;z-index:1}
.col-wrap{max-width:760px}
.col-crumb{font-size:.8rem;color:var(--muted);margin:0 0 34px;letter-spacing:.04em}
.col-crumb a{color:var(--muted)}
.col-crumb a:hover{color:var(--bronze)}
.col-head{border-bottom:1px solid var(--line);padding-bottom:30px;margin-bottom:44px}
.col-eyebrow{font-size:.72rem;letter-spacing:.22em;color:var(--bronze);margin:0 0 14px;font-weight:700}
.col-title{font-family:"Noto Serif JP",serif;font-weight:700;
  font-size:clamp(1.5rem,3.4vw,2.05rem);line-height:1.62;margin:0;color:var(--ink);letter-spacing:.01em}
.col-sub{margin:20px 0 0;font-size:.95rem;line-height:2.05;color:var(--muted)}
.col-sec{margin-bottom:62px}
.col-h2{font-family:"Noto Serif JP",serif;font-weight:700;font-size:1.32rem;line-height:1.7;
  color:var(--ink);margin:0 0 22px;padding-left:15px;border-left:4px solid var(--bronze)}
.col-h3{font-weight:700;font-size:1.02rem;color:var(--ink);margin:40px 0 14px}
.col-sec p{font-size:.95rem;line-height:2.15;margin:0 0 20px;color:var(--text)}
.col-sec strong{font-weight:700;color:var(--ink)}
.col-list{margin:0 0 20px;padding-left:1.3em}
.col-list li{font-size:.95rem;line-height:2.05;margin-bottom:7px;color:var(--text)}
.col-trades{list-style:none;margin:28px 0 34px;padding:0}
.col-trades li{display:grid;grid-template-columns:auto 1fr;gap:20px;padding:22px 0;border-top:1px solid var(--line)}
.col-trades li:last-child{border-bottom:1px solid var(--line)}
.tr-n{font-family:"Noto Serif JP",serif;font-size:1.05rem;font-weight:600;color:var(--bronze);
  letter-spacing:.05em;padding-top:2px}
.tr-body h3{margin:0 0 8px;font-size:1.02rem;font-weight:700;color:var(--ink)}
.tr-body p{margin:0;font-size:.93rem;line-height:2}
.col-tablewrap{overflow-x:auto;margin:24px 0}
.col-table{border-collapse:collapse;width:100%;min-width:420px;font-size:.9rem}
.col-table th,.col-table td{padding:11px 14px;border-bottom:1px solid var(--line);text-align:left}
.col-table thead th{background:var(--tint);color:var(--ink);font-weight:700;font-size:.82rem;letter-spacing:.04em}
.col-table td.num{text-align:right;font-variant-numeric:tabular-nums}
.col-table caption{caption-side:bottom;text-align:left;padding-top:10px;font-size:.78rem;
  color:var(--muted);line-height:1.85}
.col-note{background:var(--tint);border-left:4px solid var(--muted-d);padding:18px 22px;margin:26px 0}
.col-note p{font-size:.86rem;line-height:1.95;margin:0 0 12px;color:var(--muted)}
.col-note p:last-child{margin-bottom:0}
.col-more{margin:26px 0 0;font-size:.9rem}
.col-more a{color:var(--bronze);font-weight:500}
.col-more a:hover{color:var(--ink)}
.col-foot{margin:72px 0 0;padding:22px 0 0;border-top:1px solid var(--line)}
.col-foot p{font-size:.8rem;line-height:1.95;color:var(--muted);margin:0}
.col-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:2px;margin:30px 0 0}
.col-cards a{display:block;padding:22px 24px;border:1px solid var(--line);text-decoration:none;background:var(--paper)}
.col-cards a:hover{background:var(--tint);border-color:var(--bronze)}
.footer-col-link{margin-top:18px}
.cc-t{display:block;font-family:"Noto Serif JP",serif;font-weight:700;font-size:1.05rem;color:var(--ink);margin-bottom:6px}
.cc-d{display:block;font-size:.84rem;line-height:1.9;color:var(--muted)}
@media (max-width:680px){.col-main{padding-top:88px}.col-trades li{grid-template-columns:1fr;gap:6px}}
</style>"""


def _head(title: str, desc: str, canonical: str, og_desc: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} ｜ 株式会社 第一技研</title>
  <meta name="description" content="{desc}" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{og_desc}" />
  <meta property="og:type" content="article" />
  <meta property="og:locale" content="ja_JP" />
  <link rel="canonical" href="{canonical}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@500;600;700&display=swap" rel="stylesheet" />
  <link rel="icon" href="../favicon.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="../styles.css" />{analytics_tags()}
{CSS}
</head>
<body>

<header class="site-header" id="top">
  <div class="header-inner">
    <a href="../" class="brand" aria-label="株式会社 第一技研 ホーム">
      <img src="../img/logo-black.png" alt="第一技研 D GIKEN ロゴ" class="brand-logo" />
      <span class="brand-text">株式会社&#8202;第一技研</span>
    </a>
    <nav class="site-nav" aria-label="グローバルナビゲーション">
      <a href="../#about">企業姿勢</a>
      <a href="../#strength">強み</a>
      <a href="../#service">事業内容</a>
      <a href="../#works">施工実績</a>
      <a href="../#company">会社概要</a>
      <a href="../#contact" class="nav-cta">お問い合わせ</a>
    </nav>
    <button class="nav-toggle" aria-label="メニューを開く" aria-expanded="false">
      <span></span><span></span><span></span>
    </button>
  </div>
</header>

<main class="col-main">
  <div class="container col-wrap">
"""


FOOTER = """  </div>
</main>

<footer class="site-footer">
  <div class="container footer-stats">
    <!-- 問い合わせ導線。ここは企業サイト側なので .cta ではなく
         企業サイトの .footer-stats-link を使う（統計サイトとCSSが違う）。
         **文言は build_pref.CTA_BUILDING と同じものを手で複製している。**
         CSSクラスが違うので共有できない。片方だけ直すと食い違うので、
         どちらかを変えたら必ずもう片方も直すこと（2026-09-12 に実際にずれた）。 -->
    <a class="footer-stats-link" href="../#contact">
      <span class="footer-stats-label">お見積りをご希望の場合は</span>
      <span class="footer-stats-title">建物調査・お見積は一棟から</span>
      <span class="footer-stats-desc">事務所・店舗・倉庫・工場などの外装改修を、足場から防水まで自社管理で一貫対応しています。</span>
      <span class="footer-stats-arrow" aria-hidden="true">→</span>
    </a>
    <a class="footer-stats-link footer-col-link" href="/shuzen-stats/">
      <span class="footer-stats-label">公開統計</span>
      <span class="footer-stats-title">大規模修繕統計ビューア</span>
      <span class="footer-stats-desc">国土交通省・総務省の統計を、都道府県別・市区町村別に整理して公開しています。出典と算式はすべて明記しています。</span>
      <span class="footer-stats-arrow" aria-hidden="true">→</span>
    </a>
  </div>
  <div class="container footer-inner">
    <div class="footer-brand">
      <img src="../img/logo-white.png" alt="第一技研 D GIKEN" class="footer-logo" />
      <p class="footer-license">特定建設業&ensp;東京都知事許可（特-7）第138912号<br />A Member of NISSO GROUP（東証・名証 1444）</p>
    </div>
    <p class="footer-copy">© 1996–2026 DAIICHI GIKEN CO., LTD.</p>
  </div>
</footer>

<script>
  (function () {
    var toggle = document.querySelector('.nav-toggle');
    var nav = document.querySelector('.site-nav');
    if (!toggle || !nav) return;
    toggle.addEventListener('click', function () {
      var open = document.body.classList.toggle('nav-open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    nav.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') {
        document.body.classList.remove('nav-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  })();
</script>

</body>
</html>
"""


def build(basis: dict) -> int:
    nr = basis.get("nonres")
    if not nr:
        return 0
    ref = int(basis["generated"][:4])
    years, prefs = nr["years"], nr["prefs"]
    bld, flo = nr["buildings"], nr["floor_m2"]
    old = [y for y in years if ref - y >= 13]
    age_lo, age_hi = ref - max(old), ref - min(old)
    # 増減を見る前後5年。**同じ長さの窓で比べる。**期間が違うと増減の意味が変わる
    early = years[:5]
    late = years[-5:]

    def s(u, ps, ys, src=None):
        src = src or bld
        return sum(src[u].get(p, {}).get(str(y), 0) for p in ps for y in ys)

    out = HERE / "column"
    out.mkdir(exist_ok=True)
    totals = {u: s(u, prefs, old) for u in nr["uses"]}
    ranked = sorted(nr["uses"], key=lambda u: -totals[u])
    written = []

    # ---- 工種の解説（1本だけ。用途ページからは要約＋リンク）----
    tr = "".join(
        f'<li><span class="tr-n">{i+1:02d}</span><div class="tr-body">'
        f'<h3>{n}</h3><p>{d}</p></div></li>'
        for i, (n, d) in enumerate(TRADES))
    p = out / "koushu.html"
    p.write_text(
        _head("外装改修を構成する五つの専門工事",
              "外装改修は足場・下地補修・シーリング・塗装・防水という複数の専門工事の組み合わせです。"
              "それぞれの役割と、工程の順序を入れ替えられない理由を整理しました。",
              "https://dai1giken.co.jp/column/koushu.html",
              "足場・下地補修・シーリング・塗装・防水。五つの専門工事の役割と、工程の依存関係。")
        + f'''    <p class="col-crumb"><a href="../">ホーム</a>　/　<a href="index.html">技術コラム</a>　/　外装改修の工種</p>

    <header class="col-head">
      <p class="col-eyebrow">技術コラム</p>
      <h1 class="col-title">外装改修を構成する<br />五つの専門工事</h1>
      <p class="col-sub">建物の外装改修は、単一の工事ではありません。職種の異なる専門工事が組み合わさって成立します。それぞれが何を担い、なぜ順序を入れ替えられないのかを整理しました。</p>
    </header>

    <section class="col-sec">
      <h2 class="col-h2">五つの工種と、それぞれの役割</h2>
      <p>外装改修は、次の専門工事の組み合わせです。それぞれ職種が異なり、通常は別の業者が担当します。</p>
      <ol class="col-trades">{tr}</ol>

      <h3 class="col-h3">順序を入れ替えられない、という制約</h3>
      <p>この五つには工程上の依存関係があります。<strong>足場が架からなければ他の工事は始められず、足場を解体してしまえば元には戻せません。</strong>下地補修が終わらないうちに仕上げには進めません。</p>
      <p>つまり外装改修は、<strong>複数の職種を一つの工程表の上に並べ、順番に入れる</strong>工事です。ひとつの工種が遅れれば、後続はすべて後ろにずれます。</p>

      <h3 class="col-h3">職種が分かれると、何が発生するか</h3>
      <p>五つの工種をそれぞれ別の会社に発注する場合、発注者の側には次が生じます。</p>
      <ul class="col-list">
        <li>会社ごとの見積の取得と比較</li>
        <li>工程の調整と、遅延が出たときの再調整</li>
        <li>会社ごとの安全書類の受領と確認</li>
        <li>不具合が出たときの、どの工種の責任かという切り分け</li>
      </ul>
      <p>第一技研は、<strong>足場・下地補修・シーリング・塗装・防水（および内装）の六科目を自社管理で一貫して行っています。</strong>職別の手配・調整・安全書類までを当社が担うため、上に挙げた調整が発注者の側で発生しません。創業1996年から30年、この体制で改修工事にあたってきました。</p>
      <p class="col-more"><a href="../#service">六科目の詳細は「事業内容」をご覧ください →</a></p>
    </section>

    <section class="col-sec">
      <h2 class="col-h2">用途別の建物数を見る</h2>
      <p>首都圏にどれだけの建物があるかは、用途ごとに整理しています。</p>
      <div class="col-cards">{"".join(
        f'<a href="{SLUG[u]}.html"><span class="cc-t">{HEADING[u]}</span>'
        f'<span class="cc-d">首都圏に {totals[u]:,}棟（築{age_lo}〜{age_hi}年）</span></a>'
        for u in ranked)}</div>
    </section>

    <div class="col-foot">
      <p>工事の内容・工程は建物の構造、規模、劣化の状況によって異なります。個別の建物についてのご相談は、<a href="../#contact">お問い合わせ</a>よりご連絡ください。</p>
    </div>
''' + FOOTER, encoding="utf-8")
    written.append("koushu")

    # ---- 用途別 ----
    for use in nr["uses"]:
        slug, head_name = SLUG[use], HEADING[use]
        n_old = totals[use]
        m2 = s(use, prefs, old, flo)
        e, l = s(use, prefs, early), s(use, prefs, late)
        delta = (l / e - 1) * 100 if e else 0
        top_pref = max(prefs, key=lambda p: s(use, [p], old))
        rank = ranked.index(use) + 1

        rows = "".join(
            f'<tr><td>{p}</td><td class="num">{s(use,[p],old):,}</td>'
            f'<td class="num">{s(use,[p],old,flo):,} m²</td></tr>'
            for p in sorted(prefs, key=lambda p: -s(use, [p], old)))

        # 増減の書き方。**「需要が堅い」のような解釈は書かない。**数字だけ置く
        move = (f"{abs(delta):.0f}% 減っています" if delta < 0
                else f"{delta:.0f}% 増えています")
        cmp_note = ""
        if delta > -15:
            others = [u for u in nr["uses"] if u != use]
            worse = sum(1 for u in others
                        if (s(u, prefs, late) / s(u, prefs, early) - 1) * 100 < delta)
            if worse == len(others):
                cmp_note = "　これは六用途のなかで最も小さい変化です。"

        p = out / f"{slug}.html"
        p.write_text(
            _head(f"{head_name}の外装改修｜首都圏の建物数",
                  f"一都三県で{min(old)}〜{max(old)}年度に着工した{use}は {n_old:,}棟。"
                  f"{ref}年時点で築{age_lo}〜{age_hi}年。都県別の内訳と、外装改修の工種の構成を整理しました。",
                  f"https://dai1giken.co.jp/column/{slug}.html",
                  f"首都圏の{use}は {n_old:,}棟が築{age_lo}〜{age_hi}年（国土交通省 建築着工統計）。")
            + f'''    <p class="col-crumb"><a href="../">ホーム</a>　/　<a href="index.html">技術コラム</a>　/　{head_name}</p>

    <header class="col-head">
      <p class="col-eyebrow">技術コラム</p>
      <h1 class="col-title">{head_name}の外装改修<br />首都圏の建物数</h1>
      <p class="col-sub">{WHAT[use]}首都圏にどれだけの建物があり、そのうちどれだけが築{age_lo}〜{age_hi}年にあたるかを、公表統計から整理しました。あわせて、外装改修がどの工種で構成されるかに触れます。</p>
    </header>

    <section class="col-sec">
      <h2 class="col-h2">首都圏の{head_name}は、{n_old:,}棟が築{age_lo}〜{age_hi}年</h2>
      <p>国土交通省「建築着工統計調査」によると、一都三県で{min(old)}〜{max(old)}年度に着工した{use}は <strong>{n_old:,}棟</strong>、延べ床面積で <strong>約{m2/10000:,.0f}万m²</strong> です。{ref}年時点で築{age_lo}〜{age_hi}年にあたります。六用途のなかでは{rank}番目の多さです。</p>

      <div class="col-tablewrap">
        <table class="col-table">
          <caption>一都三県の{use}（{min(old)}〜{max(old)}年度着工）／国土交通省 建築着工統計調査</caption>
          <thead><tr><th>都県</th><th>棟数</th><th>延べ床面積</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>

      <p>もっとも多いのは<strong>{top_pref}</strong>です。また着工の棟数は、{min(early)}〜{max(early)}年度の {e:,}棟 に対して {min(late)}〜{max(late)}年度は {l:,}棟 で、<strong>{move}</strong>。{cmp_note}</p>

      <div class="col-note">
        <p><strong>この数字の読み方。</strong>これは着工（フロー）の累計であり、現在建っている棟数ではありません。取り壊しや用途変更は反映されていません。また、この統計表は{min(years)}年度からの収録のため、<strong>それ以前に建った建物は含まれていません</strong>。実際の建物はこれより多く存在します。</p>
        <p>大規模修繕の実施周期は12〜15年程度が目安（国土交通省の長期修繕計画作成ガイドラインによる）とされますが、築年数だけで実施時期が決まるものではありません。用途は着工時の区分です。</p>
      </div>

      <p class="col-more"><a href="/shuzen-stats/nonres/{slug}.html">年度別の推移や他用途との比較は「首都圏の{use}の大規模修繕統計」でご覧いただけます →</a></p>
    </section>

    <section class="col-sec">
      <h2 class="col-h2">外装改修は、五つの専門工事でできている</h2>
      <p>建物の外装改修は単一の工事ではなく、<strong>足場・下地補修・シーリング・塗装・防水</strong>という職種の異なる専門工事の組み合わせです。足場が架からなければ他は始められず、解体すれば元には戻せないため、工程の順序を入れ替えることができません。</p>
      <p>これらを別々の会社に発注する場合、見積の比較、工程の調整、安全書類の確認、不具合が出たときの責任の切り分けが、発注者の側で発生します。第一技研は<strong>六科目を自社管理で一貫して行う</strong>ため、これらの調整を当社が担います。</p>
      <p class="col-more"><a href="koushu.html">五つの工種それぞれの役割は「外装改修を構成する五つの専門工事」で詳しく →</a></p>
    </section>

    <div class="col-foot">
      <p>本記事の統計数値は、国土交通省「建築着工統計調査」（政府統計総合窓口 e-Stat）の公表値です。工事の内容・工程は建物の構造、規模、劣化の状況によって異なります。個別の建物についてのご相談は、<a href="../#contact">お問い合わせ</a>よりご連絡ください。</p>
    </div>
''' + FOOTER, encoding="utf-8")
        written.append(slug)

    # ---- 一覧 ----
    cards = "".join(
        f'<a href="{SLUG[u]}.html"><span class="cc-t">{HEADING[u]}</span>'
        f'<span class="cc-d">首都圏に {totals[u]:,}棟（築{age_lo}〜{age_hi}年）</span></a>'
        for u in ranked)
    (out / "index.html").write_text(
        _head("技術コラム",
              "外装改修の工種の構成と、首都圏の建物数を用途別に整理しています。"
              "数値は国土交通省「建築着工統計調査」の公表値です。",
              "https://dai1giken.co.jp/column/",
              "外装改修の工種と、首都圏の建物数を用途別に。")
        + f'''    <p class="col-crumb"><a href="../">ホーム</a>　/　技術コラム</p>

    <header class="col-head">
      <p class="col-eyebrow">技術コラム</p>
      <h1 class="col-title">技術コラム</h1>
      <p class="col-sub">外装改修がどの工種で構成されるか、首都圏にどれだけの建物があるかを、公表統計をもとに整理しています。数値は国土交通省「建築着工統計調査」の公表値です。</p>
    </header>

    <section class="col-sec">
      <h2 class="col-h2">工種について</h2>
      <div class="col-cards">
        <a href="koushu.html"><span class="cc-t">外装改修を構成する五つの専門工事</span>
        <span class="cc-d">足場・下地補修・シーリング・塗装・防水。それぞれの役割と、工程の依存関係</span></a>
      </div>
    </section>

    <section class="col-sec">
      <h2 class="col-h2">用途別の建物数</h2>
      <p>一都三県で{min(old)}〜{max(old)}年度に着工し、{ref}年時点で築{age_lo}〜{age_hi}年にあたる建物の数です。着工の累計であり、現在建っている棟数ではありません。</p>
      <div class="col-cards">{cards}</div>
    </section>

    <div class="col-foot">
      <p>統計数値は国土交通省「建築着工統計調査」（政府統計総合窓口 e-Stat）の公表値です。より詳しい集計は <a href="/shuzen-stats/nonres/">首都圏の非住宅建築物</a> でご覧いただけます。</p>
    </div>
''' + FOOTER, encoding="utf-8")

    keep = {f"{s_}.html" for s_ in written} | {"index.html"}
    for f in sorted(out.glob("*.html")):
        if f.name not in keep:
            f.unlink()

    return len(written)


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    print(f"column/ に {build(basis)} 本 ＋ 一覧を生成しました")


if __name__ == "__main__":
    main()

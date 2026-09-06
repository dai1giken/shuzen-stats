# -*- coding: utf-8 -*-
"""都道府県別ページ（47枚）と一覧・サイトマップを生成する。

    py build_pref.py        # build.py のあとに実行する（basis.json が要る）

出力:
    pref/<ローマ字>.html    47枚
    pref/index.html         一覧
    sitemap.xml             本体＋一覧＋47枚

--- 見出し数字はストック。着工は Ref. に降りた -------------------------
以前はこのページの見出しが着工統計（フロー・分譲マンション・1988〜2001年度）で、
下部に差し込む市区町村の内訳が住宅・土地統計（ストック・非木造共同住宅・
1981〜2000年建築）だった。**同じページの上と下で、同じ東京都が5.3倍ちがっていた**
（297,723戸 と 1,578,400戸）。原因は3つ ―― ストックかフローか／分譲のみか賃貸込みか／
14年幅か20年幅か。注意書きで境目は示していたが、読者は注記より数字を先に見る。

そこで見出しをストックへ寄せ、上下を同じ統計・同じ定義に揃えた。
着工統計は「年度別の推移」というストックに出せないものを持っているので、
Ref. セクションとして残してある（3点の違いをその場に書いている）。

  ストックで載せられる … 47都道府県ぶんの現存戸数と、一都三県の市区町村の内訳。
                       同じ statsDataId=0004021796 から両方が取れる。
  ストックで失うもの   … この表には所有関係の軸が無く、絞り込めるのは
                       「非木造の共同住宅」まで。賃貸が混ざる。ページに明記すること。
  どちらでも載せられない … 工事費の指数。県別・市区町村別のデフレーターは存在しない。

市区町村別の着工統計は収録期間が短く、修繕適齢期のコホートが作れない。
だから「着工で統一する」という道は最初から無い。
"""
from __future__ import annotations

import json
from pathlib import Path

from pref_city import city_section

HERE = Path(__file__).resolve().parent
SITE_URL = "https://dai1giken.github.io/shuzen-stats/"
MONO = "IBM Plex Mono, monospace"

# ---- アクセス解析 -------------------------------------------------------
# GitHub は Pages サイトのアクセス解析を提供していない（リポジトリの
# Insights → Traffic はリポジトリの閲覧数であって、公開サイトの数字ではない）。
# だから外部の道具を入れるしかない。2つは役割が違うので両方入れる。
#
#   GSC_TOKEN … Google Search Console の所有権確認。**スクリプトを読み込まない**。
#               検索クエリ・表示回数・クリック・インデックス済みページ数が見える。
#               「検索から来ているか」に答えるのはこちら。
#   GA_ID     … Google Analytics 4 の測定ID（G- で始まる）。訪問者の行動が見える。
#               Cookie を置いて外部へ送信するので、第一技研の名前で出す以上は
#               改正電気通信事業法の外部送信規律の説明を添えること。
#
# どちらも公開して差し支えない値なので Secrets には置かない。
# **空文字なら何も出力しない。** 先に Search Console だけ入れて、GA4 は後から足せる。
GSC_TOKEN = ""
GA_ID = ""


def analytics_tags() -> str:
    """head に差し込む解析タグ。定数が空なら空文字を返す。"""
    t = []
    if GSC_TOKEN:
        t.append(f'<meta name="google-site-verification" content="{GSC_TOKEN}">')
    if GA_ID:
        t.append(f'<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>'
                 '<script>window.dataLayer=window.dataLayer||[];'
                 'function gtag(){dataLayer.push(arguments);}'
                 f"gtag('js',new Date());gtag('config','{GA_ID}');</script>")
    return ("\n" + "\n".join(t)) if t else ""

SLUG = {
    "北海道": "hokkaido", "青森県": "aomori", "岩手県": "iwate", "宮城県": "miyagi",
    "秋田県": "akita", "山形県": "yamagata", "福島県": "fukushima", "茨城県": "ibaraki",
    "栃木県": "tochigi", "群馬県": "gunma", "埼玉県": "saitama", "千葉県": "chiba",
    "東京都": "tokyo", "神奈川県": "kanagawa", "新潟県": "niigata", "富山県": "toyama",
    "石川県": "ishikawa", "福井県": "fukui", "山梨県": "yamanashi", "長野県": "nagano",
    "岐阜県": "gifu", "静岡県": "shizuoka", "愛知県": "aichi", "三重県": "mie",
    "滋賀県": "shiga", "京都府": "kyoto", "大阪府": "osaka", "兵庫県": "hyogo",
    "奈良県": "nara", "和歌山県": "wakayama", "鳥取県": "tottori", "島根県": "shimane",
    "岡山県": "okayama", "広島県": "hiroshima", "山口県": "yamaguchi", "徳島県": "tokushima",
    "香川県": "kagawa", "愛媛県": "ehime", "高知県": "kochi", "福岡県": "fukuoka",
    "佐賀県": "saga", "長崎県": "nagasaki", "熊本県": "kumamoto", "大分県": "oita",
    "宮崎県": "miyazaki", "鹿児島県": "kagoshima", "沖縄県": "okinawa",
}

CSS = """
:root{
  --ground:#EDEEE9; --surface:#F8F9F5; --sunk:#E4E6DF; --raise:#FFFFFF;
  --ink:#191D16; --ink2:#4C5348; --ink3:#7D8578;
  --rule:#D2D6CB; --rule-soft:#E2E5DC; --shu:#BE3A22; --ai:#2C5468;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --cond:"IBM Plex Sans Condensed","IBM Plex Sans",system-ui,sans-serif;
  --jp:"Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic","Yu Gothic UI",Meiryo,system-ui,sans-serif;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#151813; --surface:#1D211B; --sunk:#101310; --raise:#262B23;
  --ink:#E9EBE4; --ink2:#A8B0A3; --ink3:#767E71;
  --rule:#2F342C; --rule-soft:#242920; --shu:#E4664A; --ai:#7FB2CD;}}
:root[data-theme="dark"]{
  --ground:#151813; --surface:#1D211B; --sunk:#101310; --raise:#262B23;
  --ink:#E9EBE4; --ink2:#A8B0A3; --ink3:#767E71;
  --rule:#2F342C; --rule-soft:#242920; --shu:#E4664A; --ai:#7FB2CD;}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);font-family:var(--jp);font-size:15px;line-height:1.75;
  -webkit-font-smoothing:antialiased;
  background-image:repeating-linear-gradient(to right,var(--rule-soft) 0 1px,transparent 1px 56px),
                   repeating-linear-gradient(to bottom,var(--rule-soft) 0 1px,transparent 1px 56px)}
.wrap{max-width:920px;margin:0 auto;padding:0 24px 96px}
a{color:var(--ai);text-decoration:underline;text-underline-offset:2px;text-decoration-thickness:1px}
a:focus-visible{outline:2px solid var(--shu);outline-offset:2px}
.masthead{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 20px;border-bottom:1px solid var(--ink);padding:26px 0 10px}
a.by{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;color:var(--ink3);text-decoration:none}
a.by b{color:var(--ink);font-weight:600;font-family:var(--jp);font-size:14px;text-decoration:underline;
  text-underline-offset:4px;text-decoration-thickness:1px;text-decoration-color:var(--rule)}
a.by:hover b{color:var(--shu);text-decoration-color:var(--shu)}
.masthead .spacer{flex:1 1 100px}
.crumb{font-family:var(--mono);font-size:11.5px;color:var(--ink3)}
.srcband{margin-top:18px;border:1px solid var(--ai);border-left-width:4px;background:var(--surface);
  padding:12px 18px;font-size:12.5px;line-height:1.8;color:var(--ink2)}
.srcband b{font-family:var(--mono);font-size:10.5px;letter-spacing:.13em;color:var(--ai);display:block;margin-bottom:4px}
.srcband strong{color:var(--ink)}
.toplabel{font-family:var(--mono);font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ai);
  margin:28px 0 10px;display:block;font-weight:500}
h1{font-family:var(--cond);font-weight:700;font-size:clamp(32px,6vw,54px);line-height:1;margin:0;text-wrap:balance}
h1 .sub{display:block;font-family:var(--jp);font-weight:500;font-size:15px;line-height:1.7;color:var(--ink2);margin-top:14px;max-width:60ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1px;background:var(--rule);
  border:1px solid var(--rule);margin-top:30px}
.kpi{background:var(--surface);padding:18px 20px}
.kpi .k{font-family:var(--mono);font-size:10.5px;letter-spacing:.11em;text-transform:uppercase;color:var(--ink3)}
.kpi .v{font-family:var(--mono);font-weight:600;font-size:34px;line-height:1.15;letter-spacing:-.03em;
  font-variant-numeric:tabular-nums;margin:6px 0 4px}
.kpi .v small{font-size:14px;font-weight:500;color:var(--ink2);margin-left:3px}
.kpi.hi .v{color:var(--shu)}
.kpi p{margin:0;font-size:12.5px;line-height:1.7;color:var(--ink2)}
section{margin-top:56px}
h2{font-family:var(--cond);font-weight:600;font-size:23px;margin:0;padding-bottom:9px;border-bottom:1px solid var(--ink);
  display:flex;align-items:baseline;gap:12px;text-wrap:balance}
h2 .idx{font-family:var(--mono);font-size:12px;letter-spacing:.1em;color:var(--shu);font-weight:500;white-space:nowrap}
.lede{max-width:64ch;color:var(--ink2);margin:16px 0 0}
.chartbox{margin-top:20px;background:var(--surface);border:1px solid var(--rule);padding:18px 12px 10px;overflow-x:auto}
.chartbox{position:relative}
.chartbox svg{display:block;min-width:600px;width:100%;height:auto}
.bar{transition:opacity .12s}
.chartbox svg.hot .bar{opacity:.32}
.chartbox svg .bar.on{opacity:1}
.barhit{cursor:crosshair}
@media (prefers-reduced-motion:reduce){.bar{transition:none}}
.tip{position:absolute;pointer-events:none;background:var(--raise);border:1px solid var(--rule);border-radius:3px;
  padding:8px 11px;font-family:var(--mono);font-size:12px;line-height:1.7;color:var(--ink);white-space:nowrap;
  opacity:0;transition:opacity .1s;z-index:5;font-variant-numeric:tabular-nums;box-shadow:0 4px 14px rgba(0,0,0,.16)}
.tip.on{opacity:1}
.tip b{display:block;color:var(--ink3);font-weight:500;font-size:11px;margin-bottom:3px}
.chart-foot{font-family:var(--mono);font-size:11.5px;color:var(--ink3);padding:8px 8px 4px;
  border-top:1px solid var(--rule-soft);margin-top:6px;line-height:1.7}
.tablebox{margin-top:20px;overflow-x:auto;border:1px solid var(--rule)}
table{border-collapse:collapse;width:100%;min-width:420px;background:var(--surface);font-size:13.5px}
th,td{text-align:left;padding:10px 14px;border-bottom:1px solid var(--rule-soft)}
thead th{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink3);
  font-weight:500;background:var(--sunk);border-bottom:1px solid var(--rule)}
tbody tr:last-child td{border-bottom:0}
tr.me td{background:var(--sunk);font-weight:600}
td.n{font-family:var(--mono);font-variant-numeric:tabular-nums;text-align:right;white-space:nowrap}
.warn{margin-top:20px;border:1px solid var(--shu);border-left-width:5px;background:var(--sunk);padding:16px 20px}
.warn h4{margin:0 0 9px;font-family:var(--cond);font-weight:700;font-size:16px;color:var(--shu)}
.warn ul{margin:0;padding-left:1.15em;font-size:13px;line-height:1.9;color:var(--ink2)}
.warn strong{color:var(--ink)}
a.cta{display:flex;flex-wrap:wrap;align-items:center;gap:3px 18px;margin-top:28px;padding:20px 24px;
  text-decoration:none;border:1px solid var(--rule);border-left:5px solid var(--ai);background:var(--surface)}
a.cta:hover{background:var(--sunk);border-color:var(--ai)}
a.cta .k{width:100%;font-family:var(--mono);font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--ink3);margin-bottom:4px}
a.cta .n{font-family:var(--cond);font-weight:700;font-size:22px;color:var(--ink)}
a.cta:hover .n{color:var(--ai)}
a.cta .d{font-size:12.5px;color:var(--ink2)}
a.cta .arrow{margin-left:auto;font-family:var(--mono);font-size:20px;color:var(--ai)}
a.sitelink{display:flex;flex-wrap:wrap;align-items:center;gap:3px 18px;margin-top:20px;padding:20px 24px;
  text-decoration:none;border:1px solid var(--rule);border-left:5px solid var(--shu);background:var(--surface)}
a.sitelink:hover{background:var(--sunk);border-color:var(--shu)}
a.sitelink .k{width:100%;font-family:var(--mono);font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--ink3);margin-bottom:4px}
a.sitelink .n{font-family:var(--cond);font-weight:700;font-size:22px;color:var(--ink)}
a.sitelink:hover .n{color:var(--shu)}
a.sitelink .d{font-size:12.5px;color:var(--ink2);font-family:var(--mono)}
a.sitelink .arrow{margin-left:auto;font-family:var(--mono);font-size:20px;color:var(--shu)}
.credit{margin-top:22px;padding:14px 18px;background:var(--sunk);border-left:3px solid var(--ai);
  font-size:12.5px;line-height:1.8;color:var(--ink2)}
.colophon{margin-top:24px;font-family:var(--mono);font-size:11.5px;color:var(--ink3);line-height:1.9}
.prefgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:1px;background:var(--rule);
  border:1px solid var(--rule);margin-top:24px}
.prefgrid a{background:var(--surface);padding:12px 14px;text-decoration:none;display:flex;justify-content:space-between;
  align-items:baseline;gap:8px;color:var(--ink)}
.prefgrid a:hover{background:var(--sunk)}
.prefgrid .nm{font-size:14px}
.prefgrid .vv{font-family:var(--mono);font-size:12px;color:var(--ink3);font-variant-numeric:tabular-nums}
"""


def head(title: str, desc: str, canonical: str, crumb: str = "都道府県別") -> str:
    return f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{SITE_URL}ogp.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="canonical" href="{canonical}">{analytics_tags()}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@500;600;700&display=swap">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header class="masthead">
    <a class="by" href="https://dai1giken.co.jp/" target="_blank" rel="noopener">制作・提供　<b>株式会社第一技研</b>↗</a>
    <span class="spacer"></span>
    <span class="crumb"><a href="{SITE_URL}">大規模修繕統計ビューア</a> ／ {crumb}</span>
  </header>
"""


TIP_JS = '''<script>
(function(){
  document.querySelectorAll('.chartbox').forEach(function(box){
    var svg=box.querySelector('svg'), tip=box.querySelector('.tip');
    if(!svg||!tip) return;
    var bars=[].slice.call(svg.querySelectorAll('.bar'));
    var hits=[].slice.call(svg.querySelectorAll('.barhit'));
    if(!hits.length) return;
    function show(ev,i){
      svg.classList.add('hot');
      for(var k=0;k<bars.length;k++) bars[k].classList.toggle('on', k===i);
      tip.className='tip on';
      tip.innerHTML='<b>'+hits[i].getAttribute('data-y')+'</b>'+hits[i].getAttribute('data-v')+' 戸';
      var r=box.getBoundingClientRect();
      var left=(ev.clientX-r.left)+box.scrollLeft+14;
      if(left+tip.offsetWidth > r.width+box.scrollLeft-8) left=left-tip.offsetWidth-28;
      tip.style.left=Math.max(4+box.scrollLeft,left)+'px';
      tip.style.top=Math.max(4,(ev.clientY-r.top)-tip.offsetHeight-12)+'px';
    }
    function hide(){
      svg.classList.remove('hot');
      for(var k=0;k<bars.length;k++) bars[k].classList.remove('on');
      tip.className='tip';
    }
    hits.forEach(function(h,i){
      h.addEventListener('mousemove',function(ev){ show(ev,i); });
      h.addEventListener('touchstart',function(ev){ if(ev.touches[0]) show(ev.touches[0],i); },{passive:true});
    });
    svg.addEventListener('mouseleave',hide);
    svg.addEventListener('touchend',hide);
  });
})();
</script>
'''


FOOT = TIP_JS + f"""
  <a class="cta" href="{SITE_URL}">
    <span class="k">全国の統計へ</span>
    <span class="n">大規模修繕統計ビューア</span>
    <span class="d">工事費指数・戸あたり工事金額・修繕周期・積立金は全国共通です</span>
    <span class="arrow">→</span>
  </a>

  <a class="sitelink" href="https://dai1giken.co.jp/" target="_blank" rel="noopener">
    <span class="k">制作・提供</span>
    <span class="n">株式会社第一技研</span>
    <span class="d">マンション・ビルの外装大規模修繕　dai1giken.co.jp</span>
    <span class="arrow">→</span>
  </a>

  <p class="credit">この統計データは、政府統計総合窓口(e-Stat)のAPI機能を使用していますが、内容は国によって保証されたものではありません。<br>
  本ページの図表・数値は、出典の明記だけで自由に転載できます（CC BY 4.0）。</p>
</div>
</body>
</html>
"""


def period_chart(periods: dict[str, int], cohort: list[str]) -> str:
    """建築の時期別の住宅数。コホートの帯だけ朱で塗る。"""
    labels = list(periods)
    vals = [periods[k] for k in labels]
    n = len(labels)
    x0, x1, ytop, ybase = 96, 872, 34, 250
    ymax = max(vals) or 1
    step = 10 ** (len(str(int(ymax))) - 1)
    top = -(-ymax // step) * step
    slot = (x1 - x0) / n
    bw = slot - 10

    def Y(v):
        return ybase - v / top * (ybase - ytop)

    s = [f'<svg viewBox="0 0 900 320" role="img" aria-label="建築の時期別の非木造共同住宅数。'
         + "、".join(f"{k}は{v:,}戸" for k, v in periods.items()) + '。">']
    s.append('<g stroke="var(--rule-soft)" stroke-width="1">')
    for k in range(1, 5):
        y = ybase - (ybase - ytop) * k / 4
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
    s.append('</g>')
    s.append(f'<g font-family="{MONO}" font-size="11" fill="var(--ink3)" text-anchor="end">')
    for k in range(0, 5):
        y = ybase - (ybase - ytop) * k / 4
        s.append(f'<text x="{x0 - 9}" y="{y + 4:.1f}">{int(top * k / 4):,}</text>')
    s.append('</g>')
    s.append(f'<text x="{x0}" y="20" font-family="{MONO}" font-size="10.5" fill="var(--ink3)">戸</text>')
    s.append(f'<line x1="{x0}" y1="{ybase}" x2="{x1}" y2="{ybase}" stroke="var(--rule)"/>')

    for i, (lb, v) in enumerate(zip(labels, vals)):
        on = lb in cohort
        x = x0 + i * slot + 5
        yy = Y(v)
        s.append(f'<rect x="{x:.1f}" y="{yy:.1f}" width="{bw:.1f}" height="{ybase - yy:.1f}" rx="3" '
                 f'fill="{"var(--shu)" if on else "var(--ai)"}" opacity="{1 if on else 0.42}"/>')
        s.append(f'<text x="{x + bw/2:.1f}" y="{yy - 7:.1f}" text-anchor="middle" font-family="{MONO}" '
                 f'font-size="11.5" fill="{"var(--shu)" if on else "var(--ink3)"}">{v:,}</text>')
        s.append(f'<text x="{x + bw/2:.1f}" y="{ybase + 17}" text-anchor="middle" font-family="{MONO}" '
                 f'font-size="10.5" fill="var(--ink3)">{lb.replace("年", "").replace("～", "-")}</text>')

    s.append(f'<g font-family="{MONO}" font-size="11">')
    s.append(f'<rect x="{x0}" y="290" width="24" height="10" rx="2" fill="var(--shu)"/>')
    s.append(f'<text x="{x0 + 31}" y="299" fill="var(--ink2)">1981〜2000年建築＝2026年時点で築26〜45年</text>')
    s.append('</g></svg>')
    return "\n      ".join(s)


def year_chart(series: dict[str, int], lo: int, hi: int) -> str:
    """年度別の着工戸数。コホート期間だけ朱で塗る。"""
    years = list(series)
    vals = [series[y] for y in years]
    n = len(years)
    x0, x1, ytop, ybase = 62, 872, 34, 268
    ymax = max(vals) if max(vals) > 0 else 1
    # きりのよい上限へ
    step = 10 ** (len(str(int(ymax))) - 1)
    top = -(-ymax // step) * step
    slot = (x1 - x0) / n
    bw = slot - 3

    def Y(v):
        return ybase - v / top * (ybase - ytop)

    s = [f'<svg viewBox="0 0 900 320" role="img" aria-label="年度別の分譲マンション着工戸数。'
         f'{years[0]}から{years[-1]}まで。">']
    s.append('<g stroke="var(--rule-soft)" stroke-width="1">')
    for k in range(1, 5):
        y = ybase - (ybase - ytop) * k / 4
        s.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}"/>')
    s.append('</g>')
    s.append(f'<g font-family="{MONO}" font-size="11" fill="var(--ink3)" text-anchor="end">')
    for k in range(0, 5):
        y = ybase - (ybase - ytop) * k / 4
        s.append(f'<text x="{x0 - 9}" y="{y + 4:.1f}">{int(top * k / 4):,}</text>')
    s.append('</g>')
    s.append(f'<text x="{x0}" y="20" font-family="{MONO}" font-size="10.5" fill="var(--ink3)">戸</text>')
    s.append(f'<line x1="{x0}" y1="{ybase}" x2="{x1}" y2="{ybase}" stroke="var(--rule)"/>')

    for i, (yr, v) in enumerate(zip(years, vals)):
        y_ = int(yr[:4])
        inside = lo <= y_ <= hi
        x = x0 + i * slot + 1.5
        yy = Y(v)
        s.append(f'<rect class="bar" x="{x:.1f}" y="{yy:.1f}" width="{bw:.1f}" '
                 f'height="{ybase - yy:.1f}" rx="2" '
                 f'fill="{"var(--shu)" if inside else "var(--ai)"}" opacity="{1 if inside else 0.42}"/>')

    s.append(f'<g font-family="{MONO}" font-size="11" fill="var(--ink3)" text-anchor="middle">')
    for i, yr in enumerate(years):
        if int(yr[:4]) % 5 == 0:
            s.append(f'<text x="{x0 + i * slot + bw / 2:.1f}" y="{ybase + 18}">{yr[:4]}</text>')
    s.append('</g>')
    s.append(f'<g font-family="{MONO}" font-size="11">')
    s.append(f'<rect x="{x0}" y="292" width="24" height="10" rx="2" fill="var(--shu)"/>')
    s.append(f'<text x="{x0 + 31}" y="301" fill="var(--ink2)">{lo}〜{hi}年度＝2026年時点で築{2026-hi}〜{2026-lo}年</text>')
    s.append(f'<rect x="{x0 + 330}" y="292" width="24" height="10" rx="2" fill="var(--ai)" opacity=".42"/>')
    s.append(f'<text x="{x0 + 361}" y="301" fill="var(--ink2)">その他の年度</text>')
    s.append('</g>')

    # SVG の <title> は表示が遅く、細い棒では当たり判定も外れる。UIとして当てにしない。
    # 透明な矩形を重ねて JS で出す（本体ページの Fig.3 と同じ作り）。
    s.append('<g class="hits">')
    for i, (yr, v) in enumerate(zip(years, vals)):
        s.append(f'<rect class="barhit" x="{x0 + i * slot:.1f}" y="{ytop}" width="{slot:.1f}" '
                 f'height="{ybase - ytop}" fill="transparent" data-y="{yr}" data-v="{v:,}"/>')
    s.append('</g></svg>')
    return "\n      ".join(s)



def stock_by_pref(basis: dict) -> tuple[dict[str, int], dict[str, str], int, int]:
    """住宅・土地統計（ストック）から、都道府県別の築26〜45年の戸数を取り出す。

    返り値は (都道府県名→戸数, 都道府県名→areaコード, 全国行の値, 47県の合計)。
    全国行と47県合計は一致しない（標本調査なので）。差はページに書く。
    """
    city = basis["city"]
    areas, cohort = city["areas"], city["cohort"]

    def coh(a):
        return sum(a["periods"][k] for k in cohort)

    codes = {a["name"]: c for c, a in areas.items()
             if c.endswith("000") and c != "00000"}
    if len(codes) != 47:
        sys.exit(f"都道府県の合計行が {len(codes)} 件です（期待47件）。"
                 f"ストック表の area 軸が変わった可能性があります。")
    vals = {nm: coh(areas[c]) for nm, c in codes.items()}
    nat = coh(areas["00000"]) if "00000" in areas else 0
    return vals, codes, nat, sum(vals.values())


def build(basis: dict) -> int:
    pref = basis["prefecture"]
    units = pref["units"]                 # 着工（フロー）。副次セクションで使う
    by_year = pref["by_year"]
    lo, hi = pref["cohort"]

    city = basis["city"]
    stock, codes, nat_stock, sum47 = stock_by_pref(basis)
    national = nat_stock or sum47         # 見出し数字の母数はストックの全国値
    day = basis["generated"].split()[0]

    ranked = sorted(stock.items(), key=lambda kv: -kv[1])
    rank = {name: i + 1 for i, (name, _) in enumerate(ranked)}

    out = HERE / "pref"
    out.mkdir(exist_ok=True)
    written = []

    for name, val in ranked:
        slug = SLUG[name]
        r = rank[name]
        share = val / national * 100
        area = city["areas"][codes[name]]
        total = area["total"]
        tshare = val / total * 100 if total else 0
        flow = units[name]                       # 着工（フロー）。Ref. セクション用
        series = {k: v for k, v in by_year[name].items()}
        canonical = f"{SITE_URL}pref/{slug}.html"
        # 日本語SERPは約32字で切れる。定義は h1 と description が担う
        title = f"{name}の大規模修繕統計｜築26〜45年 {val:,}戸"
        desc = (f"{name}の非木造共同住宅のうち、1981〜2000年に建築されたものは{val:,}戸。"
                f"2026年時点で築26〜45年、大規模修繕の2〜3回目にあたります。"
                f"全国{r}位、全国の{share:.1f}%。分譲と賃貸の区別はありません。"
                f"総務省「令和5年住宅・土地統計調査」の公表値。")

        # 近隣＝順位の前後
        i = r - 1
        near = ranked[max(0, i - 2): i + 3]

        h = [head(title, desc, canonical)]
        h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて総務省「{city["survey"]}」の公表値です。</strong>
    e-Stat の API から取得し、期間の合計以外の加工はしていません。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
    なお<strong>この統計表には所有関係（分譲／賃貸）の軸がありません</strong>。
    絞り込めるのは「非木造の共同住宅」までで、賃貸マンションを含みます。
  </div>

  <span class="toplabel">総務省 公表統計 ／ 都道府県別</span>
  <h1>{name}の大規模修繕統計
    <span class="sub">{name}の非木造共同住宅のうち、<strong>1981〜2000年に建築されたものは {val:,}戸</strong>。2026年時点で築26〜45年、大規模修繕の2回目から3回目にあたります。</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">築26〜45年の非木造共同住宅</span>
      <div class="v">{val:,}<small>戸</small></div>
      <p>1981〜2000年建築。{name}の非木造共同住宅 {total:,}戸 の {tshare:.1f}%。分譲・賃貸の区別はありません。</p>
    </div>
    <div class="kpi">
      <span class="k">全国順位</span>
      <div class="v">{r}<small>位 / 47</small></div>
      <p>全国 {national:,}戸 に占める割合は {share:.1f}%。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig.</span>{name}の非木造共同住宅（建築の時期別）</h2>
    <p class="lede">2023年10月1日時点で現存する住宅の数です。朱色の2本が、2026年時点で築26〜45年にあたります。</p>
    <div class="chartbox">
      {period_chart(area["periods"], city["cohort"])}
      <div class="chart-foot">
        出典：{city["survey"]}／<a href="{city["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={city["statsDataId"]}</a><br>
        {city["filter"]}　取得日 {day}
      </div>
    </div>
  </section>

  <section>
    <h2><span class="idx">Rank</span>順位の近い都道府県</h2>
    <div class="tablebox"><table>
      <thead><tr><th>順位</th><th>都道府県</th><th>戸数</th><th>全国比</th></tr></thead>
      <tbody>''')
        for nm, vv in near:
            cls = ' class="me"' if nm == name else ''
            link = nm if nm == name else f'<a href="{SLUG[nm]}.html">{nm}</a>'
            h.append(f'<tr{cls}><td class="n">{rank[nm]}</td><td>{link}</td>'
                     f'<td class="n">{vv:,}</td><td class="n">{vv/national*100:.1f}%</td></tr>')
        h.append(f'''</tbody></table></div>
    <p class="lede"><a href="index.html">47都道府県の一覧を見る →</a></p>
  </section>
''')
        h.append(city_section(basis, name))
        h.append(f'''  <section>
    <h2><span class="idx">Ref.</span>{name}の分譲マンション着工戸数（年度別・別統計）</h2>
    <div class="srcband" style="margin-top:16px">
      <b>ここだけ別の統計です</b>
      上のストックは2023年10月1日時点の断面なので、年ごとの動きは出せません。
      年度別の推移が見られるのは<strong>国土交通省「住宅着工統計調査」</strong>のほうです。
      <strong>{lo}〜{hi}年度に{name}で着工した分譲マンションは {flow:,}戸</strong>
      （共同住宅・鉄筋コンクリート造・分譲住宅）。上の {val:,}戸 とは
      <strong>着工か現存か・分譲のみか賃貸込みか・{hi-lo+1}年幅か20年幅か</strong>の3点が違うため、
      直接は比べられません。
    </div>
    <p class="lede">朱色の期間が、2026年時点で築{2026-hi}〜{2026-lo}年にあたる住戸です。棒にカーソルを重ねると実数が出ます。</p>
    <div class="chartbox">
      {year_chart(series, lo, hi)}
      <div class="tip"></div>
      <div class="chart-foot">
        出典：国土交通省「住宅着工統計調査」時系列表／<a href="{pref["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={pref["statsDataId"]}</a><br>
        {pref["filter"]}　取得日 {day}
      </div>
    </div>
  </section>

  <div class="warn">
    <h4>この数字が指しているもの</h4>
    <ul>
      <li><strong>分譲と賃貸の区別はありません。</strong>この統計表には所有関係の軸が無く、絞り込めるのは「非木造の共同住宅」までです。賃貸マンションも含まれています。</li>
      <li><strong>標本調査にもとづく推計値です。</strong>全数調査ではありません。全国 {nat_stock:,}戸 に対し47都道府県の合計は {sum47:,}戸 で、差 {nat_stock - sum47:,}戸 があります。</li>
      <li>大規模修繕の実施周期は<strong>12〜15年程度が目安</strong>（国土交通省ガイドライン）で、築年数だけで実施時期が決まるものではありません。</li>
      <li>Ref. の着工戸数は<strong>フロー</strong>で、その後の取り壊しや用途変更は反映されていません。上のストックとは別の統計です。</li>
    </ul>
  </div>
''')
        h.append(FOOT)
        (out / f"{slug}.html").write_text("".join(h), encoding="utf-8")
        written.append(slug)

    # ---- 一覧 ----
    canonical = f"{SITE_URL}pref/"
    idx = [head("都道府県別の大規模修繕統計｜全47都道府県",
                f"築26〜45年（1981〜2000年建築）の非木造共同住宅の戸数を都道府県別に。全国{national:,}戸。"
                f"分譲と賃貸の区別はありません。総務省「令和5年住宅・土地統計調査」の公表値。",
                canonical)]
    idx.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて総務省「{city["survey"]}」の公表値です。</strong>
    e-Stat の API から取得しています。絞り込めるのは「非木造の共同住宅」までで、賃貸マンションを含みます。
  </div>

  <span class="toplabel">総務省 公表統計 ／ 都道府県別</span>
  <h1>都道府県別の大規模修繕統計
    <span class="sub">非木造共同住宅のうち1981〜2000年に建築されたもの＝2026年時点で築26〜45年の戸数を、都道府県別に並べたものです。全国では <strong>{national:,}戸</strong>。分譲と賃貸の区別はありません。</span>
  </h1>

  <div class="prefgrid">''')
    for nm, vv in ranked:
        idx.append(f'<a href="{SLUG[nm]}.html"><span class="nm">{nm}</span>'
                   f'<span class="vv">{vv:,}</span></a>')
    idx.append(f'</div>\n  <p class="colophon">単位：戸。多い順。'
               f'全国 {nat_stock:,}戸 に対し47都道府県の合計は {sum47:,}戸 で、'
               f'差 {nat_stock - sum47:,}戸 があります（標本調査のため）。</p>\n')
    idx.append(FOOT)
    (out / "index.html").write_text("".join(idx), encoding="utf-8")

    # ---- サイトマップ ----
    day = basis["generated"].split()[0]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for loc, pri in [(SITE_URL, "1.0"), (f"{SITE_URL}pref/", "0.8")]:
        sm.append(f'<url><loc>{loc}</loc><lastmod>{day}</lastmod><priority>{pri}</priority></url>')
    for slug in written:
        sm.append(f'<url><loc>{SITE_URL}pref/{slug}.html</loc><lastmod>{day}</lastmod>'
                  f'<priority>0.6</priority></url>')
    # 市区町村ページ（build_city が先に生成している前提。無ければ黙って飛ばす）
    city_dir = HERE / "city"
    if city_dir.is_dir():
        sm.append(f'<url><loc>{SITE_URL}city/</loc><lastmod>{day}</lastmod><priority>0.7</priority></url>')
        for f in sorted(city_dir.glob("*.html")):
            if f.name == "index.html":
                continue
            sm.append(f'<url><loc>{SITE_URL}city/{f.name}</loc><lastmod>{day}</lastmod>'
                      f'<priority>0.5</priority></url>')
    sm.append('</urlset>')
    (HERE / "sitemap.xml").write_text("\n".join(sm), encoding="utf-8")

    return len(written)


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    n = build(basis)
    print(f"pref/ に {n} 県 ＋ 一覧を生成、sitemap.xml も更新しました")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""都道府県別ページ（47枚）と一覧・サイトマップを生成する。

    py build_pref.py        # build.py のあとに実行する（basis.json が要る）

出力:
    pref/<ローマ字>.html    47枚
    pref/index.html         一覧
    sitemap.xml             本体＋一覧＋47枚

載せられるものと載せられないものが、はっきり分かれている。

  載せられる … 都道府県別の分譲マンション着工戸数（1988年度〜）。
               修繕適齢期のコホートを県単位で出せるのはこの表だけ。
  載せられない … 工事費の指数。県別・市区町村別のデフレーターは存在しない。
               だから県ページで言えるのは「量」だけで、「いくら」は全国共通になる。

市区町村別の着工統計は2011〜2024年しかなく、修繕適齢期のコホートが作れない。
そこで一都三県の市区町村は、着工ではなく令和5年住宅・土地統計調査（ストック）を
使っている（build_city.py）。県ページの下部にもその内訳を差し込むが、上下で
出典も定義も違うので、境目は pref_city.py が明示している。
"""
from __future__ import annotations

import json
from pathlib import Path

from pref_city import city_section

HERE = Path(__file__).resolve().parent
SITE_URL = "https://dai1giken.github.io/shuzen-stats/"
MONO = "IBM Plex Mono, monospace"

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


def head(title: str, desc: str, canonical: str) -> str:
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
<link rel="canonical" href="{canonical}">
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
    <span class="crumb"><a href="{SITE_URL}">大規模修繕統計ビューア</a> ／ 都道府県別</span>
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



def build(basis: dict) -> int:
    pref = basis["prefecture"]
    units = pref["units"]
    by_year = pref["by_year"]
    lo, hi = pref["cohort"]
    national = pref["national"]
    d = basis["deflator"]
    prim = d["series"][d["primary"]]
    sv = basis["survey"]
    factor = prim[-1] / 100.0
    third = next(r for r in sv["per_unit"] if r["label"] == "3回目以上")
    month = d["months"][-1]

    ranked = sorted(units.items(), key=lambda kv: -kv[1])
    rank = {name: i + 1 for i, (name, _) in enumerate(ranked)}

    out = HERE / "pref"
    out.mkdir(exist_ok=True)
    written = []

    for name, val in ranked:
        slug = SLUG[name]
        r = rank[name]
        share = val / national * 100
        series = {k: v for k, v in by_year[name].items()}
        canonical = f"{SITE_URL}pref/{slug}.html"
        title = f"{name}の大規模修繕統計｜修繕適齢期の分譲マンション {val:,}戸"
        desc = (f"{name}で{lo}〜{hi}年度に着工した分譲マンションは{val:,}戸。"
                f"2026年時点で築{2026-hi}〜{2026-lo}年、大規模修繕の2〜3回目にあたります。"
                f"全国{r}位、全国の{share:.1f}%。国土交通省の公表統計をそのまま並べています。")

        # 近隣＝順位の前後
        i = r - 1
        near = ranked[max(0, i - 2): i + 3]

        h = [head(title, desc, canonical)]
        h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて国土交通省の公表値です。</strong>
    住宅着工統計調査（e-Stat API）から取得し、期間の合計以外の加工はしていません。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">国土交通省 公表統計 ／ 都道府県別</span>
  <h1>{name}の大規模修繕統計
    <span class="sub">{lo}〜{hi}年度に{name}で着工した分譲マンションは <strong>{val:,}戸</strong>。2026年時点で築{2026-hi}〜{2026-lo}年、大規模修繕の2回目から3回目にあたる住戸です。</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">修繕適齢期の住戸</span>
      <div class="v">{val:,}<small>戸</small></div>
      <p>{lo}〜{hi}年度に着工した分譲マンション（共同住宅・鉄筋コンクリート造）。</p>
    </div>
    <div class="kpi">
      <span class="k">全国順位</span>
      <div class="v">{r}<small>位 / 47</small></div>
      <p>全国 {national:,}戸 に占める割合は {share:.1f}%。</p>
    </div>
    <div class="kpi">
      <span class="k">工事費の目安</span>
      <div class="v">{third["median"]*factor:.0f}<small>万円／戸</small></div>
      <p>3回目以上の中央値を{month}の物価に換算した<strong>全国値</strong>。県別の工事費指数は存在しません。</p>
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig.</span>{name}の分譲マンション着工戸数（年度別）</h2>
    <p class="lede">朱色の期間が、2026年時点で築{2026-hi}〜{2026-lo}年にあたる住戸です。棒にカーソルを重ねると実数が出ます。</p>
    <div class="chartbox">
      {year_chart(series, lo, hi)}
      <div class="tip"></div>
      <div class="chart-foot">
        出典：国土交通省「住宅着工統計調査」時系列表／<a href="{pref["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={pref["statsDataId"]}</a><br>
        {pref["filter"]}　取得日 {basis["generated"].split()[0]}
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
        h.append(f'''
  <div class="warn">
    <h4>この数字は「いま建っている数」ではありません</h4>
    <ul>
      <li><strong>着工戸数（フロー）であって、現存する住宅の数（ストック）ではありません。</strong>その後の取り壊しや用途変更は反映されていません。</li>
      <li>大規模修繕の実施周期は<strong>12〜15年程度が目安</strong>（国土交通省ガイドライン）で、築年数だけで実施時期が決まるものではありません。</li>
      <li><strong>工事費の指数は全国値しかありません。</strong>県別・市区町村別の建設工事費デフレーターは公表されていないため、金額に関する数字はすべて全国共通です。</li>
      <li>上の工事費は統計上の中央値であり、<strong>見積の目安ではありません</strong>。共通仮設費は含まれず、仕様・規模・立地・劣化状況も反映していません。</li>
    </ul>
  </div>
''')
        h.append(FOOT)
        (out / f"{slug}.html").write_text("".join(h), encoding="utf-8")
        written.append(slug)

    # ---- 一覧 ----
    canonical = f"{SITE_URL}pref/"
    idx = [head("都道府県別の大規模修繕統計｜全47都道府県",
                f"修繕適齢期（{lo}〜{hi}年度着工）の分譲マンション戸数を都道府県別に。全国{national:,}戸。国土交通省の公表統計。",
                canonical)]
    idx.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて国土交通省の公表値です。</strong>
    住宅着工統計調査（e-Stat API）から取得しています。
  </div>

  <span class="toplabel">国土交通省 公表統計 ／ 都道府県別</span>
  <h1>都道府県別の大規模修繕統計
    <span class="sub">{lo}〜{hi}年度に着工した分譲マンションの戸数を、都道府県別に並べたものです。2026年時点で築{2026-hi}〜{2026-lo}年、大規模修繕の2回目から3回目にあたります。全国では <strong>{national:,}戸</strong>。</span>
  </h1>

  <div class="prefgrid">''')
    for nm, vv in ranked:
        idx.append(f'<a href="{SLUG[nm]}.html"><span class="nm">{nm}</span>'
                   f'<span class="vv">{vv:,}</span></a>')
    idx.append('</div>\n  <p class="colophon">単位：戸。多い順。</p>\n')
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

# -*- coding: utf-8 -*-
"""他のページに置く「工事金額の分布を見る」入口バナー。

--- なぜ build_cost.py と別なのか ---------------------------------------
`build_cost.py` は `build_pref` の head()/foot() を使うので build_pref を import する。
一方、バナーは `build_pref`（都道府県ページ）にも置きたい。同じ向きで import すると
**build_pref → build_cost → build_pref の循環になる。**
バナーだけを、build_pref に依存しないこのモジュールに分けてある。

SITE_URL だけは build_pref が持っているので、**関数の中で import する**。
モジュールの先頭で import すると、結局この循環が復活する。

--- 動かすのは戸数だけ ---------------------------------------------------
自動で例示値を切り替えるが、**触った瞬間に止まる。**動いていないと機能があること
自体に気づかれないが、勝手に動き続けると操作の邪魔になる。
`prefers-reduced-motion` のときは最初から動かさない。

**築年数や年代を動かして金額を変えてはいけない。**原典の四分位は工事の回数で
分かれているだけで築年別ではないので、動かすと原典に無い相関を見せることになる。

--- そのページの戸数と繋げない -------------------------------------------
市区町村ページには「その市の非木造共同住宅ストック◯◯戸」が載っている。
**それをこのバナーに渡してはいけない。**「この市を全部直すと◯◯億円」という、
統計の読み方として成立しない数字になる。バナーの戸数は独立した例示値で、
そのことを画面に書く。
"""
from __future__ import annotations

import json

# つまみの範囲。build_cost と揃える必要があるので、向こうからここを読む。
UNIT_MIN, UNIT_MAX, UNIT_DEFAULT = 6, 300, 40

# 自動で切り替える例示値。小さめから大きめまで、戸数で金額が動くことが分かる並びにする。
DEMO_UNITS = [24, 38, 56, 80, 120]

CSS = """
/* 警告（.warn）と出典（.srcband）はどちらも「枠線だけ」で、朱は警告の色。
   同じ形にすると警告の列に埋もれるので、**このサイトで唯一の塗りつぶし**にして
   識別色を藍（--ai）にしてある。朱に戻すと .warn と見分けが付かなくなる。 */
.costban{display:block;border:1px solid var(--ai);background:var(--raise);
  margin-top:26px;text-decoration:none;color:var(--ink);overflow:hidden}
/* 見出しは藍のベタ塗り。文字色に --ground を使うのは、--ai と --ground が
   明暗どちらのテーマでも必ず反転するため（明: 濃藍地に淡文字／暗: 淡藍地に濃文字）。
   白と決め打ちすると、暗いテーマで淡い藍地に白文字になって読めない。 */
.costban .cbk{display:block;background:var(--ai);color:var(--ground);
  font-family:var(--cond);font-weight:700;font-size:12.5px;letter-spacing:.09em;
  padding:8px 18px}
.costban .cbbody{display:block;padding:18px 20px 16px}
.costban:hover .cbbody{background:var(--sunk)}
.costban .cbmain{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 14px}
.costban .cbu{font-family:var(--cond);font-weight:700;color:var(--ink);
  font-size:clamp(26px,4vw,38px);line-height:1;font-variant-numeric:tabular-nums}
.costban .cbu small{font-size:.45em;font-weight:600;margin-left:3px;color:var(--ink2)}
.costban .cbeq{color:var(--ink2);font-size:13.5px}
.costban .cbv{font-family:var(--cond);font-weight:700;color:var(--ai);
  font-size:clamp(34px,5.6vw,52px);line-height:1;font-variant-numeric:tabular-nums;
  transition:opacity .18s}
.costban .cbv.fade{opacity:.3}
.costban .cbgo{margin-left:auto;align-self:center;font-family:var(--cond);font-weight:700;
  font-size:13px;color:var(--ai);white-space:nowrap}
.costban input[type=range]{width:100%;margin-top:14px;accent-color:var(--ai);height:20px}
.costban .cbn{display:block;margin-top:10px;font-size:11.5px;line-height:1.8;color:var(--ink3)}
@media (max-width:560px){.costban .cbgo{margin-left:0;width:100%;margin-top:6px}}
@media print{.costban{display:none}}
"""

EXTRA_CSS = f"\n<style>{CSS}</style>"


def banner(basis: dict) -> str:
    """入口バナー1枚ぶんの HTML（CSS は EXTRA_CSS を head に渡すこと）。"""
    from build_pref import SITE_URL   # 循環 import を避けるため関数内で読む

    d = basis["deflator"]
    ratio = d["series"][d["primary"]][-1] / 100.0
    month = d["months"][-1]
    med = {r["label"]: r["median"] * ratio for r in basis["survey"]["per_unit"]}

    # 代表に「2回目」を使う。1回目は平均が中央値を大きく上回る（大規模・高仕様の案件が
    # 上に伸びる）ため代表値として高い側に寄り、3回目以上は最も低く出る。真ん中を取る。
    per_unit = med.get("2回目", list(med.values())[0])

    cfg = {"perUnit": per_unit, "min": UNIT_MIN, "max": UNIT_MAX,
           "demo": DEMO_UNITS, "url": SITE_URL + "cost/"}

    return f'''
  <a class="costban" href="{SITE_URL}cost/" id="costban">
    <span class="cbk">TOOL ／ 戸数から工事金額の分布を見る</span>
    <span class="cbbody">
      <span class="cbmain">
        <span class="cbu"><b id="cbu">{UNIT_DEFAULT}</b><small>戸</small></span>
        <span class="cbeq">なら、工事金額の中央値は</span>
        <span class="cbv" id="cbv">—</span>
        <span class="cbgo">くわしく見る →</span>
      </span>
      <input type="range" id="cbr" min="{UNIT_MIN}" max="{UNIT_MAX}" step="1"
        value="{UNIT_DEFAULT}" aria-label="総戸数（例示）">
      <span class="cbn">国土交通省の実態調査（2回目・{month}換算）の中央値に戸数を掛けた額です。
        <strong>共通仮設費と消費税は含みません</strong>（原典の集計定義）。実際の総額はこれより上になります。
        戸数は操作のための例で、このページに出ている戸数とは関係ありません。</span>
    </span>
  </a>
  <script>(function(){{
    var C={json.dumps(cfg, ensure_ascii=False)};
    var r=document.getElementById('cbr'),u=document.getElementById('cbu'),
        v=document.getElementById('cbv'),a=document.getElementById('costban');
    if(!r) return;
    var nf=new Intl.NumberFormat('ja-JP');
    function draw(){{
      var n=+r.value||C.min;
      u.textContent=nf.format(n);
      v.textContent=nf.format(Math.round(C.perUnit*n/10)*10)+'万円';
      a.href=C.url+'?units='+n;
    }}
    // 切り替えは「薄くする → 180ms 後に値を差し替える」の2段になっている。
    // **止めるときは予約済みの差し替えも消すこと。**interval だけ止めると、
    // つまみを掴んだ直後の 180ms に予約分が発火して、利用者の値を上書きする。
    var timer=null, pending=null;
    function stop(){{
      if(timer){{clearInterval(timer);timer=null;}}
      if(pending){{clearTimeout(pending);pending=null;}}
      v.classList.remove('fade');
    }}
    ['pointerdown','keydown','focus'].forEach(function(e){{ r.addEventListener(e,stop); }});
    // **input では stop() だけでなく draw() も呼ぶこと。**stop() だけだと、
    // つまみを動かしても金額が動かない。自動デモが裏で描画しているあいだは
    // 動いているように見えるので、デモを止めた後でしか気づけない。
    r.addEventListener('input',function(){{ stop(); draw(); }});
    // つまみの操作でリンクをたどってしまわないように既定動作を止める。
    r.addEventListener('click',function(e){{ e.preventDefault(); e.stopPropagation(); }});
    draw();
    var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if(!reduce){{
      var i=0;
      timer=setInterval(function(){{
        i=(i+1)%C.demo.length;
        v.classList.add('fade');
        pending=setTimeout(function(){{
          pending=null; r.value=C.demo[i]; draw(); v.classList.remove('fade');
        }},180);
      }},2600);
    }}
  }})();</script>
'''

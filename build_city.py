# -*- coding: utf-8 -*-
"""一都三県の市区町村別ページと一覧を生成する。

    py build_city.py        # build.py から呼ばれる（basis.json が要る）

出力: city/<JISコード>.html ／ city/index.html

--- なぜ着工統計ではなく住宅・土地統計を使うのか -------------------------
都道府県ページ（pref/）は着工統計＝フロー。その年に何戸着工したかであって、
いま何戸建っているかではない。取り壊しも用途変更も反映されない。
市区町村ページは住宅・土地統計＝ストック。現存する住宅を数えている。
**修繕の対象は現存ストックなので、こちらのほうが指標として正しい。**

--- 引き換えに失うもの ---------------------------------------------------
この表には所有関係（持ち家／借家）の軸が無い。だから見出しの数は
「非木造の共同住宅」までで、**分譲と賃貸を合わせた数**になる。
**これは誤りではない。**1棟オーナーの賃貸マンションも大規模修繕はするので、
合計は合計として意味がある。分譲とは別のものというだけ。
そこで合計は置き換えず、所有の関係の内訳を別表（0004021758）から足してある。
その別表は市区までで町村が無いので、町村のページには内訳が出ない。

--- URL にローマ字を使わない理由 -----------------------------------------
210市区町村分のローマ字表記を手で用意すると誤りが混入する。JISコードなら
一意で、市町村合併があっても追跡できる。読みやすさは title と本文で担保する。
"""
from __future__ import annotations

import json
from pathlib import Path

from build_pref import (CSS, CTA_HOUSING, SITE_URL, SLUG, age_of, cite_block,
                        head, period_chart, ref_ages)
from pref_city import MIN_UNITS, cohort_sum, label, published_leaves

HERE = Path(__file__).resolve().parent


def unit(pref_name: str) -> str:
    """東京都→「都」、北海道→「道」、大阪府→「府」、それ以外→「県」。
    ラベルを「県全体」「県内比」と決め打ちにすると東京都で誤りになる。"""
    return pref_name[-1] if pref_name[-1] in "都道府県" else "県"

BAND_JS = """  <script>
  // 築年数帯を選ぶと、階数別と所有の関係別の表を差し替える。
  // 通信も保存もしない。数字はこのページに埋め込んだ公表値だけを足し合わせる。
  // 解釈は書かない（このサイトは当社の分析・見解を載せないと宣言している）。
  (function(){
    var el = document.getElementById('bandData');
    if (!el) return;
    var D; try { D = JSON.parse(el.textContent); } catch (e) { return; }
    var floorBody = document.getElementById('floorBody'),
        ownBody   = document.getElementById('ownBody');
    if (!floorBody) return;

    var host = floorBody.closest('section');
    var pick = document.createElement('div');
    pick.className = 'bandpick';
    var opts = '<option value="">' + D.cohortLabel + '（' + D.win[0] + '〜' + D.win[1] + '年建築・既定）</option>';
    D.order.forEach(function(k){
      opts += '<option value="' + k + '">' + D.ages[k] + '（' + k + '建築）</option>';
    });
    pick.innerHTML = '<label for="band">築年数で見る</label>' +
                     '<select id="band">' + opts + '</select>' +
                     '<p class="qnote" id="bandNote"></p>';
    host.parentNode.insertBefore(pick, host);

    function fmt(n){ return n.toLocaleString('ja-JP'); }
    function sum(o, ks){ var t = 0; ks.forEach(function(k){ t += (o && o[k]) || 0; }); return t; }
    function rows(pairs, tot){
      return pairs.map(function(p){
        var pc = tot ? (p[1] / tot * 100).toFixed(1) : '0.0';
        return '<tr><td>' + p[0] + '</td><td class="n">' + fmt(p[1]) +
               '</td><td class="n">' + pc + '%</td></tr>';
      }).join('');
    }
    function apply(){
      var v = document.getElementById('band').value;
      var ks = v ? [v] : D.cohort;
      var label = v ? D.ages[v] : D.cohortLabel;
      var total = sum(D.periods, ks);

      [].forEach.call(document.querySelectorAll('.bandlab'), function(e){ e.textContent = label; });
      document.getElementById('bandNote').textContent =
        label + '（' + (v ? v : D.win[0] + '〜' + D.win[1] + '年') + '建築）の非木造共同住宅は ' + fmt(total) + ' 戸';

      var fl = D.floorOrder.map(function(f){ return [f, sum(D.floors[f], ks)]; });
      var fsum = fl.reduce(function(t, p){ return t + p[1]; }, 0);
      floorBody.innerHTML = rows(fl, fsum);
      var lede = document.getElementById('floorLede');
      if (lede) lede.textContent = '対象は ' + (v ? v : D.win[0] + '〜' + D.win[1] + '年') + '建築。';
      var gap = total - fsum;
      var fn = document.getElementById('floorNote');
      if (fn) fn.textContent = gap
        ? '階数別の合計は ' + fmt(fsum) + '戸 で、' + fmt(total) + '戸 と ' + fmt(Math.abs(gap)) +
          '戸 ちがいます。公表値が100戸単位に丸めてあるためです。'
        : '階数別の合計は ' + fmt(total) + '戸 と一致します。';

      if (ownBody && D.tenure) {
        var own = sum(D.tenure.owned, ks), tot = sum(D.tenure.total, ks);
        ownBody.innerHTML = rows([['持ち家（分譲）', own], ['持ち家以外', tot - own]], tot);
        var on = document.getElementById('ownNote');
        if (on) on.textContent = tot === total
          ? '合計 ' + fmt(tot) + '戸 は上の ' + fmt(total) + '戸 と一致します。'
          : 'この表での合計は ' + fmt(tot) + '戸 で、上の ' + fmt(total) + '戸 と ' +
            fmt(Math.abs(tot - total)) + '戸 ちがいます。';
      }
    }
    document.getElementById('band').addEventListener('change', apply);
    apply();
  })();
  </script>
"""


FOOT_T = CTA_HOUSING + """
  <a class="cta" href="{back}">
    <span class="k">都道府県の統計へ</span>
    <span class="n">{pref}の大規模修繕統計</span>
    <span class="d">{whole}の戸数と、順位の近い都道府県</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{site}#calc">
    <span class="k">Tool ／ 自分のマンションで試す</span>
    <span class="n">修繕積立金と工事費を並べる</span>
    <span class="d">戸数と積立の条件を入れると、入力した積立額と、実態調査の分布に戸数を掛けた額とを並べて表示します。見積でも、必要額の算定でも、助言でもありません</span>
    <span class="arrow">→</span>
  </a>

  <a class="cta" href="{site}">
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



def build(basis: dict) -> int:
    city = basis["city"]
    areas = city["areas"]
    cohort = city["cohort"]
    ref, age_lo, age_hi = ref_ages(basis)
    win = city["stock_window"]
    day = basis["generated"].split()[0]

    def coh(a):
        return cohort_sum(a, cohort)

    # 都県ごとに、集計行を除きページを作る市区町村だけで順位を作る。
    # 順位・近隣リンク・一覧・サイトマップを全部この結果から作る。ここを一本にしないと、
    # 閾値で落とした市区町村へのリンクが残って404になる。
    ranks: dict[str, dict[str, int]] = {}
    leaves: dict[str, list] = {}
    for pre in {c[:2] for c in areas}:
        lv = published_leaves(areas, cohort, pre)
        leaves[pre] = lv
        ranks[pre] = {c: i + 1 for i, (c, _) in enumerate(lv)}

    # ページを作る対象。集計行（特別区部・政令市）も閾値で判定する
    publish = {c for pre in leaves for c, _ in leaves[pre]}
    publish |= {c for c, a in areas.items()
                if not a["is_leaf"] and not c.endswith("000") and coh(a) >= MIN_UNITS}

    out = HERE / "city"
    out.mkdir(exist_ok=True)
    written = []

    for code, a in areas.items():
        if code.endswith("000"):          # 都県の行はページにしない（pref/ が担当）
            continue
        if code not in publish:           # 閾値未満。中身が空のページを作らない
            continue
        pre = code[:2]
        name, pref_name = label(areas, code), a["pref"]
        u = unit(pref_name)
        v = coh(a)
        total = a["total"]
        share = v / total * 100 if total else 0
        r = ranks[pre].get(code)
        pref_v = coh(areas[pre + "000"]) if pre + "000" in areas else 0
        pshare = v / pref_v * 100 if pref_v else 0
        canonical = f"{SITE_URL}city/{code}.html"
        title = f"{name}（{pref_name}）の大規模修繕統計｜築{age_lo}〜{age_hi}年 {v:,}戸"
        desc = (f"{name}の非木造共同住宅のうち、1981〜2000年に建築されたものは{v:,}戸。"
                f"{ref}年時点で築{age_lo}〜{age_hi}年、大規模修繕の2〜3回目にあたります。"
                f"総務省「令和5年住宅・土地統計調査」の公表値。")

        h = [head(title, desc, canonical, crumb="市区町村別")]
        rank_html = (f'<div class="v">{r}<small>位 / {len(leaves[pre])}</small></div>'
                     f'<p>{pref_name}の市区町村のうち。{u}全体 {pref_v:,}戸 の {pshare:.1f}%。</p>'
                     if r else
                     f'<div class="v">—</div><p>区の合計にあたる行のため、順位は付けていません。'
                     f'{u}全体 {pref_v:,}戸 の {pshare:.1f}%。</p>')

        h.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて{city["survey"]}の公表値です。</strong>
    e-Stat の API から取得し、<strong>建築の時期の区分を合計して割合を出すところまで</strong>を行っています。
    当社が独自に調べたデータ、当社の分析・見解・将来予測は<strong>含みません</strong>。
  </div>

  <span class="toplabel">公表統計 ／ {pref_name}</span>
  <h1>{name}の大規模修繕統計
    <span class="sub">{name}の非木造共同住宅のうち、<strong>{win[0]}〜{win[1]}年に建築されたものは {v:,}戸</strong>。{ref}年時点で築{age_lo}〜{age_hi}年、大規模修繕の2回目から3回目にあたります。</span>
  </h1>

  <div class="kpis">
    <div class="kpi hi">
      <span class="k">築{age_lo}〜{age_hi}年の共同住宅</span>
      <div class="v">{v:,}<small>戸</small></div>
      <p>1981〜2000年建築。{name}の非木造共同住宅 {total:,}戸 の {share:.1f}%。</p>
    </div>
    <div class="kpi">
      <span class="k">{pref_name}内の順位</span>
      {rank_html}
    </div>
  </div>

  <section>
    <h2><span class="idx">Fig.</span>{name}の非木造共同住宅（建築の時期別）</h2>
    <p class="lede">2023年10月1日時点で現存する住宅の数です。朱色の2本が、{ref}年時点で築{age_lo}〜{age_hi}年にあたります。</p>
    <div class="chartbox">
      {period_chart(a["periods"], cohort, ref)}
      <div class="chart-foot">
        出典：{city["survey"]}／<a href="{city["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={city["statsDataId"]}</a><br>
        {city["filter"]}　取得日 {day}
      </div>
    </div>
  </section>
''')

        # --- 階数別 ---------------------------------------------------------
        # 数字を並べるだけにする。「何階だからこの工法」といった読み方は
        # 当社の見解であって公表値ではない。このページは公表値だけを載せると
        # 上のSOURCE欄で宣言しているので、解釈は書かない。
        fl = a.get("floors") or {}
        if sum(fl.values()):
            fsum = sum(fl.values())
            rows = "".join(
                f'<tr><td>{k}</td><td class="n">{fl[k]:,}</td>'
                f'<td class="n">{fl[k] / fsum * 100:.1f}%</td></tr>'
                for k in city["floor_order"] if k in fl)
            gap = v - fsum
            # 両方とも100戸単位に丸めた公表値なので、合計は一致しないことがある。
            # 黙って揃えたり、どちらかを書き換えたりしない。
            note = (f'階数別の合計は {fsum:,}戸 で、上の {v:,}戸 と {abs(gap):,}戸 ちがいます。'
                    '公表値が100戸単位に丸めてあるためです。' if gap else
                    f'階数別の合計は上の {v:,}戸 と一致します。')
            h.append(f'''  <section>
    <h2><span class="idx">Floor</span>{name}の<span class="bandlab">築{age_lo}〜{age_hi}年</span>（階数別）</h2>
    <p class="lede">非木造共同住宅を建物の階数で分けたものです。<span id="floorLede">対象は上と同じ {win[0]}〜{win[1]}年建築。</span></p>
    <div class="tablebox"><table>
      <thead><tr><th>階数</th><th>戸数</th><th>構成比</th></tr></thead>
      <tbody id="floorBody">{rows}</tbody>
    </table></div>
    <p class="colophon">単位：戸。出典：{city["survey"]}／<a href="{city["url"]}" target="_blank" rel="noopener">e-Stat statsDataId={city["statsDataId"]}</a>（上の数字と同じ表）。<span id="floorNote">{note}</span></p>
  </section>
''')

        # --- 所有の関係別 ---------------------------------------------------
        # 見出しの数（分譲と賃貸の合計）は置き換えない。1棟オーナーの賃貸マンションも
        # 大規模修繕はするので、合計が誤りなのではなく分譲とは別のものというだけ。
        # 内訳は別表から取る。**別表どうしを引き算しない**（丸め差が賃貸の戸数に化ける）
        # ため、合計もその表から取ってある。実測では227件すべて見出しと一致した。
        ten = a.get("tenure")
        tn = city.get("tenure", {})
        if ten and ten.get("total"):
            own, tot_t = ten["owned"], ten["total"]
            other = tot_t - own
            rows = "".join(
                f'<tr><td>{k}</td><td class="n">{x:,}</td>'
                f'<td class="n">{x / tot_t * 100:.1f}%</td></tr>'
                for k, x in [("持ち家（分譲）", own), ("持ち家以外", other)])
            same = ("上の {:,}戸 と一致します。".format(v) if tot_t == v
                    else "この表での合計は {:,}戸 で、上の {:,}戸 と {:,}戸 ちがいます。"
                         .format(tot_t, v, abs(tot_t - v)))
            h.append(f'''  <section>
    <h2><span class="idx">Own</span>{name}の<span class="bandlab">築{age_lo}〜{age_hi}年</span>（所有の関係別）</h2>
    <p class="lede">同じ調査の別の統計表から。「持ち家」は住戸ごとに所有者がいるもの、「持ち家以外」は借りて住んでいるものです。</p>
    <div class="tablebox"><table>
      <thead><tr><th>所有の関係</th><th>戸数</th><th>構成比</th></tr></thead>
      <tbody id="ownBody">{rows}</tbody>
    </table></div>
    <p class="colophon">単位：戸。出典：{city["survey"]}／<a href="{tn.get("url", "")}" target="_blank" rel="noopener">e-Stat statsDataId={tn.get("statsDataId", "")}</a>。{tn.get("filter", "")}　取得日 {day}。<span id="ownNote">合計 {tot_t:,}戸 は{same}</span></p>
  </section>
''')
        else:
            h.append(f'''  <section>
    <h2><span class="idx">Own</span>{name}の築{age_lo}〜{age_hi}年（所有の関係別）</h2>
    <p class="lede">所有の関係（持ち家か、そうでないか）の内訳は、同じ調査の別の統計表
    （<a href="{tn.get("url", "")}" target="_blank" rel="noopener">statsDataId={tn.get("statsDataId", "")}</a>）にありますが、
    <strong>その表は市区までで、町村は収録されていません</strong>。{name}はこれに当たるため、内訳を出していません。</p>
  </section>
''')

        # --- 築年数帯の切り替え -----------------------------------------
        # 上の2つの表は既定で築26〜45年ぶん。JS があるときだけ、帯を選べる
        # ようにする。**選択肢を出すのも JS 側**にしてあるので、JS が無効なら
        # 既定の表がそのまま残り、空のセレクトが出て壊れて見えることがない。
        # データはこの市区町村ぶんだけを埋め込む（通信しない）。
        band = {
            "order": city["order"],
            "ages": {k: age_of(k, ref) for k in city["order"]},
            "cohort": cohort,
            "cohortLabel": f"築{age_lo}〜{age_hi}年",
            "win": win,
            "floorOrder": city["floor_order"],
            "periods": a["periods"],
            "floors": a.get("floors_by_period") or {},
            "tenure": a.get("tenure_by_period"),
        }
        h.append('  <script id="bandData" type="application/json">'
                 + json.dumps(band, ensure_ascii=False) + '</script>' + chr(10))
        h.append(BAND_JS)

        if r:
            i = r - 1
            near = leaves[pre][max(0, i - 2): i + 3]
            h.append(f'''  <section>
    <h2><span class="idx">Rank</span>{pref_name}内で順位の近い市区町村</h2>
    <div class="tablebox"><table>
      <thead><tr><th>順位</th><th>市区町村</th><th>築{age_lo}〜{age_hi}年</th><th>{u}内比</th></tr></thead>
      <tbody>''')
            for c2, a2 in near:
                cls = ' class="me"' if c2 == code else ''
                v2 = coh(a2)
                nm2 = (label(areas, c2) if c2 == code
                       else f'<a href="{c2}.html">{label(areas, c2)}</a>')
                h.append(f'<tr{cls}><td class="n">{ranks[pre][c2]}</td><td>{nm2}</td>'
                         f'<td class="n">{v2:,}</td><td class="n">{v2/pref_v*100:.1f}%</td></tr>')
            h.append('</tbody></table></div>\n    <p class="lede"><a href="index.html">'
                     '一都三県の市区町村一覧を見る →</a></p>\n  </section>\n')

        h.append(f'''  <div class="warn">
    <h4>この数字が指しているもの</h4>
    <ul>
      <li><strong>見出しの戸数は、分譲と賃貸を合わせた数です。</strong>この統計表で絞り込めるのは「非木造の共同住宅」までで、賃貸マンションを含みます。持ち家かどうかの内訳は、上の「所有の関係別」に別の統計表から載せています（その表は市区までで、町村はありません）。</li>
      <li><strong>標本調査にもとづく推計値です。</strong>全数調査ではありません。また小規模な町村は個別に公表されないため、市区町村の合計は{u}の値と一致しません（一都三県で0.1〜0.5%の差）。</li>
      <li>大規模修繕の実施周期は<strong>12〜15年程度が目安</strong>（国土交通省ガイドライン）で、築年数だけで実施時期が決まるものではありません。</li>
    </ul>
  </div>
''')
        h.append(cite_block(canonical, day))
        h.append(FOOT_T.format(back=f"../pref/{SLUG[pref_name]}.html", pref=pref_name,
                               whole=f"{u}全体", site=SITE_URL))
        (out / f"{code}.html").write_text("".join(h), encoding="utf-8")
        written.append(code)

    # ---- 一覧 ----
    canonical = f"{SITE_URL}city/"
    idx = [head("一都三県の市区町村別 大規模修繕統計",
                f"東京・神奈川・埼玉・千葉の市区町村別に、築{age_lo}〜{age_hi}年の非木造共同住宅の戸数を並べています。"
                "総務省「令和5年住宅・土地統計調査」の公表値。",
                canonical, crumb="市区町村別")]
    idx.append(f'''  <div class="srcband">
    <b>SOURCE ／ 出典</b>
    <strong>このページの数値は、すべて{city["survey"]}の公表値です。</strong>
  </div>

  <span class="toplabel">公表統計 ／ 一都三県</span>
  <h1>一都三県の市区町村別
    <span class="sub">非木造共同住宅のうち{win[0]}〜{win[1]}年に建築されたもの＝{ref}年時点で築{age_lo}〜{age_hi}年の戸数です。分譲と賃貸を合わせた数で、各ページに所有の関係別の内訳を載せています。</span>
  </h1>

  <div class="finder">
    <label for="q">市区町村をさがす</label>
    <input type="search" id="q" autocomplete="off" placeholder="例：江東　世田谷　川崎　浦安"
           aria-describedby="qnote" aria-controls="qlist">
    <p id="qnote" class="qnote" role="status" aria-live="polite"></p>
  </div>
  <div id="qlist">
''')
    for pre in ["13", "14", "11", "12"]:
        if pre not in leaves:
            continue
        pname = basis["city"]["areas"][pre + "000"]["pref"]
        idx.append(f'<section><h2><span class="idx">{pname}</span>'
                   f'{len(leaves[pre])} 市区町村</h2>\n  <div class="prefgrid">')
        for c2, a2 in leaves[pre]:
            idx.append(f'<a href="{c2}.html"><span class="nm">{label(areas, c2)}</span>'
                       f'<span class="vv">{coh(a2):,}</span></a>')
        # 集計行（特別区部・政令市）は市区町村と二重に数えるので順位一覧には入れられないが、
        # ページ自体は作っている。ここに出さないと内部リンクゼロのまま sitemap にだけ載る。
        # 横浜市 390,900戸 はこのサイトで最大の単位で、それが孤立していた。
        rolls = sorted((c2 for c2 in areas
                        if c2[:2] == pre and not areas[c2]["is_leaf"]
                        and not c2.endswith("000") and c2 in publish),
                       key=lambda c2: -coh(areas[c2]))
        if rolls:
            idx.append('</div>\n  <p class="colophon">集計行（順位は付けていません）：'
                       + "　".join(f'<a href="{c2}.html">{areas[c2]["name"]}</a> {coh(areas[c2]):,}'
                                   for c2 in rolls)
                       + '</p></section>\n')
        else:
            idx.append('</div></section>\n')
    idx.append('  </div>\n')
    idx.append(f'  <p class="colophon">単位：戸。多い順。'
               f'<strong>築{age_lo}〜{age_hi}年の非木造共同住宅が {MIN_UNITS:,}戸 以上の市区町村だけ</strong>を'
               f'載せています（それ未満は個別ページを作っていません）。'
               f'特別区部・政令市の集計行は、市区町村と二重に数えることになるので'
               f'順位の一覧からは外し、各県の下に別途置いています。</p>\n')
    idx.append('''  <script>
  // 入力を端末の外へ出さない。fetch も localStorage も使わず、
  // すでにページにある173件のリンクを絞り込むだけ。JS が無効なら全件が出たまま。
  (function(){
    var q = document.getElementById('q'), note = document.getElementById('qnote');
    if (!q) return;
    var cells = [].slice.call(document.querySelectorAll('#qlist .prefgrid a'));
    var secs  = [].slice.call(document.querySelectorAll('#qlist section'));
    var total = cells.length;
    function apply(){
      var v = q.value.trim();
      var hit = 0;
      cells.forEach(function(a){
        var nm = a.querySelector('.nm');
        var on = !v || (nm && nm.textContent.indexOf(v) >= 0);
        a.hidden = !on;
        if (on) hit++;
      });
      secs.forEach(function(sec){
        var any = [].slice.call(sec.querySelectorAll('.prefgrid a')).some(function(a){ return !a.hidden; });
        // 集計行の段落だけが残った県は、見出しごと隠す
        sec.hidden = !any;
      });
      note.textContent = !v ? '' :
        (hit ? hit + ' 件' : '該当なし。市区町村名の一部を漢字で入れてください（例：江東）');
    }
    q.addEventListener('input', apply);
    apply();
  })();
  </script>
''')
    idx.append(cite_block(canonical, day))
    idx.append(FOOT_T.format(back="../pref/", pref="都道府県別",
                             whole="都道府県全体", site=SITE_URL))
    (out / "index.html").write_text("".join(idx), encoding="utf-8")

    # 閾値から外れたページを消す。ここをやらないと、ディスクに残ったファイルを
    # ワークフローの `cp -r pref city _site/` が公開し続け、
    # build_pref.py の sitemap 生成（city/*.html を glob する）が載せ続ける。
    keep = {f"{c}.html" for c in written} | {"index.html"}
    stale = sorted(p for p in out.glob("*.html") if p.name not in keep)
    for p in stale:
        p.unlink()
    if stale:
        print(f"  閾値 {MIN_UNITS:,}戸 未満のため削除: {len(stale)} 枚 "
              f"（{'、'.join(p.stem for p in stale[:5])}…）")

    return len(written)


def main() -> None:
    basis = json.loads((HERE / "basis.json").read_text(encoding="utf-8"))
    print(f"city/ に {build(basis)} ページ ＋ 一覧を生成しました")


if __name__ == "__main__":
    main()

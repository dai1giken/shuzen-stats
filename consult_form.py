# -*- coding: utf-8 -*-
"""統計ページの中に置く、短い相談フォーム。

--- なぜ /consultation/ のコピーではないのか -----------------------------
相談ページは**企業サイト側**のページで、企業サイトの `styles.css`（`cs-*`）で
できている。統計サイト（/shuzen-stats/）にそのまま貼ると CSS を丸ごと持ち込む
ことになり、**毎月の ZIP で企業サイトの CSS を上書きする事故**につながる
（README_内部.md の警告）。ここでは統計サイトの変数だけを使って、
**同じ契約の短い版**を作る。

--- 契約は変えない（最重要）---------------------------------------------
送信先は既存の `/contact.php`。POST する項目は**いまと同じ6つだけ**。

    company / name / email / tel / message / website（bot対策の空欄）

案件の条件には **`name` 属性を付けない。**付けると contact.php に未知の項目が
飛んで、サーバ側の挙動が変わりうる。条件は JS が `message` に組み立てるだけ。
**この方針は build_consultation.py と同じ。片方だけ変えないこと。**

--- 本番以外からは送らない ----------------------------------------------
`location.hostname === 'dai1giken.co.jp'` のときだけ action を残す。
**テスト用のホスト（GitHub Pages・localhost）から送ると本物の問い合わせが飛ぶ。**
それ以外では POST の中身を画面に出すだけにする（build_consultation と同じ）。

--- 対応エリア -----------------------------------------------------------
一都三県のみ。**それ以外の都道府県ページには置かない。**
判定は呼ぶ側（build_pref）が持つ。ここではしない。

--- 概算を本文に載せるときの但し書き ------------------------------------
上のツールで出した金額を本文に入れる。**「当社のお見積りではありません」を
必ず同じ本文に入れること。**入れないと、転送された先で当社が出した金額として
読まれる。

--- id は1ページに1組 ----------------------------------------------------
`contact-form` `cfMsg` などを JS が直接引く。**1ページに2つ置かない。**
"""
from __future__ import annotations

import json

CONTACT_ACTION = "/contact.php"

CSS = """
/* 統計と営業の境目をページに明示する。統計サイトの価値は「公表値だけ」と
   言い切れることなので、**この帯を消さないこと。** */
.bizband{margin-top:26px;padding:7px 14px;border:1px solid var(--rule);
  background:var(--sunk);font-family:var(--cond);font-weight:600;font-size:11.5px;
  letter-spacing:.05em;color:var(--ink3)}
.bizband b{color:var(--ink2);font-weight:700;margin-right:10px}
.cf{border:1px solid var(--rule);border-top:0}
.cf > summary{list-style:none;cursor:pointer;display:block;padding:16px 18px;background:var(--raise)}
.cf > summary::-webkit-details-marker{display:none}
.cf > summary:hover{background:var(--sunk)}
.cf .cfk{display:block;font-family:var(--cond);font-weight:700;font-size:15px;color:var(--ink)}
.cf .cfd{display:block;margin-top:5px;font-size:12.5px;line-height:1.8;color:var(--ink2)}
.cf .cfgo{display:inline-block;margin-top:11px;font-family:var(--cond);font-weight:700;font-size:13px;
  color:var(--ai);border:1px solid var(--ai);border-radius:999px;padding:7px 16px;
  transition:background .15s,color .15s}
.cf > summary:hover .cfgo{background:var(--ai);color:var(--ground)}
.cf[open] > summary .cfgo{display:none}
.cf-in{padding:4px 18px 20px;border-top:1px solid var(--rule)}
.cf-f{display:block;margin-top:16px}
.cf-f > span.l{display:block;font-family:var(--cond);font-weight:600;font-size:12.5px;
  color:var(--ink3);letter-spacing:.04em;margin-bottom:6px}
.cf-f .req{color:var(--shu);font-weight:700;margin-left:7px}
.cf-f .opt{color:var(--ink3);font-weight:400;margin-left:7px}
.cf-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:0 16px}
.cf input[type=text],.cf input[type=email],.cf input[type=tel],.cf select,.cf textarea{
  width:100%;box-sizing:border-box;font:inherit;font-size:14px;padding:8px 10px;
  background:var(--surface);color:var(--ink);border:1px solid var(--rule);border-radius:2px}
.cf textarea{font-size:13px;line-height:1.85;resize:vertical}
.cf input:focus-visible,.cf select:focus-visible,.cf textarea:focus-visible{outline:2px solid var(--ai);outline-offset:1px}
.cf-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(178px,1fr));gap:1px;
  background:var(--rule);border:1px solid var(--rule)}
.cf-grid label{display:flex;align-items:center;gap:7px;background:var(--surface);
  padding:8px 11px;font-size:13px;cursor:pointer}
.cf-grid label:hover{background:var(--sunk)}
.cf-sum{margin-top:16px;border:1px solid var(--ai);background:var(--sunk);padding:11px 14px;
  font-size:12.5px;line-height:1.85;color:var(--ink2)}
.cf-sum b{display:block;font-family:var(--cond);font-size:11.5px;letter-spacing:.06em;
  color:var(--ai);margin-bottom:4px}
.cf-sum .v{font-family:var(--mono);font-variant-numeric:tabular-nums;color:var(--ink)}
.cf-hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.cf-send{margin-top:18px;font-family:var(--cond);font-weight:700;font-size:14.5px;padding:12px 26px;
  background:var(--ai);color:var(--ground);border:1px solid var(--ai);border-radius:2px;cursor:pointer}
.cf-send:hover{opacity:.88}
.cf-rb{margin-top:8px;font-family:var(--cond);font-size:12px;padding:6px 12px;background:var(--surface);
  color:var(--ink2);border:1px solid var(--rule);border-radius:2px;cursor:pointer}
.cf-note{margin:12px 0 0;font-size:11.5px;line-height:1.85;color:var(--ink3)}
.cf-pre{margin-top:14px;padding:12px;background:var(--sunk);border:1px solid var(--rule);
  font-family:var(--mono);font-size:11.5px;white-space:pre-wrap;color:var(--ink2)}
@media print{.cf,.bizband{display:none!important}}
"""

EXTRA_CSS = "\n<style>" + CSS + "</style>"


def _boxes(items: list[str], group: str, kind: str = "checkbox") -> str:
    """条件の選択肢。**name 属性を付けない**（contact.php の契約を変えないため）。"""
    return "".join(
        f'<label><input type="{kind}" data-cf="{group}" value="{v}">{v}</label>'
        for v in items)


def form(*, page_url: str, page_title: str, region: str = "",
         city: str = "", open_: bool = False) -> str:
    """相談フォーム1枚ぶんの HTML（CSS は EXTRA_CSS を head に渡すこと）。

    region / city はその地域ページの初期値。入れておくと利用者が選び直す手間が減る。
    **上のツールの戸数と金額は渡さない。**JS が実行時に読む。ビルド時に埋め込むと、
    つまみを動かしても本文が既定値のまま残る。
    """
    # 語彙は相談ページと共有する。**2箇所に書かない。**
    # モジュールの先頭で import すると build_pref → consult_form →
    # build_consultation → build_pref の循環になるので、関数の中で読む。
    from build_consultation import CONSULT_URL, REGIONS, TIMING, TRADES

    cfg = {"action": CONTACT_ACTION, "url": page_url, "title": page_title}
    op = " open" if open_ else ""
    regions = "".join(
        f'<option{" selected" if r == region else ""}>{r}</option>' for r in REGIONS)
    timings = "".join(f"<option>{t}</option>" for t in TIMING)
    return f'''
  <div class="bizband"><b>当社のご案内</b>ここから下は株式会社第一技研からのご案内です。公表統計ではありません。</div>
  <details class="cf"{op}>
    <summary>
      <span class="cfk">お見積りをご希望の場合は、この条件のままご相談いただけます</span>
      <span class="cfd">上の金額は<strong>公表統計に戸数を掛けた数字で、お見積りではありません</strong>。実際の金額は建物の劣化状況と仕様で決まります。上で選んだ戸数と金額は、そのままご相談の本文に入ります。対応エリアは東京・神奈川・埼玉・千葉です。</span>
      <span class="cfgo">この条件で相談する（このページで送信できます）→</span>
    </summary>
    <div class="cf-in">
      <form id="contact-form" action="{CONTACT_ACTION}" method="post">
        <div class="cf-sum"><b>ご相談に入る内容（上のツールの状態）</b><span id="cfSumV">—</span></div>

        <div class="cf-row">
          <label class="cf-f"><span class="l">所在地<span class="opt">任意</span></span>
            <select id="cfRegion"><option value="">選んでください</option>{regions}</select>
          </label>
          <label class="cf-f"><span class="l">市区町村<span class="opt">任意</span></span>
            <input type="text" id="cfCity" maxlength="60" value="{city}" placeholder="例：文京区" autocomplete="off">
          </label>
        </div>

        <div class="cf-f"><span class="l">希望する工事<span class="opt">任意・複数選べます</span></span>
          <div class="cf-grid">{_boxes(TRADES, "trade")}</div>
        </div>

        <label class="cf-f"><span class="l">希望する時期<span class="opt">任意</span></span>
          <select id="cfTiming"><option value="">選んでください</option>{timings}</select>
        </label>

        <label class="cf-f"><span class="l">お問い合わせ内容<span class="req">必須</span></span>
          <textarea name="message" id="cfMsg" rows="12" required></textarea>
        </label>
        <button type="button" class="cf-rb" id="cfRb" hidden>選んだ条件から本文を作り直す</button>

        <div class="cf-row">
          <label class="cf-f"><span class="l">会社名・団体名<span class="opt">任意</span></span>
            <input type="text" name="company" autocomplete="organization"></label>
          <label class="cf-f"><span class="l">お名前<span class="req">必須</span></span>
            <input type="text" name="name" autocomplete="name" required></label>
        </div>
        <div class="cf-row">
          <label class="cf-f"><span class="l">メールアドレス<span class="req">必須</span></span>
            <input type="email" name="email" autocomplete="email" required></label>
          <label class="cf-f"><span class="l">電話番号<span class="opt">任意</span></span>
            <input type="tel" name="tel" autocomplete="tel"></label>
        </div>

        <div class="cf-hp" aria-hidden="true"><label>このフィールドは空欄のままにしてください
          <input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>

        <button type="submit" class="cf-send">この内容で相談する</button>
        <p class="cf-note">送信内容は既存のお問い合わせ窓口に届きます。<strong>金額・工期・施工の可否は、現地または資料を確認のうえ担当者よりご案内します。この画面で確約するものではありません。</strong>建物の用途や所有形態も含めて詳しく選べる<a href="{CONSULT_URL}">案件のご相談ページ</a>もあります。</p>
        <pre class="cf-pre" id="cfPre" hidden></pre>
      </form>
    </div>
  </details>
  <script id="cf-data" type="application/json">{json.dumps(cfg, ensure_ascii=False)}</script>
  <script>{JS}</script>
'''


# JS は f-string にしない。**`function(){` の波括弧を全部 `{{` に書き換える必要が
# 出て、1つ抜けただけで黙って壊れる。**値は cf-data から読む（build_consultation
# と同じ作り）。
JS = r"""
(function(){
  'use strict';
  var C = JSON.parse(document.getElementById('cf-data').textContent);
  var $ = function(id){ return document.getElementById(id); };
  var form = $('contact-form'), msg = $('cfMsg');
  if(!form || !msg) return;
  var touched = false;               /* 利用者が本文を触ったら自動で上書きしない */
  var nf = new Intl.NumberFormat('ja-JP');

  /* 上のツールの状態を**実行時に**読む。ビルド時に埋め込むと、つまみを動かしても
     本文が既定値のまま残る。ツールが無いページでも落ちないよう null を返す。 */
  function tool(){
    var u = $('iUnits'), s = $('oSel'), a = $('oSelAmt');
    if(!u || !s || !a) return null;
    return { units: +u.value || 0, sel: s.textContent, amt: a.textContent };
  }
  function picked(g){
    return [].slice.call(document.querySelectorAll('[data-cf="' + g + '"]:checked'))
             .map(function(e){ return e.value; });
  }
  function compose(){
    var t = tool();
    var region = $('cfRegion').value, city = $('cfCity').value.trim();
    var trades = picked('trade'), timing = $('cfTiming').value;
    var L = ['大規模修繕のお見積りについて、ご相談したく連絡しました。', '', '【案件の条件】'];
    if(region) L.push('所在地：' + region + (city ? ' ' + city : ''));
    if(t && t.units) L.push('総戸数：' + nf.format(t.units) + '戸');
    if(trades.length) L.push('希望する工事：' + trades.join('、'));
    if(timing) L.push('希望する時期：' + timing);
    if(L.length === 3) L.push('（まだ決まっていません。相談しながら整理したいです。）');
    if(t){
      L.push('', '【統計ページで見た概算】', C.title, C.url,
             t.sel + ' ＝ ' + t.amt + '（税抜）');
      /* **この2行を外さないこと。**転送された先で、当社が出した金額として読まれる。 */
      L.push('※国土交通省の実態調査の値に戸数を掛けた統計値で、当社のお見積りではありません。');
      L.push('※共通仮設費・消費税・設計コンサルタント業務の費用は含まれていません。');
    }
    L.push('', '【ご相談の内容】', '');
    return L.join('\n');
  }
  function summary(){
    var t = tool();
    var box = $('cfSumV');
    if(t){
      box.replaceChildren();
      var v = document.createElement('span');
      v.className = 'v';
      v.textContent = t.sel + ' ＝ ' + t.amt + '（税抜）';
      box.appendChild(v);
    } else {
      box.textContent = '上のツールで戸数と金額を選ぶと、ここに入ります。';
    }
  }
  function refresh(){
    summary();
    if(!touched) msg.value = compose();
  }

  /* ツールの操作（つまみ・表のセル・階数・範囲）はどれも input/change/click で
     起きる。個別に繋ぐとツールを直したときに片方だけ古くなるので、文書ごと拾う。
     **capture で拾うこと。**ツール側が再描画でボタンを作り直すため、
     個々の要素に後から付けたリスナーは消える。 */
  ['input', 'change', 'click'].forEach(function(ev){
    document.addEventListener(ev, function(e){
      if(e.target === msg) return;
      refresh();
    }, true);
  });
  msg.addEventListener('input', function(){ touched = true; $('cfRb').hidden = false; });
  $('cfRb').addEventListener('click', function(){
    touched = false; $('cfRb').hidden = true; refresh(); msg.focus();
  });

  /* **本番以外からは送らない。**テストのホストから送ると本物の問い合わせが飛ぶ。 */
  if(location.hostname !== 'dai1giken.co.jp'){
    form.removeAttribute('action');
    form.addEventListener('submit', function(e){
      e.preventDefault();
      if(!form.reportValidity()) return;
      var fd = new FormData(form), lines = [];
      fd.forEach(function(v, k){ if(k !== 'website') lines.push(k + ': ' + v); });
      var pre = $('cfPre');
      pre.hidden = false;
      pre.textContent = 'POST ' + C.action + '\n\n' + lines.join('\n');
      pre.scrollIntoView({ block: 'center' });
    });
  }
  refresh();
  /* **ツールの JS より先に走ることがある。**そのときは oSel がまだ「—」なので、
     読み込み完了後にもう一度作り直す。これを外すと、ページによってまとめ欄が
     「— ＝ —」のまま残る（/cost/ で実際に起きた）。 */
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', refresh);
  }
})();
"""

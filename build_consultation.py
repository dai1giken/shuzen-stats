# -*- coding: utf-8 -*-
"""企業サイト（dai1giken.co.jp）の案件相談ページを生成する。

    py build_consultation.py      # build.py から呼ばれる

出力: consultation/index.html

--- 置き場所 -------------------------------------------------------------
生成先は企業サイトの htdocs/consultation/。`column/` と同じ企業サイト側で、
統計サイト（/shuzen-stats/）とは別。**統計サイトは公表値だけ、こちらは
当社のサービス。**性格が違うので分けている。

--- 既存フォームの契約を変えない（最重要）-------------------------------
送信先は既存の `/contact.php`。POST される項目は**いまと同じ6つだけ**にする。

    company / name / email / tel / message / website（bot対策の空欄）

案件の条件を選ぶ入力には **`name` 属性を付けていない**。付けると
contact.php が知らない項目が飛んで、サーバ側の挙動が変わりうる。
条件は JavaScript が読んで `message` の本文に組み立てるだけ。
**条件の入力に name を足さないこと。**足した瞬間に契約が変わる。

--- コピー＆貼り付けをやめた --------------------------------------------
前案は「相談文をコピー → 公式フォームに貼る」だったが、**問い合わせを
気軽にするのが目的なのに手数が増えている。**このページに連絡先欄まで置き、
1ページ・1回の送信で終わるようにした。sessionStorage の引き継ぎも不要。

--- 公開実績の照合は載せない --------------------------------------------
前案には「関連する公開実績」があったが外した。実績は企業サイトの
`/#works` に52件の一覧があり、**そちらが一次情報**。相談ページに
抜粋を持つと二重管理になり、片方だけ古くなる。
用途が近い実績へは `/#works` へのリンクで案内する。

--- 書いてよいこと ------------------------------------------------------
対応できる工種と、相談時に用意があると早い資料まで。
**金額・工期・施工可否は書かない。**担当者が現地と資料を見てから決めること。
"""
from __future__ import annotations

import json
from pathlib import Path

from build_pref import analytics_tags

HERE = Path(__file__).resolve().parent

# 本番（dai1giken.co.jp/consultation/）へ出すまでは False。
#   False … <meta robots noindex> を付け、ホスト直下のサイトマップに載せない
#   True  … noindex を外し、サイトマップに載せる
# **GitHub Pages のテスト版が検索に載ると、本番と重複したまま先に拾われる。**
# v1.1 で github.io の重複が実際に問題になったので、出すまでは noindex。
PUBLISH = False

CANONICAL = "https://dai1giken.co.jp/consultation/"

# 企業サイトの共有資産（styles.css・ロゴ・ナビの遷移先）をどこから読むか。
#
#   本番 htdocs/consultation/  … 親が企業サイトのルートなので "../" でよい
#   GitHub Pages のテスト      … 親は /shuzen-stats/ で**企業サイトではない**。
#                                 "../" だと CSS もロゴもナビも全部外れる
#
# テストのときだけ本番の絶対URLを読む。**見た目を本番と同じにしたまま、
# ファイルを1つもコピーしない。**企業サイトの styles.css を repo に持ち込むと、
# 毎月のZIPで本番のCSSを上書きする事故につながる（README_内部.md の警告）。
BASE = "../" if PUBLISH else "https://dai1giken.co.jp/"

# 建物の用途。企業サイトの実績フィルタは「商用・公共施設／集合・個人住宅」の
# 2区分だが、相談では担当者が知りたい粒度が違うのでこちらは細かくする。
USES = [
    ("集合住宅", "マンション・アパート・社宅・寮"),
    ("オフィス・商業ビル", "事務所・店舗・複合ビル"),
    ("工場・倉庫", "生産施設・物流施設"),
    ("学校・研究施設", "校舎・体育館・研究棟"),
    ("医療・介護施設", "病院・診療所・介護施設"),
    ("その他・未定", "上記以外、または決まっていない"),
]

# 集合住宅のときだけ聞く。所有形態で工事の段取りが変わるため。
#
# **補足文を付けないこと。**ここに「管理組合が窓口」「オーナー様が窓口」と
# 書いていたが、**元請から見ると「うちを飛ばして直接やる会社」に読める。**
# 当社は下請なので、取引相手を名指しした説明を画面に置くと、
# 用途の補足（建物の種類の説明）と違って選択の助けにもならず、
# 立場だけが主張として残る。選択肢名だけで誰でも選べる。
TENURES = [
    ("分譲マンション", ""),
    ("賃貸・社宅（ワンオーナー）", ""),
    ("わからない・その他", ""),
]

REGIONS = ["東京都", "神奈川県", "埼玉県", "千葉県", "その他の地域", "未定・相談したい"]

TRADES = [
    "大規模修繕（一括で相談）", "足場・ゴンドラ仮設", "下地・タイル補修",
    "シーリング", "塗装", "防水", "内装・付帯工事", "まだ決まっていない",
]

TIMING = ["できるだけ早く", "3か月以内", "半年以内", "1年以内",
          "1年以上先", "未定・相談したい"]

SCALE = ["〜30戸／小規模", "30〜100戸", "100〜200戸", "200戸以上",
         "戸数以外（延床・階数で相談）", "未定・わからない"]

# 相談時にあると早い資料。用途・所有形態・工種で足す。
# **「必要」ではなく「あると早い」。**無くても相談できることを画面にも書く。
CHECK_BASE = [
    "建物の規模（階数・戸数・延床面積のいずれか）",
    "図面・過去の修繕履歴・調査報告書の有無",
    "居住や営業を続けながらの工事かどうか",
]
CHECK_BY_TENURE = {
    "分譲マンション": [
        "総会・理事会の予定時期（決議のタイミング）",
        "長期修繕計画の有無と、直近の見直し時期",
        "管理会社・設計コンサルタントの関与の有無",
    ],
    # 「オーナー様側の決裁」と書いていた。**「様」を付けると、所有者が当社の
    # 客だという前提になる。**元請から見ると飛び越えて見えるので中立にした。
    # ここは「相談の前にあると早い情報」であって、誰と取引するかの話ではない。
    "賃貸・社宅（ワンオーナー）": [
        "入居・稼働の状況（空室の有無、工事ができる時間帯）",
        "発注までの決裁の流れと、決まる時期の見込み",
    ],
}
CHECK_BY_TRADE = {
    "防水": ["漏水の有無と場所、既存防水の仕様がわかる資料"],
    "足場・ゴンドラ仮設": ["建物周囲のスペース、搬入経路、接道の状況"],
    "下地・タイル補修": ["浮き・ひび割れの状況、打診調査の記録があれば"],
    "塗装": ["前回の塗り替え時期と、使用した塗料がわかる資料"],
}

CSS = """<style>
/* 案件相談ページ専用。共有部分（ヘッダー・フッター・配色）は ../styles.css。
   **企業サイトの styles.css は書き換えない。**毎月のZIPで上書きしないため。 */
.cs-main{padding:0 0 72px}
.cs-hero{background:var(--ink);color:#fff;padding:56px 0 48px;margin-bottom:40px}
.cs-hero .container{max-width:var(--maxw);margin:0 auto;padding:0 24px}
.cs-eyebrow{font-size:.78rem;letter-spacing:.18em;color:var(--bronze-l);margin:0 0 14px}
.cs-hero h1{font-family:"Noto Serif JP",serif;font-weight:700;font-size:clamp(1.6rem,4.2vw,2.3rem);
  line-height:1.55;margin:0 0 16px;color:#fff}
.cs-hero p{margin:0;color:var(--muted-d);font-size:.95rem;line-height:1.95;max-width:42em}
.cs-skip{display:inline-block;margin-top:22px;color:#fff;font-size:.86rem;
  border-bottom:1px solid var(--bronze-l);padding-bottom:3px;text-decoration:none}
.cs-skip:hover{color:var(--bronze-l)}
.cs-wrap{max-width:var(--maxw);margin:0 auto;padding:0 24px;
  display:grid;grid-template-columns:minmax(0,1fr) 316px;gap:40px;align-items:start}
@media(max-width:900px){.cs-wrap{grid-template-columns:1fr;gap:28px}}
.cs-card{background:var(--paper);border:1px solid var(--line);padding:30px 28px;margin-bottom:22px}
.cs-card>h2{font-family:"Noto Serif JP",serif;font-weight:700;font-size:1.18rem;color:var(--ink);
  margin:0 0 6px;display:flex;align-items:baseline;gap:11px}
.cs-num{font-family:"Noto Serif JP",serif;font-size:.9rem;color:var(--bronze);
  border-bottom:1px solid var(--bronze);padding-bottom:1px}
.cs-lead{margin:0 0 22px;color:var(--muted);font-size:.86rem;line-height:1.85}
.cs-field{display:block;margin-bottom:20px}
.cs-field>.cs-label{display:block;font-weight:700;font-size:.9rem;color:var(--text);margin-bottom:9px}
.cs-opt{font-weight:400;font-size:.76rem;color:var(--muted);margin-left:8px}
.cs-req{font-weight:400;font-size:.72rem;color:var(--paper);background:var(--bronze);
  padding:2px 7px;margin-left:8px;letter-spacing:.06em;vertical-align:1px}
.cs-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(232px,1fr));gap:10px}
.cs-choice{display:block;position:relative;border:1px solid var(--line);background:var(--tint);
  padding:13px 15px;cursor:pointer;transition:border-color .15s,background .15s}
.cs-choice:hover{border-color:var(--bronze-l);background:var(--paper)}
.cs-choice input{position:absolute;opacity:0;width:0;height:0}
.cs-choice b{display:block;font-size:.9rem;font-weight:700;color:var(--text);line-height:1.5}
.cs-choice span{display:block;font-size:.76rem;color:var(--muted);margin-top:3px;line-height:1.6}
.cs-choice:has(input:checked){border-color:var(--ink);background:var(--paper);
  box-shadow:inset 3px 0 0 var(--bronze)}
.cs-choice:has(input:focus-visible){outline:2px solid var(--ink);outline-offset:2px}
.cs-row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:640px){.cs-row{grid-template-columns:1fr}}
.cs-card input[type=text],.cs-card input[type=email],.cs-card input[type=tel],
.cs-card select,.cs-card textarea{width:100%;box-sizing:border-box;font:inherit;font-size:.92rem;
  padding:11px 13px;border:1px solid var(--line);background:var(--paper);color:var(--text);border-radius:0}
.cs-card textarea{line-height:1.95;resize:vertical;min-height:15em}
.cs-card input:focus,.cs-card select:focus,.cs-card textarea:focus{outline:2px solid var(--ink);
  outline-offset:-1px;border-color:var(--ink)}
.cs-sub{border-left:3px solid var(--bronze-l);padding-left:18px;margin:-6px 0 20px}
.cs-hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.cs-submit{width:100%;font:inherit;font-size:1rem;font-weight:700;letter-spacing:.05em;
  background:var(--ink);color:#fff;border:0;padding:17px;cursor:pointer;transition:background .15s}
.cs-submit:hover{background:var(--ink-2)}
.cs-note{margin:14px 0 0;font-size:.78rem;color:var(--muted);line-height:1.85}
.cs-rebuild{font:inherit;font-size:.78rem;color:var(--muted);background:none;border:0;
  border-bottom:1px solid var(--line);padding:0 0 2px;cursor:pointer;margin-top:10px}
.cs-rebuild:hover{color:var(--ink);border-color:var(--bronze)}
.cs-aside{position:sticky;top:96px}
@media(max-width:900px){.cs-aside{position:static}}
.cs-box{background:var(--tint);border:1px solid var(--line);padding:22px 20px;margin-bottom:18px}
.cs-box h3{font-family:"Noto Serif JP",serif;font-size:.98rem;color:var(--ink);margin:0 0 12px}
.cs-box ul{margin:0;padding-left:1.15em;font-size:.83rem;line-height:1.95;color:var(--text)}
.cs-box li{margin-bottom:7px}
.cs-box p{margin:0;font-size:.83rem;line-height:1.95;color:var(--muted)}
.cs-box a{color:var(--ink);text-decoration:underline;text-underline-offset:3px}
.cs-warn{border:1px solid var(--bronze);background:#fdfaf5;padding:18px 20px;margin-bottom:18px}
.cs-warn h3{font-family:"Noto Serif JP",serif;font-size:.94rem;color:var(--bronze);margin:0 0 9px}
.cs-warn p{margin:0;font-size:.81rem;line-height:1.9;color:var(--text)}
.cs-test{background:#2b2118;color:#f2e9dd;padding:15px 20px;font-size:.84rem;line-height:1.8}
.cs-test b{color:#e8c68a}
.cs-preview{white-space:pre-wrap;font-size:.8rem;line-height:1.8;background:var(--tint);
  border:1px solid var(--line);padding:16px;margin-top:14px;max-height:22em;overflow:auto}
</style>"""


def _head(title: str, desc: str) -> str:
    robots = "" if PUBLISH else '\n  <meta name="robots" content="noindex,nofollow" />'
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <meta name="description" content="{desc}" />{robots}
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{desc}" />
  <meta property="og:type" content="website" />
  <meta property="og:locale" content="ja_JP" />
  <link rel="canonical" href="{CANONICAL}" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Noto+Serif+JP:wght@500;600;700&display=swap" rel="stylesheet" />
  <link rel="icon" href="{BASE}favicon.svg" type="image/svg+xml" />
  <link rel="stylesheet" href="{BASE}styles.css" />{analytics_tags()}
{CSS}
</head>
<body>

<header class="site-header" id="top">
  <div class="header-inner">
    <a href="{BASE}" class="brand" aria-label="株式会社 第一技研 ホーム">
      <img src="{BASE}img/logo-black.png" alt="第一技研 D GIKEN ロゴ" class="brand-logo" />
      <span class="brand-text">株式会社&#8202;第一技研</span>
    </a>
    <nav class="site-nav" aria-label="グローバルナビゲーション">
      <a href="{BASE}#about">企業姿勢</a>
      <a href="{BASE}#strength">強み</a>
      <a href="{BASE}#service">事業内容</a>
      <a href="{BASE}#works">施工実績</a>
      <a href="{BASE}#company">会社概要</a>
      <a href="{BASE}#contact" class="nav-cta">お問い合わせ</a>
    </nav>
    <button class="nav-toggle" aria-label="メニューを開く" aria-expanded="false">
      <span></span><span></span><span></span>
    </button>
  </div>
</header>
"""


FOOTER = """
<footer class="site-footer">
  <div class="container footer-inner">
    <div class="footer-brand">
      <img src="{BASE}img/logo-white.png" alt="第一技研 D GIKEN" class="footer-logo" />
      <p class="footer-license">特定建設業&ensp;東京都知事許可（特-7）第138912号<br />A Member of NISSO GROUP（東証・名証 1444）</p>
    </div>
    <p class="footer-copy">© 1996–2026 DAIICHI GIKEN CO., LTD.</p>
  </div>
</footer>

<script>
(function () {
  var t = document.querySelector('.nav-toggle'), n = document.querySelector('.site-nav');
  if (t && n) t.addEventListener('click', function () {
    var open = n.classList.toggle('is-open');
    t.setAttribute('aria-expanded', open ? 'true' : 'false');
  });
})();
</script>
</body>
</html>
"""


def _choices(items: list[tuple[str, str]], kind: str, group: str) -> str:
    """選択肢。**name 属性を付けない。**付けると contact.php に未知の項目が飛ぶ。

    補足が空のときは <span> ごと出さない。空の span も display:block なので、
    出すと選択肢の高さだけが揃わずに増える。
    """
    out = []
    for value, note in items:
        sub = f"<span>{note}</span>" if note else ""
        out.append(
            f'<label class="cs-choice"><input type="{kind}" data-group="{group}" '
            f'value="{value}" /><b>{value}</b>{sub}</label>')
    return "".join(out)


def _options(items: list[str]) -> str:
    return "".join(f"<option>{v}</option>" for v in items)


# ---------------------------------------------------------------- ページ本体
JS = r"""
(function () {
  'use strict';
  var D = JSON.parse(document.getElementById('cs-data').textContent);
  var $ = function (s) { return document.querySelector(s); };
  var form = $('#contact-form'), msg = $('#cs-message');
  var touched = false;   // 利用者が本文を直接編集したら、自動で上書きしない

  function picked(group) {
    return [].slice.call(document.querySelectorAll('[data-group="' + group + '"]:checked'))
             .map(function (e) { return e.value; });
  }
  function one(group) { var v = picked(group); return v.length ? v[0] : ''; }

  function isJutaku() { return one('use') === '集合住宅'; }

  function syncTenure() {
    var box = $('#cs-tenure');
    box.hidden = !isJutaku();
    if (box.hidden) {
      [].slice.call(box.querySelectorAll('input')).forEach(function (i) { i.checked = false; });
    }
  }

  function checklist() {
    var list = D.base.slice();
    var t = one('tenure');
    if (t && D.byTenure[t]) list = list.concat(D.byTenure[t]);
    picked('trade').forEach(function (tr) {
      if (D.byTrade[tr]) D.byTrade[tr].forEach(function (x) {
        if (list.indexOf(x) < 0) list.push(x);
      });
    });
    var ul = $('#cs-check');
    ul.replaceChildren();
    list.forEach(function (x) {
      var li = document.createElement('li');
      li.textContent = x;
      ul.appendChild(li);
    });
  }

  function compose() {
    var use = one('use'), ten = one('tenure'), trades = picked('trade');
    var region = $('#cs-region').value, city = $('#cs-city').value.trim();
    var scale = $('#cs-scale').value, timing = $('#cs-timing').value;
    var L = ['工事のご相談をしたく、ご連絡しました。', '', '【案件の条件】'];
    // 所有形態のラベル自体が括弧を含むので、括弧で囲むと二重になる。「／」でつなぐ。
    if (use) L.push('建物の用途：' + use + (ten ? '／' + ten : ''));
    if (region) L.push('所在地：' + region + (city ? ' ' + city : ''));
    if (scale) L.push('規模：' + scale);
    if (trades.length) L.push('希望する工事：' + trades.join('、'));
    if (timing) L.push('希望する時期：' + timing);
    if (L.length === 3) L.push('（まだ決まっていません。相談しながら整理したいです。）');
    L.push('', '【ご相談の内容】', '');
    return L.join('\n');
  }

  function refresh() {
    syncTenure();
    checklist();
    if (!touched) {
      var keep = msg.selectionStart === msg.value.length;
      msg.value = compose();
      if (keep) { msg.selectionStart = msg.selectionEnd = msg.value.length; }
    }
  }

  document.addEventListener('change', function (e) {
    if (!e.target.dataset || !e.target.dataset.group) {
      if (['cs-region', 'cs-city', 'cs-scale', 'cs-timing'].indexOf(e.target.id) < 0) return;
    }
    // 「まだ決まっていない」は他の工種と同時に選べない
    if (e.target.dataset && e.target.dataset.group === 'trade' && e.target.checked) {
      var undecided = 'まだ決まっていない';
      [].slice.call(document.querySelectorAll('[data-group="trade"]')).forEach(function (c) {
        if (c !== e.target && (e.target.value === undecided || c.value === undecided)) {
          c.checked = false;
        }
      });
    }
    refresh();
  });
  $('#cs-city').addEventListener('input', refresh);

  msg.addEventListener('input', function () { touched = true; $('#cs-rebuild').hidden = false; });
  $('#cs-rebuild').addEventListener('click', function () {
    touched = false; $('#cs-rebuild').hidden = true; refresh(); msg.focus();
  });

  // --- 送信 -------------------------------------------------------------
  // 本番（dai1giken.co.jp）でだけ contact.php へ送る。
  // **テスト用のホストから送ると、本物の問い合わせメールが飛ぶ。**
  var live = location.hostname === 'dai1giken.co.jp';
  if (!live) {
    form.removeAttribute('action');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!form.reportValidity()) return;
      var fd = new FormData(form), lines = [];
      fd.forEach(function (v, k) { if (k !== 'website') lines.push(k + ': ' + v); });
      var pre = $('#cs-preview');
      pre.hidden = false;
      pre.textContent = 'POST ' + D.action + '\n\n' + lines.join('\n');
      pre.scrollIntoView({ block: 'center' });
    });
  }
  refresh();
})();
"""


def build(basis: dict | None = None) -> int:
    out = HERE / "consultation"
    out.mkdir(exist_ok=True)

    title = "案件のご相談｜株式会社 第一技研"
    desc = ("マンション・ビル・工場・学校などの外装改修について、決まっている条件だけで"
            "ご相談いただけます。建物の用途・所在地・工種・時期を選ぶと相談内容が整い、"
            "そのまま送信できます。足場から内装まで自社管理で一貫対応。")

    data = {
        "base": CHECK_BASE,
        "byTenure": CHECK_BY_TENURE,
        "byTrade": CHECK_BY_TRADE,
        "action": "/contact.php",
    }

    h = [_head(title, desc)]
    h.append(f'''
<main class="cs-main">

<div class="cs-hero">
  <div class="container">
    <p class="cs-eyebrow">CONSULTATION ／ 案件のご相談</p>
    <h1>決まっていることだけで、<br />ご相談いただけます。</h1>
    <p>建物の用途や希望する工事を選ぶと、ご相談の内容が自動でまとまります。未定の項目はそのままで構いません。足場・下地補修・シーリング・塗装・防水・内装まで、一つの窓口でお受けします。</p>
    <a class="cs-skip" href="#cs-contact">条件を選ばずに、そのまま相談する →</a>
  </div>
</div>

<div class="cs-wrap">
  <form class="contact-form" id="contact-form" action="/contact.php" method="post">

    <section class="cs-card">
      <h2><span class="cs-num">01</span>案件について</h2>
      <p class="cs-lead">わかる範囲で選んでください。すべて任意です。選ぶほど、担当者からの最初のご返信が具体的になります。</p>

      <div class="cs-field">
        <span class="cs-label">建物の用途<span class="cs-opt">任意</span></span>
        <div class="cs-grid">{_choices(USES, "radio", "use")}</div>
      </div>

      <div class="cs-sub" id="cs-tenure" hidden>
        <div class="cs-field">
          <span class="cs-label">集合住宅の所有形態<span class="cs-opt">任意</span></span>
          <p class="cs-lead" style="margin-bottom:12px">ご相談の進め方が変わるためお伺いしています。</p>
          <div class="cs-grid">{_choices(TENURES, "radio", "tenure")}</div>
        </div>
      </div>

      <div class="cs-row">
        <label class="cs-field"><span class="cs-label">所在地<span class="cs-opt">任意</span></span>
          <select id="cs-region"><option value="">選んでください</option>{_options(REGIONS)}</select>
        </label>
        <label class="cs-field"><span class="cs-label">市区町村<span class="cs-opt">任意</span></span>
          <input type="text" id="cs-city" maxlength="60" placeholder="例：文京区" autocomplete="off" />
        </label>
      </div>

      <div class="cs-row">
        <label class="cs-field"><span class="cs-label">建物の規模<span class="cs-opt">任意</span></span>
          <select id="cs-scale"><option value="">選んでください</option>{_options(SCALE)}</select>
        </label>
        <label class="cs-field"><span class="cs-label">希望する時期<span class="cs-opt">任意</span></span>
          <select id="cs-timing"><option value="">選んでください</option>{_options(TIMING)}</select>
        </label>
      </div>

      <div class="cs-field" style="margin-bottom:0">
        <span class="cs-label">希望する工事<span class="cs-opt">任意・複数選択できます</span></span>
        <div class="cs-grid">{_choices([(t, "") for t in TRADES], "checkbox", "trade")}</div>
      </div>
    </section>

    <section class="cs-card" id="cs-contact">
      <h2><span class="cs-num">02</span>ご相談の内容と、ご連絡先</h2>
      <p class="cs-lead">上で選んだ条件が本文に入ります。ご自由に書き足し、書き換えてください。</p>

      <label class="cs-field"><span class="cs-label">お問い合わせ内容<span class="cs-req">必須</span></span>
        <textarea name="message" id="cs-message" rows="14" required></textarea>
      </label>
      <button type="button" class="cs-rebuild" id="cs-rebuild" hidden>選んだ条件から本文を作り直す</button>

      <div class="cs-row" style="margin-top:26px">
        <label class="cs-field"><span class="cs-label">会社名・団体名<span class="cs-opt">任意</span></span>
          <input type="text" name="company" autocomplete="organization" />
        </label>
        <label class="cs-field"><span class="cs-label">お名前<span class="cs-req">必須</span></span>
          <input type="text" name="name" autocomplete="name" required />
        </label>
      </div>
      <div class="cs-row">
        <label class="cs-field"><span class="cs-label">メールアドレス<span class="cs-req">必須</span></span>
          <input type="email" name="email" autocomplete="email" required />
        </label>
        <label class="cs-field"><span class="cs-label">電話番号<span class="cs-opt">任意</span></span>
          <input type="tel" name="tel" autocomplete="tel" />
        </label>
      </div>

      <div class="cs-hp" aria-hidden="true">
        <label>このフィールドは空欄のままにしてください
          <input type="text" name="website" tabindex="-1" autocomplete="off" /></label>
      </div>

      <button type="submit" class="cs-submit">この内容で相談する</button>
      <p class="cs-note">送信内容は既存のお問い合わせ窓口に届きます。金額・工期・施工の可否は、現地または資料を確認のうえ担当者よりご案内します。この画面で確約するものではありません。</p>
      <pre class="cs-preview" id="cs-preview" hidden></pre>
    </section>
  </form>

  <aside class="cs-aside">
    <div class="cs-box">
      <h3>ご相談の前にあると早いもの</h3>
      <ul id="cs-check"></ul>
      <p style="margin-top:12px">いずれも無くてご相談いただけます。わからない項目は、そのままお伝えください。</p>
    </div>
    <div class="cs-box">
      <h3>対応できる工事</h3>
      <p>足場・ゴンドラ仮設、下地・タイル補修、シーリング、塗装、防水、内装・付帯工事までを自社管理で一貫して行います。特定建設業（特-7）第138912号。1級建築施工管理技士が在籍しています。</p>
    </div>
    <div class="cs-box">
      <h3>施工実績</h3>
      <p>2023年から2026年までの52件を、施工年月・物件名・建物用途・工事内容で公開しています。<a href="{BASE}#works">実績の一覧を見る →</a></p>
    </div>
    <div class="cs-warn">
      <h3>お約束の範囲について</h3>
      <p>この画面では金額・工期・施工の可否をお答えしません。条件を確認したうえで、担当者よりご連絡します。</p>
    </div>
  </aside>
</div>
</main>

<script id="cs-data" type="application/json">{json.dumps(data, ensure_ascii=False)}</script>
<script>{JS}</script>
''')
    # FOOTER は JS を含むので f-string にできない（`function () {` が壊れる）。
    # **{BASE} はここで手で置換する。**忘れると画像のURLが "{BASE}img/..." のまま
    # 出力され、404 になる（実際に一度そうなった）。
    h.append(FOOTER.replace("{BASE}", BASE))

    html = "".join(h)
    if "{BASE}" in html:
        raise SystemExit("出力に未置換の {BASE} が残っています。f-string でない定数を確認してください。")
    (out / "index.html").write_text(html, encoding="utf-8")

    n_check = len(CHECK_BASE) + sum(len(v) for v in CHECK_BY_TENURE.values()) \
        + sum(len(v) for v in CHECK_BY_TRADE.values())
    print(f"  用途{len(USES)} / 所有形態{len(TENURES)} / 工種{len(TRADES)} / "
          f"確認事項{n_check}　POST項目6（既存のまま）　"
          f"{'公開' if PUBLISH else 'noindex（テスト）'}")
    return 1


def main() -> None:
    build(None)
    print("consultation/ に 1 枚生成しました")


if __name__ == "__main__":
    main()

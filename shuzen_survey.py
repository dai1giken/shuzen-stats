# -*- coding: utf-8 -*-
"""実態調査の「工事金額の内訳」と「仮設工事の割合」。

出典: 国土交通省「令和3年度 マンション大規模修繕工事に関する実態調査」
      （2022-06-17 公表、回答 818 件）
      https://www.mlit.go.jp/jutakukentiku/house/content/001619430.pdf

--- ページ番号は PDF と紙面で1つずれる -------------------------------
この PDF は**表紙が紙面の 0 ページ**にあたるため、PDF のページ番号は紙面より
常に1つ大きい。「p.13」とだけ書くと、読む人がどちらで開くかで別のページに着く。
`shuzen_cycle.py` と同じく **「PDF p.13（紙面 12）」の形で両方書く**こと。

      PDF p.5 （紙面 4） 工事金額の定義（何を含み、何を含まないか）
      PDF p.13（紙面 12）工事金額の内訳（総額に対する割合／建築系工事の内訳）
      PDF p.15（紙面 14）戸あたり工事金額
      PDF p.16（紙面 15）床面積あたり工事金額
      PDF p.50（紙面 49）総工事金額に占める割合、および仮設工事の割合

--- これは e-Stat から取れない ------------------------------------------
戸あたり工事金額（basis["survey"]["per_unit"]）と工事費指数は API で毎月
取り直しているが、**内訳の割合は PDF にしかない**。`shuzen_cycle.py` と同じく
原典を人が読んで書き写した値になる。原典が更新されたら手で直す必要がある。

--- 書き写しを機械で突合している --------------------------------------
突合は2段構えにしてある。

1. **原典の生テキストと照合する。**`refs/shuzen_survey.txt` に pypdf で抽出した
   原典を置いてあり、`verify()` が各定数の数値が原典に実在するかを確かめる。
2. **原典の中で独立した2つの表を突き合わせる。**PDF p.13 は「建築系工事＝100 と
   したときの各工種の割合」、PDF p.50 は「総工事金額に占める割合」。別々に
   読み取れるので、按分すれば一致するはずである。

       p.13 の各工種 × 建築系工事の 60.3%  ==  p.50 の総額比

合わなければ書き写しを間違えている。`build_cost.py` は verify() が通らなければ
ページを作らない。

    py shuzen_survey.py      # 突合だけ走らせる

--- 割合の合計は 100% にならない ---------------------------------------
原典は各項目を小数第1位に丸めて載せているので、足すと 100.1%（総額の内訳）や
99.9%（建築系の内訳）になる。**これは誤記ではない。**丸めの累積が項目数 × 0.05
の範囲に収まっているかだけを見る。合わせようとして数値をいじらないこと。

--- 母数が表ごとに違う -------------------------------------------------
戸あたり工事金額は n=818 だが、**内訳と仮設割合は n=726**。原典に
「対象マンションのうち、建築系工事を実施していないサンプルを除外して集計」と
注記がある。さらに p.50 の内訳は 合計 726 に対して 20階以上 44 ＋ 20階未満 679
＝ 723 で、**3件足りない。これも原典どおり**（階数の不明分とみられる）。
数を合わせようとしないこと。

--- 「仮設工事＝足場」と書かないこと -----------------------------------
**原典に「足場」という語は全64ページで一度も出てこない。**仮設工事の内訳定義も
無い。だから仮設工事の 22.8% を引いた額は「足場を除いた額」ではなく
「仮設工事を除いた額」でしかない。この但し書きを落とすと、引いた額が
"足場抜き" として独り歩きする。

--- 共通仮設費は入っていない -------------------------------------------
p.4 の定義で **共通仮設費は集計対象外**。つまりこの内訳の 100% のどこにも
共通仮設費は無く、消費税も無い。**ここから出る金額は実勢より低い。**
誤差の向きを画面に書くこと。隠すと、低い数字だけが独り歩きする。
"""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
REF = HERE / "refs" / "shuzen_survey.txt"

SOURCE_NAME = "令和3年度 マンション大規模修繕工事に関する実態調査"
SOURCE_PUBLISHER = "国土交通省"
SOURCE_PUBLISHED = "2022-06-17"
SOURCE_N = 818
SOURCE_URL = "https://www.mlit.go.jp/jutakukentiku/house/content/001619430.pdf"

# 内訳と仮設割合だけ母数が違う（建築系工事を実施していないサンプルを除外した集計）
BREAKDOWN_N = 726


def page(pdf: int) -> str:
    """出典のページ表記。**PDF と紙面の両方を書く。**片方だけだと1ページずれる。"""
    return f"PDF p.{pdf}（紙面 {pdf - 1}）"


PAGE_DEFINITION = page(5)
PAGE_BREAKDOWN = page(13)
PAGE_PER_UNIT = page(15)
PAGE_PER_AREA = page(16)
PAGE_SHARE = page(50)

# 価格時点。調査対象はおおむね2018〜2021年の受注で、その中心を2020年度と置いて
# デフレーターの基準年（2020年度＝100）に対応させている。**これは当社が置いた仮定**で、
# 原典が「価格時点は2020年度」と書いているわけではない。画面にそう明記すること。
PRICE_ANCHOR = "2020年度"
PRICE_ANCHOR_NOTE = (
    "調査対象はおおむね2018〜2021年に受注した工事です。その中心を2020年度と置き、"
    "工事費指数の基準年（2020年度＝100）に対応させています。これは当社が置いた仮定です。"
)

# 原典は分譲マンション（区分所有建物）の調査。賃貸・社宅・寮の外装改修に当てはめる場合、
# **調査対象そのものではない**。この一文を画面から落とさないこと。
SCOPE_NOTE = (
    "この調査の対象は分譲マンション（区分所有建物）です。賃貸マンション・社宅・寮は"
    "調査対象に含まれていません。建物の造りが近ければ目安として読めますが、"
    "その建物を調べた数値ではありません。"
)

# 工事金額に含まれるもの（p.4）
INCLUDED = [
    "直接工事費（屋根防水・床防水・外壁塗装・外壁タイル・シーリング・鉄部等塗装・"
    "建具金物・共用内部・設備関連・外構・仮設工事・その他）",
    "諸経費①（現場管理費・一般管理費・法定福利費 等）",
    "諸経費②（大規模修繕瑕疵保険の保険料）",
]

# 工事金額に含まれないもの（p.4）
EXCLUDED = [
    "共通仮設費",
    "消費税相当額",
    "設計コンサルタント業務の費用（調査・診断／設計／工事監理 等）",
    "耐震改修工事",
]

# 総工事金額に対する割合（p.13 ＜全体＞）
TOTAL_BREAKDOWN: list[tuple[str, float]] = [
    ("建築系工事", 60.3),
    ("仮設工事", 22.8),
    ("諸経費①（現場管理費等）", 9.5),
    ("その他工事", 3.8),
    ("設備系工事", 1.6),
    ("外構・付属施設", 1.3),
    ("諸経費②（瑕疵保険料）", 0.8),
]

# 建築系工事の内訳（p.13。建築系工事の合計＝100 とした割合）
BUILDING_BREAKDOWN: list[tuple[str, float]] = [
    ("外壁塗装", 24.5),
    ("床防水", 18.6),
    ("屋根防水", 13.4),
    ("外壁タイル", 12.9),
    ("シーリング工事", 12.0),
    ("鉄部等塗装", 7.4),
    ("建具・金物等", 7.4),
    ("共用内部", 3.7),
]

# p.50「総工事金額に占める割合」。**突合の相手**であって、表示には使わない。
# p.13 から按分した値がここに一致することを verify() が確かめる。
P50_TOTAL_SHARE: dict[str, float] = {
    "屋根防水": 8.1,
    "床防水": 11.2,
    "外壁塗装": 14.8,
    "外壁タイル": 7.8,
    "シーリング工事": 7.3,
    "鉄部等塗装": 4.5,
    "建具・金物等": 4.4,
    "仮設工事": 22.8,
    "その他工事": 3.8,
}

# 突合の許容差（ポイント）。原典の p.13 と p.50 は丸めの桁が違うため、
# 按分値と完全一致はしない。実測の最大差は 0.06pt（シーリング工事・建具金物等）。
VERIFY_TOLERANCE = 0.07

# 工事金額に占める仮設工事の割合（p.50）。階数で分かれている。
KASETSU_SHARE = {
    "all": {"label": "合計", "n": 726, "percent": 22.8},
    "tall": {"label": "20階以上", "n": 44, "percent": 29.0},
    "other": {"label": "20階未満", "n": 679, "percent": 21.9},
}
KASETSU_TALL_FLOORS = 20

# 床面積あたり工事金額（万円／㎡、p.16）。延床が分かるときの検算用。
PER_AREA: list[dict] = [
    {"label": "1回目", "n": 297, "q1": 0.9, "median": 1.1, "q3": 1.4, "mean": 1.3},
    {"label": "2回目", "n": 181, "q1": 1.1, "median": 1.3, "q3": 1.6, "mean": 1.5},
    {"label": "3回目以上", "n": 155, "q1": 0.9, "median": 1.2, "q3": 1.7, "mean": 1.9},
]

# 工事の範囲を絞っても、まるごとかかるもの。
# **一部分だけ直す場合でも、足場も現場管理費も同じだけかかる。**
# 部分改修の既定でここを外すと、金額が現実離れして低く出る。
COMMON_ITEMS = ["仮設工事", "諸経費①（現場管理費等）", "諸経費②（瑕疵保険料）"]

# 「仮設」「共通仮設」「足場」の違い。素人には区別が付かないので画面にそのまま出す。
KASETSU_GLOSSARY: list[tuple[str, str]] = [
    ("仮設工事",
     "工事のあいだだけ設けて、終わったら撤去するもの全部。建物には残りません。"
     "下の「直接仮設」と「共通仮設」の2つに分かれます。"),
    ("直接仮設（足場はここ）",
     "工事そのものに直接必要な設備。足場、飛散防止シート、昇降階段、"
     "落下防止の朝顔、開口部の養生など。足場はこの中でいちばん金額が大きい項目です。"),
    ("共通仮設",
     "現場を運営するために必要なもの。現場事務所、作業員休憩所、仮設トイレ、"
     "資材置場、仮設の電気・水道、安全対策、清掃、近隣対策、道路使用許可の申請など。"),
    ("この統計での扱い",
     "統計の工事金額には直接仮設が含まれ、共通仮設は含まれません。"
     "ただし原典に「足場」という語は無く、仮設工事の内訳も示されていないため、"
     "「仮設工事 22.8%」がそのまま足場の金額というわけではありません。"),
]


def _round_half_up(x: float) -> int:
    """四捨五入。Python の round() は偶数丸めなので、そのままでは使わない。

    画面の数値は JavaScript 側でも同じ式で出すため、**丸め方を揃えておく**。
    ここがずれると、サーバで作った表とブラウザで作った表が1桁だけ食い違う。
    """
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def breakdown() -> list[dict]:
    """工事金額の内訳。割合の降順。

    建築系工事は p.13 の内訳を 60.3% で按分して、総額に対する割合に直す。
    `kasetsu` は仮設工事の行、`common` は範囲を絞ってもかかる行の印。
    """
    kenchiku = dict(TOTAL_BREAKDOWN)["建築系工事"]
    rows = [
        {"label": label,
         "percent": _round_half_up(pct * kenchiku) / 100,
         "kasetsu": False,
         "common": False}
        for label, pct in BUILDING_BREAKDOWN
    ]
    rows += [
        {"label": label,
         "percent": pct,
         "kasetsu": label == "仮設工事",
         "common": label in COMMON_ITEMS}
        for label, pct in TOTAL_BREAKDOWN if label != "建築系工事"
    ]
    rows.sort(key=lambda r: -r["percent"])
    return rows


def kasetsu_share(floors: int | None) -> dict:
    """階数に対応する仮設工事の割合（p.50）。

    階数が分からないときは「合計」を返す。20階以上とそれ未満で原典が分かれている。
    """
    if not floors:
        return KASETSU_SHARE["all"]
    return KASETSU_SHARE["tall"] if floors >= KASETSU_TALL_FLOORS else KASETSU_SHARE["other"]


def _ref_text() -> str:
    """原典の生テキスト。無ければ空文字（照合を飛ばす）。"""
    return REF.read_text(encoding="utf-8") if REF.exists() else ""


def verify() -> list[str]:
    """書き写しの突合。問題があれば理由の一覧を返す（空なら OK）。"""
    bad: list[str] = []

    # (1) 合計。原典が小数第1位に丸めているので 100% ちょうどにはならない。
    #     許容は「項目数 × 丸め幅」で、これを超えたら書き写しが1項目ずれている。
    for name, rows in (("総額", TOTAL_BREAKDOWN), ("建築系", BUILDING_BREAKDOWN)):
        got = sum(p for _, p in rows)
        limit = len(rows) * 0.05
        if abs(got - 100.0) > limit + 1e-9:
            bad.append(f"{PAGE_BREAKDOWN} {name}の内訳の合計が {got:.1f}%"
                       f"（丸めの累積は ±{limit:.2f}pt までのはず）")

    # (2) p.13 から按分した値が p.50 に一致するか
    got = {r["label"]: r["percent"] for r in breakdown()}
    for label, expect in P50_TOTAL_SHARE.items():
        if label not in got:
            bad.append(f"{PAGE_SHARE} にある「{label}」が内訳に無い")
            continue
        if abs(got[label] - expect) > VERIFY_TOLERANCE:
            bad.append(f"{label}　按分 {got[label]:.2f}% ≠ {PAGE_SHARE} {expect}%"
                       f"（差 {abs(got[label] - expect):.2f}pt）")

    # (3) 仮設工事の割合。**n は足しても合計に届かない（原典どおり）**ので、
    #     超えていないことだけを見る。等号にすると原典が NG になる。
    for key in ("all", "tall", "other"):
        if not 0 < KASETSU_SHARE[key]["percent"] < 100:
            bad.append(f"仮設工事の割合が範囲外: {key}")
    n_sum = KASETSU_SHARE["tall"]["n"] + KASETSU_SHARE["other"]["n"]
    if n_sum > KASETSU_SHARE["all"]["n"]:
        bad.append(f"仮設工事の n が合計を超えている: {n_sum} > {KASETSU_SHARE['all']['n']}")

    for label in COMMON_ITEMS:
        if label not in got:
            bad.append(f"範囲を絞ってもかかる項目「{label}」が内訳に無い")

    # (4) 原典の生テキストとの照合。数値が原典に実在するかを見る。
    ref = _ref_text()
    if not ref:
        bad.append(f"原典の抽出テキストが無い: {REF}")
        return bad

    for label, pct in BUILDING_BREAKDOWN:
        if f"{pct}%" not in ref:
            bad.append(f"{PAGE_BREAKDOWN} 建築系「{label} {pct}%」が原典に見当たらない")
    for label, pct in TOTAL_BREAKDOWN:
        if f"{pct}%" not in ref:
            bad.append(f"{PAGE_BREAKDOWN} 総額「{label} {pct}%」が原典に見当たらない")
    for key in ("all", "tall", "other"):
        k = KASETSU_SHARE[key]
        if f"{k['percent']}%" not in ref:
            bad.append(f"{PAGE_SHARE} 仮設工事「{k['label']} {k['percent']}%」が原典に見当たらない")
        if f"n={k['n']}" not in ref:
            bad.append(f"{PAGE_SHARE} 仮設工事の n={k['n']}（{k['label']}）が原典に見当たらない")

    # 定義の一文。ここが変わったら EXCLUDED を書き直す必要がある。
    for phrase in ("共通仮設費は含まない", "消費税相当額は含まない",
                   "建築系工事を実施していないサンプルを除外"):
        if phrase not in ref:
            bad.append(f"原典に「{phrase}」が見当たらない。定義が変わった可能性がある")

    return bad


def main() -> None:
    bad = verify()
    rows = breakdown()
    print(f"{SOURCE_NAME}　内訳 {len(rows)} 項目")
    for r in rows:
        mark = "仮設" if r["kasetsu"] else ("常時" if r["common"] else "  ")
        p50 = P50_TOTAL_SHARE.get(r["label"])
        ref = f"　p.50 {p50}%" if p50 is not None else ""
        print(f"  {mark} {r['label']:　<14} {r['percent']:>6.2f}%{ref}")
    print(f"  合計 {sum(r['percent'] for r in rows):.2f}%（按分の丸めで 100% ちょうどにはならない）")
    if bad:
        print("\n突合 NG")
        for b in bad:
            print("  -", b)
        raise SystemExit(1)
    print(f"\n突合 OK（p.13 の按分と p.50 が ±{VERIFY_TOLERANCE}pt 以内で一致）")


if __name__ == "__main__":
    main()

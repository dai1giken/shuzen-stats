# -*- coding: utf-8 -*-
"""住宅・土地統計調査（市区町村別ストック表）の中身を実測して報告するだけの診断スクリプト。

    py probe_city.py          # ESTAT_APP_ID が要る

**basis.json も HTML も一切書き換えない。** 読んで数えて出力するだけ。
定義統一（都道府県ページを着工＝フローからストックへ寄せる）に踏み切る前に、
この表で本当に47都道府県ぶんの値が取れるのかを確かめるために作った。

答えを出したい問い:
  1. 全国行（area コード 00000）はあるか
  2. 都道府県の合計行（\\d{2}000）は47件そろうか      ← これが無いと県ページを統一できない
  3. cat04（建築の時期）のコードと表示名の対応       ← ラベル文字列一致をやめるための材料
  4. 5桁だが市区町村でない行（振興局など）が混ざるか
  5. 全国のストック値と、一都三県が占める割合
  6. 戸数の閾値で絞ったとき、一都三県に何ページ残るか

CI では .github/workflows/probe.yml から呼ぶ。commit も deploy もしない。
"""
from __future__ import annotations

import re
import sys

from update_basis import CITY_ID, CITY_PREFS, _as_list, _call

# 2026年時点で築26〜45年。update_basis.CITY_COHORT と同じ意味だが、
# ここではラベル文字列に依存せず「年」で選ぶ（それ自体が検証対象なので）。
WINDOW = (1981, 2000)
THRESHOLDS = (0, 500, 1000, 2000, 3000, 5000, 10000)

DASH = str.maketrans({"～": "-", "〜": "-", "~": "-", "－": "-", "—": "-"})


def years(label: str) -> tuple[int | None, int | None]:
    """'1981～1990年'→(1981,1990) / '1970年以前'→(None,1970) / '2021～2023年9月'→(2021,2023)

    開始年・終了年のどちらかが None のものは、端が開いているのでコホートに選ばない。
    """
    ys = [int(m) for m in re.findall(r"(?:19|20)\d{2}", label.translate(DASH))]
    if not ys:
        return (None, None)
    if "以前" in label:
        return (None, ys[0])
    if "以降" in label:
        return (ys[0], None)
    return (ys[0], ys[-1])


def main() -> int:
    meta = _call("getMetaInfo", statsDataId=CITY_ID)["GET_META_INFO"]["METADATA_INF"]
    classes = meta["CLASS_INF"]["CLASS_OBJ"]
    areas, periods = {}, {}
    for c in classes:
        if c["@id"] == "area":
            areas = {i["@code"]: i for i in _as_list(c["CLASS"])}
        if c["@id"] == "cat04":
            periods = {i["@code"]: i["@name"] for i in _as_list(c["CLASS"])}

    print("=" * 72)
    print(f"statsDataId={CITY_ID}  area クラス {len(areas)} 件")
    print("=" * 72)

    # --- 問3: cat04 のコードと名前 -------------------------------------
    print("\n[3] cat04（建築の時期）のコードと表示名")
    for code in sorted(periods):
        lo, hi = years(periods[code])
        mark = "  ★コホート" if lo is not None and hi is not None \
            and WINDOW[0] <= lo and hi <= WINDOW[1] else ""
        print(f"    {code!r:>8} = {periods[code]!r}  → 年 {lo}〜{hi}{mark}")
    # 波ダッシュの実体を明示する（U+FF5E か U+301C かでラベル一致が壊れる）
    for code in sorted(periods):
        nm = periods[code]
        if any(ch in nm for ch in "～〜~"):
            ch = next(c for c in nm if c in "～〜~")
            print(f"    ダッシュの実体: {nm!r} に U+{ord(ch):04X}")
            break

    # --- 問1・2・4: area 軸の構成 ---------------------------------------
    print("\n[1] 全国行 '00000' の有無:", "あり" if "00000" in areas else "なし")

    pref_rows = sorted(c for c in areas if re.fullmatch(r"\d{2}000", c))
    print(f"[2] 都道府県の合計行（\\d{{2}}000）: {len(pref_rows)} 件")
    if len(pref_rows) != 47:
        print("    ！47件ではない。県ページのストック統一はこの時点で見直しが要る")
    missing = [f"{i:02d}000" for i in range(1, 48) if f"{i:02d}000" not in areas]
    if missing:
        print("    欠けている都道府県コード:", missing)

    five = [c for c in areas if re.fullmatch(r"\d{5}", c)]
    odd = [c for c in areas if not re.fullmatch(r"\d{5}", c)]
    print(f"[4] area コードの形: 5桁の数字 {len(five)} 件 ／ それ以外 {len(odd)} 件")
    for c in odd[:20]:
        print(f"    非5桁: {c!r} {areas[c]['@name']}")
    # 北海道は振興局の行が混ざりやすいので、実物を並べて目で見る
    hok = sorted(c for c in areas if c.startswith("01"))
    print(f"    北海道（01）の行 {len(hok)} 件。先頭12件:")
    for c in hok[:12]:
        print(f"      {c} {areas[c]['@name']}  parent={areas[c].get('@parentCode')!r}")

    # --- データ本体 ------------------------------------------------------
    d = _call("getStatsData", statsDataId=CITY_ID, cdCat01="2", cdCat02="3", cdCat03="00",
              limit=100000)
    sd = d["GET_STATS_DATA"]["STATISTICAL_DATA"]
    vals = _as_list(sd["DATA_INF"]["VALUE"])
    print(f"\n取得した VALUE: {len(vals):,} 件")

    cohort_codes = [c for c, nm in periods.items()
                    if (y := years(nm))[0] is not None and y[1] is not None
                    and WINDOW[0] <= y[0] and y[1] <= WINDOW[1]]
    print(f"コホートに選ばれた cat04 コード: {cohort_codes} "
          f"→ {[periods[c] for c in cohort_codes]}")
    if len(cohort_codes) != 2:
        print("    ！2件ではない。区分の切り方が変わっている")

    stock: dict[str, int] = {}
    for v in vals:
        if v.get("@cat04") in cohort_codes:
            try:
                stock[v["@area"]] = stock.get(v["@area"], 0) + int(v["$"])
            except (ValueError, TypeError):
                continue

    # --- 問5: 全国値と一都三県シェア ------------------------------------
    print("\n[5] 全国のストック値（築26〜45年・非木造共同住宅）")
    nat_row = stock.get("00000")
    sum47 = sum(stock.get(c, 0) for c in pref_rows)
    print(f"    全国行 00000 : {nat_row if nat_row is not None else '（無し）'}")
    print(f"    47都道府県合計: {sum47:,} 戸")
    if nat_row is not None:
        print(f"    差            : {nat_row - sum47:,} 戸")
    metro = sum(stock.get(p + "000", 0) for p in CITY_PREFS)
    base = nat_row if nat_row is not None else sum47
    print(f"    一都三県      : {metro:,} 戸 ＝ 全国の {metro / base * 100:.1f}%"
          if base else "    一都三県: 母数が0")
    print("    ↑ template.html の「全国の約半分がこの4都県に」が真かどうかはこの数字で決まる")

    print("\n    都道府県ストック 上位8件（順位の散文もここで決まる）")
    top = sorted(((areas[c]["@name"], stock.get(c, 0)) for c in pref_rows),
                 key=lambda kv: -kv[1])[:8]
    for i, (nm, v) in enumerate(top, 1):
        print(f"      {i}. {nm} {v:,}")

    # --- 問6: 閾値ごとのページ数（一都三県） ------------------------------
    parents = {a.get("@parentCode") for a in areas.values()}
    leaves = [c for c in five
              if c[:2] in CITY_PREFS and not c.endswith("000") and c not in parents]
    tot = sum(stock.get(c, 0) for c in leaves)
    print(f"\n[6] 一都三県の leaf 市区町村 {len(leaves)} 件・合計 {tot:,} 戸")
    print("    閾値        該当数   戸数カバー率")
    for t in THRESHOLDS:
        sel = [c for c in leaves if stock.get(c, 0) >= t]
        cov = sum(stock.get(c, 0) for c in sel) / tot * 100 if tot else 0
        print(f"    {t:>6,}戸以上  {len(sel):>4}件   {cov:5.1f}%")

    print("\n" + "=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())

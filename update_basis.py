# -*- coding: utf-8 -*-
"""e-Stat API から建設ストック時計の基準値を取得し basis.json に書き出す。

取得元: 建築物着工統計 時系列表（年度次）statsDataId=0003119730
        【建築物】構造別　用途別　都道府県別 平成15年度～
        全国・用途「計」・表章項目「床面積の合計」を、構造別に引く。

    py update_basis.py

出力: basis.json （このあと build.py が page.html / index.html を生成する）

前提: 環境変数 ESTAT_APP_ID に e-Stat の appId が入っていること。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/"
STATS_DATA_ID = "0003119730"

# 取りたい構造区分（@cat01 の表示名）
STRUCTURES = ["計", "木造", "鉄筋コンクリート造", "鉄骨鉄筋コンクリート造", "鉄骨造"]

# ---- 建設工事費デフレーター（2020年度基準・月別）----
# こちらは 2026年6月まで提供されており、着工統計と違って毎月更新される。
# ---- 都道府県別 分譲マンション着工戸数（修繕適齢期コホート）----
PREF_ID = "0003119736"          # 住宅着工統計 時系列表【住宅】利用関係別 構造別 建て方別 都道府県別
COHORT = (1988, 2001)           # 2026年時点で築25〜38年＝2〜3回目の大規模修繕期

# ---- 消費者物価指数（総務省・2020年基準・総合・全国）----
CPI_ID = "0003427113"

# ---- 一都三県の市区町村別 住宅ストック（令和5年住宅・土地統計調査）----
# 着工統計（フロー）ではなく現存ストック。修繕の対象はストックなのでこちらが正しい。
# ただし所有関係の軸が無いため「非木造の共同住宅」までしか絞れず、賃貸が混ざる。
CITY_ID = "0004021796"
CITY_PREFS = {"13": "東京都", "14": "神奈川県", "11": "埼玉県", "12": "千葉県"}
CITY_COHORT = ("1981～1990年", "1991～2000年")     # 2026年時点で築26〜45年

DEFLATOR_ID = "0004055083"
DEFLATOR_TAB = "100"          # 表章項目「建設工事費デフレーター」（後方3ヶ月平均ではない方）
# (@cat01 コード, 画面表示名, 主役かどうか)
DEFLATOR_SERIES = [
    ("260", "建築補修（改装・改修）", True),
    ("100", "建設総合", False),
    ("110", "建築総合", False),
    ("120", "住宅総合", False),
    ("130", "木造住宅", False),
    ("140", "非木造住宅", False),
    ("150", "住宅・鉄骨鉄筋コンクリート造", False),
    ("160", "住宅・鉄筋コンクリート造", False),
    ("170", "住宅・鉄骨造", False),
    ("190", "非住宅総合", False),
    ("210", "非住宅・非木造", False),
    ("230", "非住宅・鉄筋コンクリート造", False),
    ("240", "非住宅・鉄骨造", False),
    ("270", "土木総合", False),
    ("720", "鉄筋・在来住宅", False),
    ("820", "鉄筋・事務所その他", False),
]


def _call(endpoint: str, **params) -> dict:
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        sys.exit("環境変数 ESTAT_APP_ID が未設定です。")
    params["appId"] = app_id
    url = BASE + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=120) as res:
        return json.loads(res.read().decode("utf-8"))


def _as_list(v):
    return [v] if isinstance(v, dict) else (v or [])


def _code(classes, cls_id: str, name: str) -> str:
    for c in classes:
        if c["@id"] != cls_id:
            continue
        for i in _as_list(c["CLASS"]):
            if i["@name"] == name:
                return i["@code"]
    sys.exit(f"分類 {cls_id} に「{name}」が見つかりません。表の構成が変わった可能性があります。")


def fetch_deflator() -> dict:
    """建設工事費デフレーターを工事種別ごとに引き、共通の月軸に揃えて返す。"""
    meta = _call("getMetaInfo", statsDataId=DEFLATOR_ID)["GET_META_INFO"]["METADATA_INF"]
    classes = meta["CLASS_INF"]["CLASS_OBJ"]
    tname = {}
    for c in classes:
        if c["@id"] == "time":
            for i in _as_list(c["CLASS"]):
                tname[i["@code"]] = i["@name"]

    raw: dict[str, dict[str, float]] = {}
    for code, label, _ in DEFLATOR_SERIES:
        d = _call("getStatsData", statsDataId=DEFLATOR_ID, cdTab=DEFLATOR_TAB,
                  cdCat01=code, limit=500)
        sd = d["GET_STATS_DATA"]["STATISTICAL_DATA"]
        got = {}
        for v in _as_list(sd["DATA_INF"]["VALUE"]):
            try:
                got[tname.get(v["@time"], v["@time"])] = float(v["$"])
            except (ValueError, TypeError):
                continue
        raw[label] = got
        print(f"  {label:24s} {len(got):3d}ヶ月")

    # 全系列に値がある月だけを共通軸にする
    months = sorted(set.intersection(*(set(v) for v in raw.values())),
                    key=lambda s: (int(s.split("年")[0]), int(s.split("年")[1].rstrip("月"))))
    series = {label: [raw[label][m] for m in months] for label in raw}
    return {
        "months": months,
        "series": series,
        "primary": next(lbl for _, lbl, star in DEFLATOR_SERIES if star),
        "statsDataId": DEFLATOR_ID,
        "base": "2020年度＝100",
        "url": f"https://www.e-stat.go.jp/dbview?sid={DEFLATOR_ID}",
    }


def fetch_cpi(months: list[str]) -> dict:
    """消費者物価指数（総合・全国）を、デフレーターと同じ月軸に揃えて返す。"""
    meta = _call("getMetaInfo", statsDataId=CPI_ID)["GET_META_INFO"]["METADATA_INF"]
    classes = meta["CLASS_INF"]["CLASS_OBJ"]
    tname = {}
    for c in classes:
        if c["@id"] == "time":
            tname = {i["@code"]: i["@name"] for i in _as_list(c["CLASS"])}

    d = _call("getStatsData", statsDataId=CPI_ID, limit=2000,
              cdTab="1", cdCat01="0001", cdArea="00000")
    got = {}
    for v in _as_list(d["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]):
        label = tname.get(v["@time"], "")
        if not label.endswith("月"):
            continue
        try:
            got[label] = float(v["$"])
        except (ValueError, TypeError):
            continue

    missing = [m for m in months if m not in got]
    if missing:
        print(f"  ※ CPI に無い月: {missing[:3]} …計{len(missing)}件。月軸を揃えられません")
    values = [got.get(m) for m in months]
    print(f"  総合（全国）{len([v for v in values if v is not None])}/{len(months)}ヶ月　"
          f"最新 {months[-1]} = {values[-1]}")
    return {
        "statsDataId": CPI_ID,
        "name": "消費者物価指数（総合・全国）",
        "base": "2020年＝100",
        "url": f"https://www.e-stat.go.jp/dbview?sid={CPI_ID}",
        "values": values,
    }


def fetch_city() -> dict:
    """一都三県の市区町村別に、非木造・共同住宅の住宅数を建築の時期別で取る。"""
    meta = _call("getMetaInfo", statsDataId=CITY_ID)["GET_META_INFO"]["METADATA_INF"]
    classes = meta["CLASS_INF"]["CLASS_OBJ"]
    areas, periods = {}, {}
    for c in classes:
        if c["@id"] == "area":
            areas = {i["@code"]: i for i in _as_list(c["CLASS"])}
        if c["@id"] == "cat04":
            periods = {i["@code"]: i["@name"] for i in _as_list(c["CLASS"])}
    order = [periods[k] for k in sorted(periods) if periods[k] != "総数"]

    d = _call("getStatsData", statsDataId=CITY_ID, cdCat01="2", cdCat02="3", cdCat03="00",
              limit=100000)
    sd = d["GET_STATS_DATA"]["STATISTICAL_DATA"]

    raw: dict[str, dict[str, int]] = {}
    for v in _as_list(sd["DATA_INF"]["VALUE"]):
        try:
            raw.setdefault(v["@area"], {})[periods[v["@cat04"]]] = int(v["$"])
        except (ValueError, TypeError, KeyError):
            continue

    parents = {a.get("@parentCode") for a in areas.values()}
    out = {}
    for code, a in areas.items():
        if code[:2] not in CITY_PREFS or code not in raw:
            continue
        vals = raw[code]
        out[code] = {
            "name": a["@name"],
            "pref": CITY_PREFS[code[:2]],
            "parent": a.get("@parentCode"),
            "is_leaf": code not in parents,          # 集計行（政令市・特別区部）を除くため
            "total": vals.get("総数", 0),
            "periods": {k: vals.get(k, 0) for k in order},
        }

    n_leaf = sum(1 for v in out.values() if v["is_leaf"] and len(v["name"]) and v["parent"] != None and len(v["periods"]))
    for pre, nm in CITY_PREFS.items():
        pr = out.get(pre + "000")
        leaves = [v for k, v in out.items() if k[:2] == pre and v["is_leaf"] and k != pre + "000"]
        s_leaf = sum(sum(v["periods"][k] for k in CITY_COHORT) for v in leaves)
        s_pref = sum(pr["periods"][k] for k in CITY_COHORT) if pr else 0
        print(f"  {nm}: 市区町村 {len(leaves):3d} ／ 築26〜45年 県値 {s_pref:,} 対 市区町村合計 {s_leaf:,} "
              f"／ 差 {s_pref - s_leaf:,}")

    return {
        "statsDataId": CITY_ID,
        "url": f"https://www.e-stat.go.jp/dbview?sid={CITY_ID}",
        "survey": "令和5年住宅・土地統計調査（2023年10月1日現在）",
        "filter": "建物の構造=非木造／建て方=共同住宅／階数=総数",
        "cohort": list(CITY_COHORT),
        "order": order,
        "areas": out,
    }


def fetch_prefecture() -> dict:
    """共同住宅・鉄筋コンクリート造・分譲住宅の着工戸数を、都道府県別にコホート集計する。"""
    meta = _call("getMetaInfo", statsDataId=PREF_ID)["GET_META_INFO"]["METADATA_INF"]
    classes = meta["CLASS_INF"]["CLASS_OBJ"]
    tname, aname = {}, {}
    for c in classes:
        if c["@id"] == "time":
            tname = {i["@code"]: i["@name"] for i in _as_list(c["CLASS"])}
        if c["@id"] == "area":
            aname = {i["@code"]: i["@name"] for i in _as_list(c["CLASS"])}

    sel = {
        "cdTab": _code(classes, "tab", "戸数"),
        "cdCat01": _code(classes, "cat01", "共同住宅"),
        "cdCat02": _code(classes, "cat02", "鉄筋コンクリート造"),
        "cdCat03": _code(classes, "cat03", "分譲住宅"),
    }
    d = _call("getStatsData", statsDataId=PREF_ID, limit=5000, **sel)
    sd = d["GET_STATS_DATA"]["STATISTICAL_DATA"]

    lo, hi = COHORT
    agg: dict[str, int] = {}
    by_year: dict[str, dict[str, int]] = {}      # 都道府県ページで年度別に見せるため全期間を残す
    for v in _as_list(sd["DATA_INF"]["VALUE"]):
        label = tname[v["@time"]]
        year = int(label[:4])
        area = aname[v["@area"]]
        try:
            val = int(v["$"])
        except (ValueError, TypeError):
            continue
        by_year.setdefault(area, {})[label] = val
        if lo <= year <= hi:
            agg[area] = agg.get(area, 0) + val

    national = agg.pop("全国", 0)
    total = sum(agg.values())
    print(f"  全国 {national:,} 戸 ／ 47都道府県の合計 {total:,} 戸 ／ 差 {national - total:,} 戸")
    if national != total:
        print("  ※ 差が0でない。全国値と都道府県計が合っていないので原因を確認すること")

    return {
        "cohort": list(COHORT),
        "statsDataId": PREF_ID,
        "url": f"https://www.e-stat.go.jp/dbview?sid={PREF_ID}",
        "filter": "建て方=共同住宅／構造=鉄筋コンクリート造／利用関係=分譲住宅／表章項目=戸数",
        "national": national,
        "units": dict(sorted(agg.items(), key=lambda kv: -kv[1])),
        "by_year": {k: dict(sorted(v.items(), key=lambda kv: (int(kv[0][:4]))))
                    for k, v in by_year.items()},
    }


def main() -> None:
    meta = _call("getMetaInfo", statsDataId=STATS_DATA_ID)["GET_META_INFO"]["METADATA_INF"]
    classes = meta["CLASS_INF"]["CLASS_OBJ"]
    table = meta["TABLE_INF"]

    time_name = {}
    for c in classes:
        if c["@id"] == "time":
            for i in _as_list(c["CLASS"]):
                time_name[i["@code"]] = i["@name"]

    fixed = {
        "cdTab": _code(classes, "tab", "床面積の合計"),
        "cdCat02": _code(classes, "cat02", "計"),
        "cdArea": _code(classes, "area", "全国"),
    }

    series: dict[str, dict[str, int]] = {}
    unit = None
    for s in STRUCTURES:
        d = _call("getStatsData", statsDataId=STATS_DATA_ID, limit=200,
                  cdCat01=_code(classes, "cat01", s), **fixed)
        sd = d["GET_STATS_DATA"]["STATISTICAL_DATA"]
        got = {}
        for v in _as_list(sd["DATA_INF"]["VALUE"]):
            label = time_name.get(v["@time"], v["@time"])
            try:
                got[label] = int(v["$"])
            except (ValueError, TypeError):
                continue  # 「-」「…」等は落とす
            unit = unit or v.get("@unit")
        series[s] = dict(sorted(got.items()))
        print(f"  {s:12s} {len(got):3d}年度分  最新 {list(series[s])[-1]} = {list(series[s].values())[-1]:,} {unit}")

    years = list(series["計"])
    latest = years[-1]

    basis = {
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source": {
            "name": "国土交通省 建築着工統計調査（建築物着工統計 時系列表・年度次）",
            "statsDataId": STATS_DATA_ID,
            "title": table.get("TITLE", {}).get("$") if isinstance(table.get("TITLE"), dict) else table.get("TITLE"),
            "api": "e-Stat API 3.0 getStatsData",
            "url": f"https://www.e-stat.go.jp/dbview?sid={STATS_DATA_ID}",
            "unit": unit,
            "filter": "全国／用途=計／表章項目=床面積の合計",
        },
        "latest_year": latest,
        "annual_floor_area_m2": series["計"][latest],
        "series": series,
        # 手入力の基準値（API では取れない。出所は page 側に明記する）
        "mansion": {
            "b_2024_units": 1480000,
            "c_2034_units": 2932000,
            "d_2044_units": 4829000,
            "stock_total_2024_units": 7131000,
            "source": "国土交通省「マンションを巡る現状」（2025-08-05 公表）",
            "verified": False,
        },
        "dome_m2": 46755,
        # e-Stat では提供されておらず、国交省の公表PDFから読み取った値
        "survey": {
            "name": "令和3年度 マンション大規模修繕工事に関する実態調査",
            "published": "2022-06-17",
            "period": "令和3年7月〜10月調査／回答時点から直近3年間に受注した工事",
            "n": 818,
            "url": "https://www.mlit.go.jp/jutakukentiku/house/content/001619430.pdf",
            "note": "工事金額に共通仮設費は含まない",
            "anchor_note": "調査対象工事はおおむね2018〜2021年の受注。その中心を2020年度と置き、デフレーター基準年（2020年度＝100）に対応させている",
            # 戸あたり工事金額（万円／戸）
            "per_unit": [
                {"label": "1回目", "n": 331, "q1": 90.9, "median": 110.2, "q3": 134.0, "mean": 151.6},
                {"label": "2回目", "n": 194, "q1": 87.8, "median": 106.1, "q3": 129.8, "mean": 112.4},
                {"label": "3回目以上", "n": 242, "q1": 76.8, "median": 97.0, "q3": 125.7, "mean": 106.1},
            ],
            # 分布（n=818）
            "dist": [
                ["25万円以下", 2.1], ["〜50万円", 3.5], ["〜75万円", 9.5], ["〜100万円", 24.7],
                ["〜125万円", 27.0], ["〜150万円", 17.4], ["〜175万円", 6.8], ["〜200万円", 2.3],
                ["200万円超", 2.8], ["無回答", 3.8],
            ],
        },
        "reserve": {
            "name": "令和5年度 マンション総合調査",
            "published": "2024-06-21",
            "url": "https://www.mlit.go.jp/jutakukentiku/house/content/001750161.pdf",
            "monthly_per_unit_yen": 13378,
            "monthly_per_unit_excl_yen": 13054,
            "note": "月／戸当たり修繕積立金の総額の平均（駐車場使用料等からの充当額を含む）",
        },
    }

    print("\n建設工事費デフレーター:")
    basis["deflator"] = fetch_deflator()

    print("\n消費者物価指数:")
    basis["cpi"] = fetch_cpi(basis["deflator"]["months"])

    print("\n都道府県別 分譲マンション着工戸数（%d〜%d年度）:" % COHORT)
    basis["prefecture"] = fetch_prefecture()

    print("\n一都三県の市区町村別 住宅ストック（令和5年）:")
    basis["city"] = fetch_city()

    out = HERE / "basis.json"
    out.write_text(json.dumps(basis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{out} を書き出しました（最新={latest} / {basis['annual_floor_area_m2']:,} {unit}）")


if __name__ == "__main__":
    main()

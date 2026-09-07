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
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
JST = dt.timezone(dt.timedelta(hours=9))
BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/"
STATS_DATA_ID = "0003119730"

# 取りたい構造区分（@cat01 の表示名）
STRUCTURES = ["計", "木造", "鉄筋コンクリート造", "鉄骨鉄筋コンクリート造", "鉄骨造"]

# ---- 建設工事費デフレーター（2020年度基準・月別）----
# こちらは 2026年6月まで提供されており、着工統計と違って毎月更新される。
# ---- 都道府県別 分譲マンション着工戸数（修繕適齢期コホート）----
PREF_ID = "0003119736"          # 住宅着工統計 時系列表【住宅】利用関係別 構造別 建て方別 都道府県別
# 既定の年度範囲。2026年時点で築16〜38年＝1回目を終えた住戸から3回目まで。
# **表示に効くのは build_pref.FLOW_COHORT のほう。** by_year に全年が入っているので、
# 範囲を変えるだけなら取り直しは要らない。ここは basis.json の記録用。
COHORT = (1988, 2010)

# ---- 消費者物価指数（総務省・2020年基準・総合・全国）----
CPI_ID = "0003427113"

# ---- 一都三県の市区町村別 住宅ストック（令和5年住宅・土地統計調査）----
# 着工統計（フロー）ではなく現存ストック。修繕の対象はストックなのでこちらが正しい。
# ただし所有関係の軸が無いため「非木造の共同住宅」までしか絞れず、賃貸が混ざる。
CITY_ID = "0004021796"
# 所有の関係（持ち家／借家）の内訳だけを別表から足す。**見出しの数字は置き換えない。**
# 1棟オーナーの賃貸マンションも商業ビルも大規模修繕はするので、賃貸込みの数が
# 誤りなのではなく、分譲とは別のものというだけ。両方を、それぞれ何かを書いて出す。
# この表は「市区」までで町村が無い（一都三県で26件）。無い市区町村は内訳を出さない。
TENURE_ID = "0004021758"
CITY_PREFS = {"13": "東京都", "14": "神奈川県", "11": "埼玉県", "12": "千葉県"}
# コホートは「築26〜45年」という意味で決まる。表示ラベルを直書きすると、
# e-Stat 側が波ダッシュを ～(U+FF5E) から 〜(U+301C) に直しただけで一致しなくなり、
# しかも下流が .get(k, 0) なので全ページが「0戸」になったまま CI は緑で通る。
# そこでラベルから年を読み取って選ぶ（pick_cohort）。
STOCK_WINDOW = (1981, 2000)                       # 2026年時点で築26〜45年

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


_DASH = str.maketrans({"～": "-", "〜": "-", "~": "-", "－": "-", "—": "-"})


def _label_years(label: str) -> tuple[int | None, int | None]:
    """建築の時期のラベルから、開始年と終了年を読み取る。

    '1981～1990年'   → (1981, 1990)
    '1970年以前'     → (None, 1970)     端が開いているのでコホートには選ばない
    '2021～2023年9月' → (2021, 2023)
    '総数'           → (None, None)
    """
    ys = [int(m) for m in re.findall(r"(?:19|20)\d{2}", label.translate(_DASH))]
    if not ys:
        return (None, None)
    if "以前" in label:
        return (None, ys[0])
    if "以降" in label:
        return (ys[0], None)
    return (ys[0], ys[-1])


def pick_cohort(order: list[str]) -> list[str]:
    """建築の時期の区分から、STOCK_WINDOW にすっぽり収まるものだけを選ぶ。

    2件にならなければ区分の切り方が変わったということなので、黙って続けずに止める。
    ここで止めないと「全ページ0戸だが CI は緑」になる。
    """
    lo, hi = STOCK_WINDOW
    sel = [lb for lb in order
           if (y := _label_years(lb))[0] is not None and y[1] is not None
           and lo <= y[0] and y[1] <= hi]
    if len(sel) != 2:
        sys.exit(f"建築の時期の区分が変わりました。{STOCK_WINDOW} に収まる区分が "
                 f"{len(sel)} 件です（期待2件）。\n  区分: {order}\n  選択: {sel}")
    return sel


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


def fetch_tenure(order: list[str]) -> dict[str, dict[str, dict[str, int]]]:
    """築26〜45年の非木造共同住宅のうち、持ち家（＝分譲）の戸数を市区別に返す。

    **見出しの数字を置き換えるためではなく、内訳として添えるために取る。**
    1棟オーナーの賃貸マンションも商業ビルも大規模修繕はする。賃貸込みの数が
    誤っているのではなく、分譲とは別のものというだけなので、両方を出して
    それぞれが何かを書く。

    この表（0004021758）は「市区」までで町村が無い。返らなかった市区町村は
    呼び出し側で None のままにし、ページには内訳を出さない。0 と書くと
    「分譲が無い」という誤った意味になる。
    """
    meta = _call("getMetaInfo", statsDataId=TENURE_ID)["GET_META_INFO"]["METADATA_INF"]
    classes = meta["CLASS_INF"]["CLASS_OBJ"]
    axis = {c["@id"]: {i["@name"]: i["@code"] for i in _as_list(c["CLASS"])}
            for c in classes if c["@id"] != "area"}
    period = {}
    for c in classes:
        if c["@id"] == "cat05":
            period = {i["@code"]: i["@name"] for i in _as_list(c["CLASS"])}

    missing = [k for k in order if k not in period.values()]
    if missing:
        sys.exit(f"所有関係の表に区分 {missing} がありません。ラベルが変わった可能性があります。"
                 f" この表の区分: {sorted(set(period.values()))}")

    def pull(own: str) -> dict[str, dict[str, int]]:
        d = _call("getStatsData", statsDataId=TENURE_ID,
                  cdCat01=axis["cat01"][own], cdCat02=axis["cat02"]["非木造"],
                  cdCat03=axis["cat03"]["共同住宅"], cdCat04=axis["cat04"]["総数"],
                  limit=100000)
        sd = d["GET_STATS_DATA"]["STATISTICAL_DATA"]
        got = int(sd["RESULT_INF"]["TOTAL_NUMBER"])
        if got >= 100000:
            sys.exit(f"所有関係の表が {got} 件で limit に達しました。分割取得が要ります。")
        acc: dict[str, dict[str, int]] = {}
        for v in _as_list(sd["DATA_INF"]["VALUE"]):
            lb = period.get(v["@cat05"])
            if lb not in order:
                continue
            try:
                acc.setdefault(v["@area"], {})[lb] = int(v["$"])
            except (ValueError, TypeError):
                continue                  # 「-」「X」（秘匿）
        return acc

    # 総数もこの表から取る。**見出しの数（別表）と引き算しないため。**
    # 両表とも100戸単位に丸めてあるので、同じ市区でも数十戸ずれる。
    # 別表どうしを引き算すると、その丸め差が「賃貸の戸数」に化ける。
    owned, whole = pull("持ち家"), pull("総数")
    # 総数の側に出てくる市区は、この表に収録されている市区。そこで持ち家が
    # 取れなかったものは 0 でよい。e-Stat の「-」は該当なし（ゼロ）であって
    # 秘匿ではない（秘匿は「X」）。実例: 木更津市は築26〜45年の分譲が 0 戸。
    # 逆に whole に出てこない市区町村は、表そのものに無い（町村）。区別すること。
    out = {c: {"owned": {k: owned.get(c, {}).get(k, 0) for k in order},
               "total": {k: whole[c].get(k, 0) for k in order}} for c in whole}
    if not out:
        sys.exit("所有関係の表から1件も取れませんでした。軸の指定が変わった可能性があります。")
    print(f"  所有の関係の内訳: {len(out)} 市区（町村はこの表に無い）")
    return out


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
    cohort = pick_cohort(order)
    owned = fetch_tenure(order)

    # cdCat03（階数）は指定しない。4区分ぶんまとめて返させて、総数と内訳を一度に取る。
    # 階数は公表値をそのまま並べるだけにする。「何階だからこの工法」といった
    # 読み方は当社の見解であって公表値ではないので、ページにも書かない。
    floor_name = {}
    for c in classes:
        if c["@id"] == "cat03":
            floor_name = {i["@code"]: i["@name"] for i in _as_list(c["CLASS"])}
    floors = [floor_name[k] for k in sorted(floor_name) if floor_name[k] != "総数"]

    d = _call("getStatsData", statsDataId=CITY_ID, cdCat01="2", cdCat02="3", limit=100000)
    sd = d["GET_STATS_DATA"]["STATISTICAL_DATA"]
    got = int(sd["RESULT_INF"]["TOTAL_NUMBER"])
    if got >= 100000:
        sys.exit(f"住宅ストックが {got} 件で limit に達しました。分割取得が要ります。")

    # raw[area][階数][建築の時期]。階数「総数」が従来どおりの見出し用の数。
    raw: dict[str, dict[str, dict[str, int]]] = {}
    for v in _as_list(sd["DATA_INF"]["VALUE"]):
        try:
            raw.setdefault(v["@area"], {}).setdefault(
                floor_name[v["@cat03"]], {})[periods[v["@cat04"]]] = int(v["$"])
        except (ValueError, TypeError, KeyError):
            continue

    parents = {a.get("@parentCode") for a in areas.values()}
    out = {}
    for code, a in areas.items():
        # 市区町村の行は一都三県ぶんだけ持つ。ページを作るのがそこだけだから。
        # ただし合計行（全国 00000 と都道府県 XX000）は47都道府県ぶん全部を持つ。
        # 都道府県ページの見出し数字をこのストック表に統一するのに要る。
        is_total_row = code.endswith("000")
        if not (is_total_row or code[:2] in CITY_PREFS) or code not in raw:
            continue
        vals = raw[code].get("総数", {})
        out[code] = {
            "name": a["@name"],
            # 一都三県の市区町村は所属県名。合計行は自分の名前（「全国」「北海道」など）
            "pref": CITY_PREFS.get(code[:2], a["@name"]),
            "parent": a.get("@parentCode"),
            "is_leaf": code not in parents,          # 集計行（政令市・特別区部）を除くため
            "total": vals.get("総数", 0),
            "periods": {k: vals.get(k, 0) for k in order},
            # 築26〜45年ぶんの階数の内訳。丸めが100戸単位なので総数とは数十戸ずれる。
            # 解釈は付けずに数字だけ出す（このサイトは分析・見解を載せないと書いている）
            "floors": {f: sum(raw[code].get(f, {}).get(k, 0) for k in cohort)
                       for f in floors},
            # 築年数帯を選べるようにするため、期間ごとにも持つ。API 呼び出しは増えない
            # （もともと全期間ぶん返ってきていて、コホート以外を捨てていただけ）
            "floors_by_period": {f: {k: raw[code].get(f, {}).get(k, 0) for k in order}
                                 for f in floors},
            # 所有の関係の内訳（築26〜45年）。別表から取った持ち家と、その表の総数。
            # 町村はこの表に無いので None のまま。0 と書くと「分譲が無い」の意味になる。
            "tenure": ({"owned": sum(owned[code]["owned"][k] for k in cohort),
                        "total": sum(owned[code]["total"][k] for k in cohort)}
                       if code in owned else None),
            "tenure_by_period": owned.get(code),
        }

    for pre, nm in CITY_PREFS.items():
        pr = out.get(pre + "000")
        leaves = [v for k, v in out.items() if k[:2] == pre and v["is_leaf"] and k != pre + "000"]
        s_leaf = sum(sum(v["periods"][k] for k in cohort) for v in leaves)
        s_pref = sum(pr["periods"][k] for k in cohort) if pr else 0
        print(f"  {nm}: 市区町村 {len(leaves):3d} ／ 築26〜45年 県値 {s_pref:,} 対 市区町村合計 {s_leaf:,} "
              f"／ 差 {s_pref - s_leaf:,}")
        # この検査は前からここに書かれていたが、印字するだけで判定していなかった。
        # 0 が通ると全ページが「0戸」で正常終了する。
        if not s_pref or not s_leaf:
            sys.exit(f"{nm} の築26〜45年が 0 戸です（県値 {s_pref} ／ 市区町村合計 {s_leaf}）。"
                     f"\n  コホート: {cohort}\n  区分: {order}")

    return {
        "statsDataId": CITY_ID,
        "url": f"https://www.e-stat.go.jp/dbview?sid={CITY_ID}",
        "survey": "令和5年住宅・土地統計調査（2023年10月1日現在）",
        "filter": "建物の構造=非木造／建て方=共同住宅／階数=総数",
        "cohort": cohort,
        # 築年数はページ側で 基準年 - この年 として出す。ページに 2026 を直書きすると
        # 年が明けた瞬間に全ページが「2026年時点で築26〜45年」のまま古くなる。
        "stock_window": list(STOCK_WINDOW),
        "order": order,
        "floor_order": floors,
        "tenure": {
            "statsDataId": TENURE_ID,
            "url": f"https://www.e-stat.go.jp/dbview?sid={TENURE_ID}",
            "filter": "所有の関係=持ち家／構造=非木造／建て方=共同住宅",
            "note": "この統計表は市区までで、町村は収録されていません。",
        },
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
        # GitHub Actions のランナーは UTC。naive な now() だと UTC が入り、
        # 画面には「取得日」として日本時間のつもりで出てしまう。JST を明示する。
        "generated": dt.datetime.now(JST).strftime("%Y-%m-%d %H:%M"),
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

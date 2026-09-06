# -*- coding: utf-8 -*-
"""e-Stat API から基準値の更新元データを取ってくる補助スクリプト。

【重要・未検証】
2026-09-06 時点で e-Stat の appId（APIキー）を取得していないため、
このスクリプトは一度も実行して確認していない。骨格のみ。
最初の実行時は必ず --search から始めて、statsDataId を目視で確定すること。

準備:
    1. https://www.e-stat.go.jp/api/ で利用登録し appId を発行
    2. 環境変数に入れる（このフォルダに .env を置かない。平文の資格情報を
       OneDrive 同期下に増やさないため）
         setx ESTAT_APP_ID "取得したappId"

使い方:
    # 統計表を探す（statsDataId を確定する）
    py fetch_estat.py --search "建築物着工統計"

    # 確定した statsDataId の中身を落として生JSONを保存
    py fetch_estat.py --stats-data-id 0003XXXXXX --out raw_chakko.json

取得後の反映は手作業:
    page.html の A_ANNUAL_M2 / B_2024 / C_2034 と、
    「算式と基準値」表の値・出所・更新日を必ず同時に書き換える。
    片方だけ直すと「算式を公開している」という主張そのものが崩れる。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

BASE = "https://api.e-stat.go.jp/rest/3.0/app/json/"


def _call(endpoint: str, params: dict) -> dict:
    app_id = os.environ.get("ESTAT_APP_ID")
    if not app_id:
        sys.exit("環境変数 ESTAT_APP_ID が未設定です。e-Stat で appId を発行してください。")
    params = {"appId": app_id, **params}
    url = BASE + endpoint + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as res:
        return json.loads(res.read().decode("utf-8"))


def _txt(v) -> str:
    """e-Stat は値を素の文字列で返したり {'$': 値} で返したりする。"""
    if isinstance(v, dict):
        return str(v.get("$", ""))
    return "" if v is None else str(v)


def search(word: str, limit: int = 50) -> None:
    data = _call("getStatsList", {"searchWord": word, "limit": limit})
    root = data.get("GET_STATS_LIST", {}).get("DATALIST_INF", {})
    tables = root.get("TABLE_INF", [])
    if isinstance(tables, dict):
        tables = [tables]
    if not tables:
        print("該当なし。検索語を変えてください。")
        return
    print(f"{len(tables)} 件\n")
    for t in tables:
        print(f"{t.get('@id')}  [{_txt(t.get('CYCLE')) or '周期不明'}]  "
              f"調査年月={_txt(t.get('SURVEY_DATE')) or '-'}  "
              f"公開={_txt(t.get('OPEN_DATE'))}  値数={_txt(t.get('OVERALL_TOTAL_NUMBER'))}")
        print(f"    {_txt(t.get('STATISTICS_NAME'))}")
        print(f"    {_txt(t.get('TITLE'))}")


def meta(stats_data_id: str) -> None:
    """統計表の分類軸（何で切れる表なのか）と期間を確認する。"""
    data = _call("getMetaInfo", {"statsDataId": stats_data_id})
    info = data.get("GET_META_INFO", {})
    result = info.get("RESULT", {})
    if str(result.get("STATUS")) != "0":
        sys.exit(f"APIエラー: {result}")
    meta_inf = info["METADATA_INF"]
    ti = meta_inf["TABLE_INF"]
    print(f"{stats_data_id}  {_txt(ti.get('STATISTICS_NAME'))}")
    print(f"  表題  : {_txt(ti.get('TITLE'))}")
    print(f"  周期  : {_txt(ti.get('CYCLE'))}   調査年月: {_txt(ti.get('SURVEY_DATE'))}")
    print(f"  値数  : {_txt(ti.get('OVERALL_TOTAL_NUMBER'))}\n")

    classes = meta_inf["CLASS_INF"]["CLASS_OBJ"]
    if isinstance(classes, dict):
        classes = [classes]
    for c in classes:
        items = c.get("CLASS", [])
        if isinstance(items, dict):
            items = [items]
        names = [i.get("@name", "") for i in items]
        head = "、".join(names[:6])
        more = f" …他{len(names) - 6}件" if len(names) > 6 else ""
        print(f"  @{c.get('@id')} {c.get('@name')}  ({len(names)}件)")
        print(f"      {head}{more}")


def fetch(stats_data_id: str, out: str) -> None:
    data = _call("getStatsData", {"statsDataId": stats_data_id, "limit": 100000})
    result = data.get("GET_STATS_DATA", {}).get("RESULT", {})
    if str(result.get("STATUS")) != "0":
        sys.exit(f"APIエラー: {result}")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    values = data["GET_STATS_DATA"]["STATISTICAL_DATA"]["DATA_INF"]["VALUE"]
    print(f"{out} に保存しました（{len(values):,} 値）。")
    print("※ ここから先の集計は表の構造を見てから書くこと。自動集計はまだ実装していない。")


def main() -> None:
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--search", metavar="WORD", help="統計表を検索して statsDataId を探す")
    g.add_argument("--meta", metavar="ID", help="統計表の分類軸と期間を確認する")
    g.add_argument("--stats-data-id", metavar="ID", help="指定した統計表の生データを取得")
    p.add_argument("--limit", type=int, default=50, help="検索件数（--search 用）")
    p.add_argument("--out", default="raw_estat.json", help="保存先（--stats-data-id 用）")
    a = p.parse_args()

    if a.search:
        search(a.search, a.limit)
    elif a.meta:
        meta(a.meta)
    else:
        fetch(a.stats_data_id, a.out)


if __name__ == "__main__":
    main()

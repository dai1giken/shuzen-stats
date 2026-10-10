# -*- coding: utf-8 -*-
"""公開するページに「3D工事分析」の入口（会社サイトの /3d/cta.js）を1行足す。何度流しても1行だけ（2026-10-10）。

    py add_cta.py          # 足す（足してあるページは触らない）
    py add_cta.py --check  # 足していないページの数だけ出す（書き換えない）

--- 何が出るか -----------------------------------------------------------
cta.js は会社サイトのラクチン野郎側（C:\\dev\\dgk-report-app\\site\\cta\\cta.js）で作り、
dai1giken.co.jp/3d/ に置いてある。ページの見出しの数字の欄（.kpis）の下に説明のカード（3Dの画像・住所の欄）を差し込み、
スクロールしても右下（スマホは下の帯）に「3Dで工事分析」のボタンを出す。
都道府県・市区町村のページでは、その地域の地図から始まる。

--- なぜ build.py の最後で呼ぶのか ---------------------------------------
GitHub Actions の毎月の更新は build.py だけを流し、index.html を作り直す。
ここで足さないと、毎月 index.html から入口が消える。pref/ city/ などは
元データが伸びた月に各 build_*.py で作り直すので、そのあとにもこれを流すこと
（流し忘れても、次に build.py が流れたときに足される）。

--- 置く場所 -------------------------------------------------------------
src は https://dai1giken.co.jp/3d/cta.js（頭から全部書く）。GitHub Pages（dai1giken.github.io）
で見た人も会社サイトの3Dへ来るように。/consultation/ は相談フォームそのものなので足さない。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAG = '<script src="https://dai1giken.co.jp/3d/cta.js" defer></script>'
# make_upload_zip.py の公開ファイルと同じ範囲（consultation は除く）
FILES = ["index.html"]
DIRS = ["pref", "city", "nonres", "deflator", "rent", "reform", "cycle", "cost", "column"]


def targets() -> list[Path]:
    out = [HERE / f for f in FILES if (HERE / f).is_file()]
    for d in DIRS:
        out += sorted((HERE / d).glob("*.html"))
    return out


def add(check: bool = False) -> int:
    todo = 0
    for p in targets():
        s = p.read_text(encoding="utf-8")
        if TAG in s or "</body>" not in s:
            continue
        todo += 1
        if not check:
            # 改行コードはそのまま（\r\n のページは \r\n で足す）
            nl = "\r\n" if "\r\n" in s else "\n"
            i = s.rindex("</body>")
            p.write_bytes((s[:i] + TAG + nl + s[i:]).encode("utf-8"))
    return todo


if __name__ == "__main__":
    check = "--check" in sys.argv
    n = add(check)
    print(f"入口を{'足していないページ' if check else '足したページ'}: {n}件（対象 {len(targets())}件）")

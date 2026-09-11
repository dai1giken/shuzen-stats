# -*- coding: utf-8 -*-
"""本番（dai1giken.co.jp）へ手でアップロードする ZIP を、手元で作る。

    py make_upload_zip.py          # shuzen-stats.zip を作る
    py make_upload_zip.py --out D:\\tmp\\x.zip

通常は GitHub Actions（毎月10日）が同じ ZIP を Release に添付する。
**このスクリプトは、Actions を待たずに手元で同じものが要るとき用。**
中身は `.github/workflows/update.yml` の「公開するファイルだけ集める」と
同じでなければならない。**片方だけ直すと、手で上げたときだけ構成が違う。**

--- 展開先 ---------------------------------------------------------------
**www/htdocs 直下**で解凍する。www 直下ではURLから見えない。
ZIP のトップに shuzen-stats/ と column/ があるので、解凍するだけで正しい位置に入る。

--- 隠しファイル ---------------------------------------------------------
`shuzen-stats/.htaccess` が入る。リポジトリでは `htaccess.txt` という名前で
持っている（ドットで始まるファイルは取り違えやすく、コピーから漏れやすいため）。
中身は `AddCharset UTF-8 .txt` の1行で、**これが無いと llms.txt の日本語が化ける**
（本番の Content-Type が "text/plain" のみで charset を持たないことを実測済み）。

`.nojekyll` は GitHub Pages 専用なので**入れない**。

--- ホスト直下に置くもの -------------------------------------------------
`robots.txt` と `sitemap.xml` が ZIP のトップにもある。これは
/shuzen-stats/ 配下の同名ファイルとは**別物**で、企業サイト全体ぶん。
クローラが読むのはホスト直下の方なので、これを上げないと更新が伝わらない。
"""
from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# /shuzen-stats/ 直下に置くファイル
FILES = ["index.html", "ogp.png", "sitemap.xml", "robots.txt", "llms.txt", "basis.json"]
# /shuzen-stats/ 配下に置くディレクトリ（column は企業サイト側なので入れない）
DIRS = ["pref", "city", "nonres", "deflator"]


def stage(dest: Path) -> None:
    site = dest / "shuzen-stats"
    site.mkdir(parents=True)

    missing = [f for f in FILES if not (HERE / f).is_file()]
    if missing:
        raise SystemExit(f"生成物がありません: {missing}　build.py を先に流してください。")
    for f in FILES:
        shutil.copy2(HERE / f, site / f)

    # 隠しファイル。リポジトリ上の名前と配置後の名前が違う
    shutil.copy2(HERE / "htaccess.txt", site / ".htaccess")

    for d in DIRS:
        src = HERE / d
        if not src.is_dir():
            raise SystemExit(f"{d}/ がありません。build.py を先に流してください。")
        shutil.copytree(src, site / d)

    # 企業サイト側（htdocs/column/）。shuzen-stats/ の外
    shutil.copytree(HERE / "column", dest / "column")

    # ホスト直下（htdocs/ 直下）。/shuzen-stats/ 配下のものとは別物
    for f in ("robots.txt", "sitemap.xml"):
        shutil.copy2(HERE / "_root" / f, dest / f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "shuzen-stats.zip"))
    a = ap.parse_args()
    out = Path(a.out).resolve()

    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "upload"
        dest.mkdir()
        stage(dest)

        files = sorted(p for p in dest.rglob("*") if p.is_file())
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for p in files:
                z.write(p, p.relative_to(dest).as_posix())

        # 数えて出す。「ZIPができた」は中身が正しいことの証明にならない。
        by_top: dict[str, int] = {}
        for p in files:
            by_top[p.relative_to(dest).parts[0]] = by_top.get(
                p.relative_to(dest).parts[0], 0) + 1
        print(f"{out}  {out.stat().st_size:,} bytes")
        print(f"  ファイル数 {len(files):,}")
        for k in sorted(by_top):
            print(f"    {k:<16}{by_top[k]:>5}")

    # 書き出した ZIP を開き直して、隠しファイルが実際に入っているか確かめる。
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        for must in ("shuzen-stats/.htaccess", "shuzen-stats/index.html",
                     "shuzen-stats/deflator/index.html", "column/index.html",
                     "robots.txt", "sitemap.xml"):
            assert must in names, f"ZIP に {must} が入っていません"
        assert not any(n.endswith(".nojekyll") for n in names), \
            ".nojekyll は GitHub Pages 専用です。ZIP に入れてはいけません"
        print("  検査：.htaccess あり／.nojekyll なし／必須ファイルあり")


if __name__ == "__main__":
    main()

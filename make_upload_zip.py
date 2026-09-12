# -*- coding: utf-8 -*-
"""本番（dai1giken.co.jp）へ手でアップロードする ZIP を、手元で作る。

    py make_upload_zip.py               # 全部入り（shuzen-stats.zip）
    py make_upload_zip.py --since HEAD~1   # 前回から変わったものだけ
    py make_upload_zip.py --out D:\\tmp\\x.zip

--- 差分アップロードのすすめ ---------------------------------------------
全部入りは 284ファイル・2.7MB ある。**pref/ city/ nonres/ column/ は
元データが伸びた月しか変わらない**ので、毎月それを上げ直すのは無駄が多い
（コントロールパネルからの手作業だとなおさら）。

`--since <ref>` を付けると、その時点から実際に変わった公開ファイルだけを
集める。ホスト直下の robots.txt / sitemap.xml は git 管理外（_root/）で
差分が取れないので、**この2つは常に入れる**（合わせて数十KB）。

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
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent

# /shuzen-stats/ 直下に置くファイル
FILES = ["index.html", "ogp.png", "sitemap.xml", "robots.txt", "llms.txt", "basis.json"]
# /shuzen-stats/ 配下に置くディレクトリ（column は企業サイト側なので入れない）
DIRS = ["pref", "city", "nonres", "deflator", "rent", "reform", "cycle"]

# 企業サイト側（htdocs/ 直下）。**shuzen-stats/ の中ではない。**
# ここに入れ忘れて DIRS に足すと、/shuzen-stats/consultation/ という
# 誤った場所に公開されて、リンクも canonical も食い違う。
CORP_DIRS = ["column", "consultation"]


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

    # 企業サイト側（htdocs/column/ と htdocs/consultation/）。shuzen-stats/ の外
    for d in CORP_DIRS:
        src = HERE / d
        if not src.is_dir():
            raise SystemExit(f"{d}/ がありません。build.py を先に流してください。")
        shutil.copytree(src, dest / d)

    # ホスト直下（htdocs/ 直下）。/shuzen-stats/ 配下のものとは別物
    for f in ("robots.txt", "sitemap.xml"):
        shutil.copy2(HERE / "_root" / f, dest / f)


def write_dir_entries(z: zipfile.ZipFile, root: Path, files: list[Path]) -> None:
    """フォルダそのものの項目を ZIP に書く。**省略してはいけない。**

    2026-09-12、ディレクトリ項目の無い ZIP を Bizメール&ウェブ の
    コントロールパネルで解凍したところ、**トップのファイルだけが展開され、
    shuzen-stats/ 配下の36ファイルが黙って飛ばされた**（エラーは出ず、画面は
    「解凍されました」と表示した）。中身が古いままなことにも気づきにくい。

    Actions 側は `zip -r` を使っていてディレクトリ項目が入るので通っていた。
    Python の ZipFile.write() はファイルしか書かないので、明示的に足す。
    """
    dirs = set()
    for p in files:
        for parent in p.relative_to(root).parents:
            if parent.as_posix() != ".":
                dirs.add(parent.as_posix())
    for d in sorted(dirs):
        info = zipfile.ZipInfo(d + "/")
        info.external_attr = (0o40755 << 16) | 0x10   # ディレクトリ属性
        z.writestr(info, b"")


def changed_since(ref: str) -> list[str]:
    """ref から今までに変わった／増えた、公開対象のファイルを返す。

    削除（D）は拾わない。**アップロードでは消せない**ので、消したページが
    あるときは手で消す必要がある。件数を出して気づけるようにしてある。
    """
    r = subprocess.run(["git", "diff", "--name-status", ref, "--"],
                       cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"git diff が失敗しました（ref={ref}）:\n{r.stderr.strip()}")

    # **未追跡のファイルは git diff に出ない。**新しいディレクトリを足した直後に
    # --since を使うと、そのディレクトリまるごとが ZIP から黙って抜ける。
    # 2026-09-12 に rent/ で踏みかけた。コミット前でも拾えるようにする。
    u = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                       cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    untracked = [ln.strip() for ln in u.stdout.splitlines() if ln.strip()]

    pub, deleted = [], []
    for path in untracked:
        top = path.split("/")[0]
        if path in FILES or top in DIRS or top in CORP_DIRS:
            pub.append(path)
    if pub:
        print(f"  未コミットの新規ファイルを {len(pub)}件 含めました")
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        st, _, path = line.partition("\t")
        path = path.strip().split("\t")[-1]
        top = path.split("/")[0]
        if not (path in FILES or top in DIRS or top in CORP_DIRS):
            continue          # ソース・README・ワークフローは公開しない
        (deleted if st.startswith("D") else pub).append(path)

    if deleted:
        print(f"  ⚠ 削除されたページが {len(deleted)}件 あります。"
              "アップロードでは消えないので、コントロールパネルで手で消してください:")
        for p in deleted[:10]:
            print(f"      {p}")
    return sorted(pub)


def stage_delta(dest: Path, paths: list[str]) -> None:
    site = dest / "shuzen-stats"
    for rel in paths:
        src = HERE / rel
        if not src.is_file():
            continue
        dst = site / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    # ホスト直下ぶんは git 管理外（_root/）なので差分が取れない。常に入れる。
    for f in ("robots.txt", "sitemap.xml"):
        shutil.copy2(HERE / "_root" / f, dest / f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--since", metavar="REF",
                    help="この git ref から変わった公開ファイルだけを集める（例: HEAD~1）")
    a = ap.parse_args()
    default = "shuzen-stats-delta.zip" if a.since else "shuzen-stats.zip"
    out = Path(a.out).resolve() if a.out else (HERE / default).resolve()

    with tempfile.TemporaryDirectory() as td:
        dest = Path(td) / "upload"
        dest.mkdir()
        if a.since:
            paths = changed_since(a.since)
            if not paths:
                sys.exit(f"{a.since} から公開ファイルの変更はありません。")
            stage_delta(dest, paths)
        else:
            stage(dest)

        files = sorted(p for p in dest.rglob("*") if p.is_file())
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            write_dir_entries(z, dest, files)
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

    # 書き出した ZIP を開き直して確かめる。「ZIPができた」は中身の証明にならない。
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        must = ["robots.txt", "sitemap.xml"]
        if not a.since:
            # 全部入りのときだけ。差分には変わったものしか入らない。
            must += ["shuzen-stats/.htaccess", "shuzen-stats/index.html",
                     "shuzen-stats/deflator/index.html", "column/index.html",
                     "consultation/index.html"]
        for m in must:
            assert m in names, f"ZIP に {m} が入っていません"
        assert not any(n.endswith(".nojekyll") for n in names), \
            ".nojekyll は GitHub Pages 専用です。ZIP に入れてはいけません"
        # **企業サイトの .htaccess を上書きしないこと。**htdocs 直下のそれは
        # 第一技研のサイト本体の設定で、このリポジトリの持ち物ではない。
        assert ".htaccess" not in names, \
            "ZIP のトップに .htaccess があります。企業サイトの設定を壊します"
        # **入れ子のファイルには、必ず親フォルダの項目が要る。**
        # 無いと解凍側が黙って飛ばす（2026-09-12 に本番で実際に起きた）。
        entries = set(names)
        for n in names:
            parts = n.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                d = "/".join(parts[:i]) + "/"
                assert d in entries, \
                    f"ZIP にフォルダ項目 {d} がありません。解凍時に配下が飛ばされます"
        ndirs = sum(1 for n in names if n.endswith("/"))
        print(f"  検査：フォルダ項目 {ndirs} 件あり（無いと解凍で配下が飛ぶ）")
        print(f"  検査：必須ファイルあり／.nojekyll なし／"
              f"トップに .htaccess なし（企業サイトの設定を壊さない）")


if __name__ == "__main__":
    main()

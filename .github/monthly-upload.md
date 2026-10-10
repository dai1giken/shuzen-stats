@yojirofujioka

**__WA__分の統計サイトの更新ファイルができました。** 下の手順でアップロードしてください。所要5分ほどです。

## ダウンロード

__ASSET__

## 手順

1. Bizメール&ウェブの管理画面 → **ファイル** → ファイルマネージャ
2. **ホームディレクトリ / www / htdocs** まで移動する
   （`index.html` や `contact.php` が見える階層。**www 直下ではありません**）
3. **先に、ZIP と同じ名前の4つを名前変更する**（**解凍は上書きしてくれません**。同じ名前が1つでもあると
   「ファイル名またはディレクトリ名はすでに存在します」で止まる・2026-10-10 に本番で確認）
   - `shuzen-stats` → `Rename_shuzen-stats`
   - `column` → `Rename_column`
   - `robots.txt` → `Rename_robots.txt`
   - `sitemap.xml` → `Rename_sitemap.xml`

   ⚠ 名前を変えてから解凍し終わるまでの間、統計ページは表示されません（数分）。手早く進めてください。
   `.htaccess`・`index.html`・`contact.php`・`consultation/`・`3d/` などは触りません
4. **アップロード** で `shuzen-stats.zip` を上げる
5. 上がった `shuzen-stats.zip` の行の **詳細** をクリック → 右下の **解凍**
6. **⚠ 保存先ディレクトリを `ホームディレクトリ/www/htdocs` に変更する**
   既定は「ホームディレクトリ」のままで、**そのまま解凍すると公開されません**。毎回いちばん間違えやすい箇所です
7. **解凍** を実行（`shuzen-stats/`・`column/`・`robots.txt`・`sitemap.xml` の4つができる）
8. `shuzen-stats.zip` を **削除**（公開領域にZIPを残さないため）
9. 下の確認ができたら、`Rename_` を付けた4つを **削除**

## 確認

- https://dai1giken.co.jp/shuzen-stats/ を開いて、ページ下部の「取得日」が新しくなっていること
- https://dai1giken.co.jp/shuzen-stats/city/13112.html を開いて、見出しの数字の下に「3Dで工事分析します」のカードが出ていること
- https://dai1giken.co.jp/column/ を開いて、正常に表示されること

の3つが確認できれば完了です。
困ったら `Rename_` を付けた4つの名前を元に戻せば、前の月の状態に戻ります。

終わったらこの Issue を閉じてください。

---
<sub>この Issue は毎月10日の自動更新で作られています。中身は政府統計の公表値のみです。</sub>

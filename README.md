
# RFC Translater

### 目的
1. RFCの英語を読むのが辛いので、Google翻訳した文を横に並べたものを読みたい。
[RFCの日本語訳リンク集](https://www.nic.ad.jp/ja/tech/rfc-jp-links.html)では原文と日本語訳が別々のページになっていて、日本語訳が正しいのか判断しにくい問題がある
2. RFCの本文は改行されているので、改行を削除した上でGoogle翻訳に貼り付けないと正しく翻訳されない。改行を削除する煩わしさを解決する

### 流れ
1. RFCのインデックス取得 https://tools.ietf.org/rfc/index (fetch_index)
1. RFCスクレイピング https://tools.ietf.org/html/rfcXXXX (fetch_rfc)
2. セクション毎に分割 & 改行の除去 (fetch_rfc)
3. Google翻訳で英語を日本語にする (trans_rfc)
4. セクション毎に英文、日本語文を並べて表示するページの生成 (make_html)
5. 有名なRFCやアクセス数の多いページに対しては、翻訳の修正作業などを行う (人手)

### 注意事項
- 複数ページにわたる図や表は上手に解釈できないことがあります
- 図や表の中に空行が含まれるときも上手に解釈できないことがあります
- RFCのHTMLが例外的な構造になっている場合も上手に解釈できません（特に番号の小さいRFC）
- RFC2220以降を対象とする (http://rfc-jp.nic.ad.jp/copyright/translate.html)

### 開発者向け

動作環境：Python3, MacOS or Windows

```
pip install requests lxml
pip install Mako
pip install tqdm
pip install googletrans==4.0.0-rc1
pip install selenium
```

2021/02/27追記：googletransは安定版の3.0.0だと翻訳できません。
別の翻訳手段として、seleniumによるGoogle翻訳も追加し、デフォルトの翻訳方法とします。
従来の方法を使いたい場合は `--transmode py-googletrans` を指定してください。

現状では、seleniumではFirefoxを使用するため、geckodriverをダウンロードしておいてください。
geckodriverの配置場所は src/trans_rfc.py の WEBDRIVER_EXE_PATH を参照ください。

```bash
python main.py --rfc 123 # RFC 123を翻訳する（取得+翻訳+HTML生成）
python main.py --rfc 123 --fetch # RFCの取得だけ
python main.py --rfc 123 --trans # RFCの翻訳だけ
python main.py --rfc 123 --make # HTMLの生成だけ
python main.py --begin 500 --end 700 # RFC 500〜700 を順番に翻訳する
python main.py --make --begin 500 --end 700 # RFC 500〜700 のHTMLを生成する
python main.py # 未翻訳RFCを順番に翻訳する
python main.py --begin 8000 --only-first # RFC 8000以降の未翻訳RFCを先頭から1つ選択し翻訳する

python main.py --rfc 123 --transmode selenium       # Seleniumを使用してGoogle翻訳(デフォルト)
python main.py --rfc 123 --transmode py-googletrans # googletransを使用してGoogle翻訳
```

生成物

1. fetch_rfc（取得） ... data/A000/B00/rfcABCD.json (段落区切りで取り出した文章)
2. trans_rfc（翻訳） ... data/A000/B00/rfcABCD-trans.json (各文章の翻訳を加えたもの)
3. make_html（生成） ... html/rfcABCD.html (原文と翻訳を並べて表示するHTML)

```bash
python main.py --make-index # インデックスページの作成
```

ローカルで成果物の確認

```bash
python -m http.server
# localhost:8000/htmlにアクセス
```

<br>

---

#### Figs

各RFCから図のみを集めて公開するサイト「RFC Figs」について

```bash
# 1000個のRFC毎に図を集め、JSONファイルで保存する
python3 figs/collect_figures.py --begin 0000 --end 0999 -w figs/data/0000.json
...
python3 figs/collect_figures.py --begin 7000 --end 7999 -w figs/data/7000.json

# JSONをHTMLに変換する
python3 figs/make_html.py 0000
...
python3 figs/make_html.py 7000

# インデックスページの作成
python3 figs/make_index.py
```


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

<br>

## 翻訳を修正したいときは

当サイトをご利用いただきありがとうございます。
翻訳修正の手順は以下の通りです。

### 翻訳修正者

1. GitHub上でForkします。
2. ブランチを切ります。名前は適当なものにします。
2. html/rfcXXXX.htmlの翻訳を修正します。
   - updated_byを「翻訳編集 : 自動生成 + 一部修正」にします。名前などを残したい方は「一部修正(tex2e)」のような感じで書いてください。
   - 見出しは`<h5>`を使います。1番目に英文、2番目に和文を書きます。
      ```html
      <div class="row">
        <div class="col-sm-12 col-md-6">
          <h5 class="text mt-2">
      1.  Introduction
          </h5>
        </div>
        <div class="col-sm-12 col-md-6">
          <h5 class="text mt-2">
      1. はじめに
          </h5>
        </div>
      </div>
      ```
   - 文章は`<p>`を使います。「indent-X」classでインデントの深さを指定します。
      ```html
      <div class="row">
        <div class="col-sm-12 col-md-6">
          <p class="text indent-3">
      Hello, world!
          </p>
        </div>
        <div class="col-sm-12 col-md-6">
          <p class="text indent-3">
      こんにちは世界！
          </p>
        </div>
      </div>
      ```
   - 図表は`<pre>`を使います。英文のみです。
      ```html
      <div class="row">
        <div class="col-sm-12 col-md-12">
          <pre class="text text-monospace">
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- - - - - - - - -
          |  Option Type  |  Opt Data Len |  Option Data
          +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+- - - - - - - - -
          </pre>
        </div>
      </div>
      ```
3. 修正したHTMLをブラウザで開いて正しく表示されるか確認します。
4. Forkしたレポジトリにpushします。
4. GitHub上でPullRequestを出します。

### 管理者

1. PullRequestの修正差分を確認し、HTMLエスケープが適切に行われているかや、XSSに使われる危険なHTMLタグ（`script`, `a`, `img` など）がないことだけ確認する
2. 問題がなければMergeし、ローカルにpullする
3. `main.py --make-json --rfc <対象RFC>` でHTMLからJSONを逆作成し、変更差分を確認
4. `main.py --make --rfc <対象RFC>` でJSONからHTMLを逆作成し、変更差分を確認
5. レポジトリにpushする

TODO: HTMLエスケープ確認作業の一部自動化


<br>

## 開発者向け

### 実装機能
- 文章のみ翻訳し、図や表はそのまま表示する
- 文章がページ区切りで分割されていても1つの段落として翻訳する
- インデントの深さも反映させる
- 箇条書き（o + * - など）の記号はそのまま表示する
- 表題（1.2.～ など）は文字を大きくする
- 原本（英語RFC）へのリンクをスクロールしても常に表示する
- 廃止されたRFCの場合、廃止されたことと修正版RFCへのリンクを表示する（例：RFC2246, RFC2616）

動作環境：Python3 + Windows or MacOS

```
pip install requests lxml
pip install Mako
pip install tqdm
pip install googletrans==4.0.0-rc1
pip install selenium
pip install beautifulsoup4
```

Windowsの場合は、py -m pip に読み替えてください。

2021/02/27 追記：googletrans 3.0.0 が使い物にならないので、SeleniumによるGoogle翻訳に切り替えました。
従来の方法を使いたい場合は `--transmode py-googletrans` を指定してください。

SeleniumではFirefoxを使用しているため、geckodriver のダウンロードが必要です。
geckodriverの配置場所を環境変数 WEBDRIVER_EXE_PATH に指定してから実行してください。
詳細は src/trans_rfc.py の WEBDRIVER_EXE_PATH を参照ください。

```bash
python main.py --rfc 123 # RFC 123を翻訳する（取得+翻訳+HTML生成）
python main.py --rfc 123 --fetch # RFCの取得だけ
python main.py --rfc 123 --trans # RFCの翻訳だけ
python main.py --rfc 123 --make # HTMLの生成だけ
python main.py --begin 2220 --end 9000 # RFC 2220〜9000 を順番に翻訳する
python main.py --make --begin 2220 --end 9000 # RFC 2220〜9000 のHTMLを生成する
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

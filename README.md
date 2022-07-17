
# RFC Translater

### 目的
1. RFCの英語を読むのが辛いので、Google翻訳した文を横に並べたものを読みたい。
[RFCの日本語訳リンク集](https://www.nic.ad.jp/ja/tech/rfc-jp-links.html)では原文と日本語訳が別々のページで、日本語訳が正しいのか判断しにくい問題がある。
2. RFCの本文は改行済みのため、改行を削除してからGoogle翻訳に貼り付けないと正しく翻訳されない。改行を削除する煩わしさを解決する。

### 流れ
1. **src/fetch_index.py**: RFC一覧の取得。取得先： https://tools.ietf.org/rfc/index
2. **src/fetch_rfc.py**: 個別RFCの取得。取得先： https://datatracker.ietf.org/doc/html/rfcXXXX
3. **src/fetch_rfc.py**: セクション毎に分割 & 改行の除去
4. **src/trans_rfc.py**: Google翻訳で英語を日本語に変換
5. **src/make_html.py**: セクション毎に英文と日本語文を並べて表示するページの生成
6. 人手: 有名なRFCやアクセス数の多いページは翻訳修正作業などを行う

### 注意事項
- 複数ページにまたがる図表は適切に解釈できない場合があります。
- 図や表の中に空行が含まれるときも適切に解釈できない場合があります。
- RFCのHTMLが例外的な構造になっている場合も適切に解釈できません (特に番号の小さいRFC)。
- 翻訳はRFC2220以降を対象とします (http://rfc-jp.nic.ad.jp/copyright/translate.html)。

<br>

## 翻訳を修正したいときは

当サイトをご利用いただきありがとうございます。
翻訳修正の手順は以下の通りです。

### 翻訳修正者

1. html/rfcXXXX.htmlの翻訳を修正します。
   - **見出し**は`<h5 class="text mt-2">`を使います。1番目に英文、2番目に和文を書きます。
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
   - **文章**は`<p class="text indent-X">`を使います。「indent-X」classでインデントの深さを指定します。
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
   - **図表やプログラム**は`<pre class="text text-monospace">`を使います。英文のみです。
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
2. 修正したHTMLをブラウザで開いて正しく表示されるか確認します。
3. GitHub上でPullRequestを出します。

### 管理者

1. PullRequestの差分を確認し、HTML構造に問題がないか確認します。
2. PullRequestのブランチをローカルにPullします。
3. `python main.py --make-json --rfc <対象RFC>` でHTMLからJSONを逆作成し、変更差分を確認します。
4. `python main.py --make --rfc <対象RFC>` でJSONからHTMLを作成し、変更差分を確認します。
5. 問題点があれば `git checkout -- html/rfc<対象RFC>.html` で元に戻して、元データの JSON やプログラムの不備を調査します。
6. 問題がなければMergeし、リモートにPushします。

<br>

## 開発者向け

### 実装機能
- 文章のみ翻訳し、図や表はそのまま表示する。
- 文章がページ区切りで分割されていても1つの段落として翻訳する。
- インデントの深さも反映させる。
- 箇条書き（o + * - など）の記号はそのまま表示する。
- 表題（1.2.～ など）は見出しとして文字を大きくする。
- 原本（英語RFC）へのリンクをスクロールしても常に表示する。
- 廃止されたRFCの場合、廃止されたことと修正版RFCへのリンクを表示する (例：RFC2246, RFC2616)。

### 動作環境
Python3 + Selenium (FireFox) on Windows / MacOS / Ubuntu (headless)

以下のライブラリがPythonでの実行に必要です。Windowsの場合は、py -m pip に読み替えてください。
```
pip3 install requests lxml beautifulsoup4 Mako tqdm selenium beautifulsoup4
```

さらに、以下のツールが実行に必要です。
- **Windows**: FireFox のサイトから geckodriver.exe をダウンロードし、src/trans_rfc.py から呼び出せるように環境変数 WEBDRIVER_EXE_PATH に exe のパスを設定ください。
- **Linux (Ubuntu)** の場合は、以下のパッケージをインストールしてください。
    ```
    sudo apt install python3-pip firefox
    ```

### 実行コマンド例

**注意：翻訳処理は非常に時間がかかります。1個のRFCを翻訳するのに短いものは5分、長いものは30分〜1時間程度かかります。**
開発初期には複数のインスタンスを起動して同時並行で24時間回し続けたのを半年くらいやっていました。

#### 取得・翻訳・生成

```bash
python3 main.py --rfc 123 # RFC 123を翻訳する（取得+翻訳+HTML生成）
python3 main.py --rfc 123 --fetch # RFCの取得だけ
python3 main.py --rfc 123 --trans # RFCの翻訳だけ
python3 main.py --rfc 123 --make # HTMLの生成だけ
python3 main.py --begin 2220 --end 10000 # RFC 2220〜10000 を順番に翻訳する
python3 main.py --make --begin 2220 --end 10000 # RFC 2220〜10000 のHTMLを生成する
python3 main.py # 未翻訳RFCを順番に翻訳する
python3 main.py --begin 8000 --only-first # RFC 8000以降の未翻訳RFCを先頭から1つ選択し翻訳する
```

生成物：
1. fetch_rfc（取得） ... data/A000/B00/rfcABCD.json (段落区切りで取り出した文章)
2. trans_rfc（翻訳） ... data/A000/B00/rfcABCD-trans.json (各文章の翻訳を加えたもの)
3. make_html（生成） ... html/rfcABCD.html (原文と翻訳を並べて表示するHTML)

#### トップページの生成

```bash
python3 main.py --make-index # インデックスページの作成
```

生成物：
1. html/index.html (トップページ)


### 確認方法
ローカルで成果物の確認：
```bash
python3 -m http.server
# localhost:8000/htmlにアクセス
```

### その他
RFCを解析した結果、本来プログラムとして解釈すべき部分を文章として解釈してしまった場合、プログラムのインデントを削除してJSON化するツール：
[https://tex2e.github.io/rfc-translater/html/format.html](https://tex2e.github.io/rfc-translater/html/format.html)


<br>

---

<!--
#### Figs

各RFCから図のみを集めて公開するサイト「RFC Figs」について（現在、更新予定はありません）

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
-->

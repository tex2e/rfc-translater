
## 開発者向け

### 要求定義
- RFCを日本語に翻訳し、その訳が正しいのか判断しやすいように表示したい
- 見出しを大きくしたり、サンプルコードは等幅フォントで表示するなど、RFC原文よりも読みやすくしたい

### 要件定義
- レイアウト
  - 原文は左側、対訳は右側に表示すること
  - 表示はレスポンシブデザインにする。PC画面で見る場合は対訳が左右に並び、スマホ画面で見る場合は対訳が上下に並ぶように表示すること
- 内容
  - 文章のみ翻訳し、図や表やサンプルコードはそのまま表示すること
  - 文章がページ区切りで分割されていても1つの段落として翻訳すること
  - インデントの深さも表示に反映させること
  - 箇条書き（o + * - など）の記号はそのまま表示すること（翻訳時は箇条書き記号より後の文字列だけを翻訳する）
  - 表題（1.2.～ など）は見出しとして文字を大きくすること
  - 目次から各セクションへのリンクを貼る
  - 本文中の[RFCxxxx]から別RFCへのリンクを貼る
- ヘッダー
  - 原本（英語RFC）へのリンクを配置し、スクロールしても常に表示すること
  - モード切り替えのボタンを配置し、ダークモードへ切り替えられること
  - 廃止されたRFCの場合、廃止されたことと修正版RFCへのリンクを表示すること (例：RFC2246, RFC2616)
  - RFCのステータス（Proposed Standard / Internet Standard など）を表示すること
  - RFCを発行したWG（ワーキンググループ）を表示すること


### 動作環境
Python 3.12 + Claude Code on Windows / MacOS / Ubuntu

requests, lxml, beautifulsoup4, Mako, xml2rfcなどのライブラリが実行に必要のためインストールしてください。Windowsの場合は、py -m pip に読み替えてください。
```
pip3 install -r requirements.txt
```

### 翻訳の流れ

RFCの取得とHTMLの生成は `main.py` が行い、翻訳は Claude が行います。

| 工程 | 担当 | 内容 |
|-----|-----|-----|
| 取得 | `main.py --fetch` | RFCを取得して段落に分割する (rfcNXXX.json) |
| 翻訳 | Claude のサブエージェント [rfc-translator](.claude/agents/rfc-translator.md) | [AGENTS.md](AGENTS.md) の翻訳スタイルガイドに従って段落を翻訳する |
| 検証 | `main.py --trans-import` と `tools/lint_translation.py` | 訳文の形式と、規範キーワード・識別子の表記を機械的に検証する |
| 生成 | `main.py --make` | 対訳HTMLを生成する (rfcNXXX.html) |

この一連の作業は Claude Code のスキル [translate-new-rfc](.claude/skills/translate-new-rfc/SKILL.md) にまとめてあります。

- **定期実行**: Claude Code のルーティン（クラウドの定期実行）が毎日このスキルを実行し、未翻訳の最新RFCを1件翻訳してPRを作成します。ルーティンの確認・停止は https://claude.ai/code/routines で行います。
- **手動実行**: Claude Code でこのレポジトリを開き、`/translate-new-rfc`（RFC番号を指定するときは `/translate-new-rfc 9999`）を実行します。

### 実行コマンド例

- **取得・生成**

    ```bash
    python3 main.py --rfc 1234 --fetch  # RFCの取得だけ
    python3 main.py --rfc 1234 --make   # HTMLの生成だけ
    python3 main.py --make --begin 2220 --end 10000  # RFC2220〜10000のHTMLを生成する
    python3 main.py --list-untranslated --begin 9000  # RFC9000以降の未翻訳RFCの番号を表示する
    ```

- **翻訳の補助（Claudeが使うコマンド）**

    翻訳対象の抽出と、訳文の検証・適用を行います。訳文そのものは作成しません。

    ```bash
    python3 main.py --rfc 1234 --trans-prepare  # 作業ファイル (rfc1234-midway.json) を作成し、進捗と翻訳単位を表示する
    python3 main.py --rfc 1234 --trans-export --offset 0 --limit 40  # 段落0〜39のうち未翻訳の段落をJSONで出力する
    python3 main.py --rfc 1234 --trans-import batch.json  # 訳文を検証して適用する
    python3 main.py --rfc 1234 --trans-status   # 進捗を表示する
    python3 main.py --rfc 1234 --trans-finish   # 全段落の翻訳完了を確認して rfc1234-trans.json に確定する
    ```

    `--trans-import` に渡すJSONの形式：
    ```json
    {"title_ja": "RFC 1234 - 日本語タイトル", "items": [{"idx": 12, "ja": "訳文"}]}
    ```
    箇条書きの記号や見出し番号が訳文の先頭に残っていない、訳文が空である、などの問題が1件でもあると、何も適用せずにエラーを表示します。
    確定後の `rfc1234-trans.json` に対しても同じコマンドで訳文を修正できます。

- **全ページの作り直し**

    翻訳済みの全RFC・全DraftのHTMLと、トップページ・Draftの一覧ページ・日本語タイトル一覧をまとめて作り直します。
    本文中の `[RFCxxxx]` のリンク先（翻訳済みページがあればサイト内、なければdatatracker）はHTMLの生成時に決まります。
    **新しいRFCの翻訳を追加したときや、テンプレート（templates/）を変更したときに実行してください。**
    実行しないと、既存ページから新しく翻訳したRFCへのリンクがdatatrackerを向いたままになります。
    生成結果は毎回同じになるため、差分が出るのは実際に変化したページだけです（全件で数十秒程度）。
    ```bash
    python3 main.py --make-all
    ```

- **トップページの生成**

    htmlフォルダ内に存在するRFCファイルの一覧から、トップページを作成します。
    同時に、RFCの日本語タイトル一覧（data-rfc-title.json）も作成します。
    ```bash
    python3 main.py --make-index  # インデックス（目次）ページの作成
    ```

- **RFCのステータス・WG・発行年月の一覧作成**

    RFCのステータス・WG・発行年月の一覧を作成して、JSONに保存するためのコマンドです。
    発行年月はRFCページのヘッダー表示と、変遷グラフの横軸（時間軸）に使用します。

    ```bash
    python3 main.py --fetch-status
    ```

- **RFCの日本語タイトル一覧作成**

    翻訳済みJSONから日本語タイトルの一覧を作成して、JSONに保存するためのコマンドです。
    RFCの変遷グラフ（RFCページの「変遷」ボタン）で、リンク先RFCのタイトルを表示するために使用します。
    `--make-index` を実行したときにも同時に作成されるため、単体で作り直したいときに使用します。

    ```bash
    python3 main.py --make-title-json
    ```

- **RFC Draftの翻訳**

    例えば、TLS Encrypted Client Hello (Draft版) である https://datatracker.ietf.org/doc/draft-ietf-tls-esni/ を翻訳したい場合は、以下のコマンドを実行します。
    翻訳の補助コマンドは `--rfc` の代わりに `--draft` を指定しても同じように使えます。
    ```bash
    python3 main.py --draft draft-ietf-tls-esni-14 --fetch
    # （Claudeで翻訳する）
    python3 main.py --draft draft-ietf-tls-esni-14 --make
    python3 main.py --make-index-draft  # インデックスページの作成
    ```

- **RFCの要約作成**

    要約は Claude Code のスキル [summarize-rfc](.claude/skills/summarize-rfc/SKILL.md) で作成します。
    Claude Code で `/summarize-rfc 9446`（番号を省略すると、要約が未作成のRFCが対象）を実行します。
    定期実行の翻訳（translate-new-rfc）でも、翻訳に続けて要約を作成します。

    ```bash
    python3 main.py --list-unsummarized --begin 9000  # 翻訳済みで要約がないRFCの番号を表示する
    python3 main.py --rfc 9446 --summary-check        # 要約 (rfc9446-summary.json) の形式を検証する
    python3 main.py --rfc 9446 --make                 # 要約をHTMLに反映する
    ```

生成物：

| ファイルパス | 説明 | 生成元プログラム |
|-----------|-----|--------------|
| html/data-rfc-list.json | 廃止RFC・WG・発行年月の一覧 | fetch_status.py (取得)
| html/data-rfc-title.json | 全RFCの日本語タイトル一覧 | make_title_json.py (生成)
| data/N000/rfcNXXX.json | 段落区切りの文書 | fetch_rfc.py（取得）
| data/N000/rfcNXXX-midway.json | 翻訳の作業ファイル（確定時に削除） | trans_rfc.py（翻訳の補助）
| data/N000/rfcNXXX-trans.json | 各文章の翻訳を付与した情報 | trans_rfc.py（翻訳の補助）
| data/N000/rfcNXXX-summary.json | RFCの要約 | Claude（作成）、check_summary.py（検証）
| html/rfcNXXX.html | 原文と翻訳を並べて表示するHTML | make_html.py（生成）
| html/index.html | トップページの生成 | make_index.py (生成)
| data/draft/draft-*.json | 段落区切りの文書 | fetch_rfc.py（取得）
| data/draft/draft-*-trans.json | 各文章の翻訳を付与した情報 | trans_rfc.py（翻訳の補助）
| html/draft/draft-*.html | RFCドラフトの原文と翻訳を並べて表示するHTML | make_html.py（生成）
| html/draft/index.html | RFCドラフト一覧のトップページHTML | make_html.py（生成）


### 翻訳結果確認
ローカルで成果物の確認：
```bash
python3 -m http.server
# localhost:8000/htmlにアクセス
```

### 単体テスト
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```
特定のテストのみ実施したい場合
```
python3 -m unittest tests.test_fetch_rfc.TestFetchRfcSectionTitle.test_section_title
```

### Draft版の全RFCのHTMLを再作成する

```bash
find data/draft -name '*' -type f -exec /bin/bash -c '/opt/homebrew/bin/python3 main.py --draft $(basename {} -trans.json) --make' \;
python main.py --make-index-draft
```

### その他

#### 図表・ソースコードをJSONへ変換する
RFCを解析した結果、本来プログラムとして解釈すべき部分を文章として解釈してしまった場合、プログラムのインデントを削除してJSON化するツール：
[https://tex2e.github.io/rfc-translater/html/format.html](https://tex2e.github.io/rfc-translater/html/format.html)



<!--
### Figs

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

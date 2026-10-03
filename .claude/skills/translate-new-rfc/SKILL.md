---
name: translate-new-rfc
description: 未翻訳の最新RFCを1件選び、取得・翻訳（rfc-translator サブエージェント）・検証・要約作成・対訳HTML生成・PR作成までを行う定例作業の手順。定期実行のルーティンから、または「新しいRFCを翻訳して」と依頼されたときに使う。引数にRFC番号を渡すと、そのRFCを対象にする。
---

# 最新RFCの翻訳（定例作業）

未翻訳のRFCを1件翻訳し、対訳HTMLを生成してPRを作成します。

## 実行モード

- 全工程を確認なしで最後まで実行します。途中で「進めてよいか」を尋ねません。
- 1回の実行で翻訳するRFCは1件です。
- `main` へ直接pushしません。成果は必ずブランチとPRで提出します。
- 途中で継続できない問題が起きたら、中途半端な成果をpushせず、何が起きたかを報告して終了します。

## 1. 準備

```sh
python3 -c "import requests, lxml, bs4, mako, xml2rfc" || pip install -r requirements.txt
git fetch origin
```

作業は最新の `origin/main` を起点にします。

## 2. 翻訳対象の選定

引数でRFC番号が指定されていれば、そのRFCを対象にします。指定がなければ次の手順で選びます。

```sh
python3 main.py --list-untranslated --begin 9000     # 未翻訳のRFC番号（昇順）
git ls-remote --heads origin 'claude/translate-rfc*'  # 翻訳済みでPRが未マージのもの
```

- 未翻訳の一覧から、`claude/translate-rfcN` というブランチがすでにリモートにある番号を除きます（PRがマージ待ちのRFCを重複して翻訳しないため）。
- 残った中で最も番号の小さいRFCを対象 `N` とします。
- 対象がなければ「翻訳対象なし」と報告して終了します。ブランチもPRも作りません。

対象が決まったら、作業ブランチを作成します。

```sh
git switch -c claude/translate-rfcN origin/main
```

## 3. 取得と作業ファイルの作成

```sh
python3 main.py --rfc N --fetch
python3 main.py --rfc N --trans-prepare
```

- `--fetch` が `RFCNotFound` になったとき（本文がまだ公開されていないなど）は、そのRFCを飛ばして次の候補で「2.」からやり直します。3件続けて取得できなければ報告して終了します。
- `--trans-prepare` の出力の `batches` が、翻訳を依頼する単位（段落番号の範囲）です。

## 4. タイトルの翻訳と用語表の作成

サブエージェントは担当範囲しか読まないため、RFC全体で訳語がぶれないように、先に用語表を作ります。

1. 冒頭（概要・導入・用語定義の節まで）を読みます。

   ```sh
   python3 main.py --rfc N --trans-export --offset 0 --limit 60
   ```

2. このRFCで繰り返し使われる用語とその訳語を、用語表としてレポジトリの外（一時ディレクトリ）に書き出します（例: `$TMPDIR/rfcN/glossary.md`）。
   - `AGENTS.md` の「9. 用語集」にある語は、その訳語をそのまま載せます。
   - プロトコルの識別子（フィールド名・メッセージ名・略語）は訳さず原文表記のまま使う語として載せます。
   - すでに翻訳済みの関連RFC（このRFCが更新・廃止するRFCなど）が `data/` にあれば、その訳語に合わせます。
3. タイトルを翻訳して適用します。`title_ja` は「RFC N - 」で始め、体言止めにします。

   ```json
   {"title_ja": "RFC N - 日本語タイトル", "items": []}
   ```

   ```sh
   python3 main.py --rfc N --trans-import <上記JSONのパス>
   ```

## 5. 本文の翻訳（サブエージェント）

`batches` の1要素ごとに、`rfc-translator` サブエージェントを1つ起動します。同時に起動するのは4つまでとします。各サブエージェントには次を伝えます。

- RFC番号 `N`、担当範囲の `offset` と `limit`
- 用語表のパス
- 訳文の出力先パス（一時ディレクトリ。例: `$TMPDIR/rfcN/batch-<offset>.json`）

全サブエージェントの完了後に進捗を確認します。

```sh
python3 main.py --rfc N --trans-status
```

- `remaining` が0でなければ、残った `batches` について再度サブエージェントを起動します。
- サブエージェントが報告した「新たに決めた訳語」は用語表に追記し、同じ原語に複数の訳語が当てられていたら1つに統一します（修正は「7.」の方法で適用します）。

## 6. 確定とlint

```sh
python3 main.py --rfc N --trans-finish
python3 -m json.tool data/<帯>/rfcN-trans.json > /dev/null
python3 tools/lint_translation.py --rfc N --format text
```

- `E` で始まるコードは全て修正します。`W` は内容を確認して、訳文の誤りであれば修正します。
- lintの検出が0件になる（または残りが誤検知であると個別に確認できる）まで繰り返します。

## 7. 訳文のレビュー

lintは、原文と照合して機械的に判定できる違反しか検出しません。翻訳した本人とは別の目で、次の観点を確認します。

```sh
python3 main.py --rfc N --trans-export --include-translated --offset <offset> --limit <limit>
```

- **RFC2119キーワードを含む段落は全件**、原文と訳文を突き合わせます。
  - 併記した原語が、そのキーワードが掛かる述語の直後にあるか（別の文や前置きの文に付いていないか）
  - 規範強度が訳語と一致しているか、肯定・否定が反転していないか
  - 段落内の文が欠落していないか
- それ以外の段落は、訳文が原文より極端に短いもの、原文と同じ文字列のままのものを確認します。
- 識別子の表記が原文と一致しているか、用語表の訳語が全体で統一されているかを確認します。

修正は、修正する段落だけを入れたJSONを作り、確定後の翻訳ファイルに適用します。

```sh
python3 main.py --rfc N --trans-import <修正JSONのパス>
```

修正したら「6.」のlintとJSONの構文検証を再実行します。

## 8. 要約の作成

スキル summarize-rfc（`.claude/skills/summarize-rfc/SKILL.md`）の「2.」〜「5.」の手順で、`data/<帯>/rfcN-summary.json` を作成します。

```sh
python3 main.py --rfc N --summary-check
```

## 9. HTMLの生成

```sh
python3 main.py --rfc N --make   # 対訳HTML
python3 main.py --fetch-status   # 廃止・更新の関係、WG、発行年月の一覧
python3 main.py --make-all       # 全ページとトップページ（他ページからのリンク先を更新）
python3 -m unittest discover -s tests -p "test_*.py"
```

`html/rfcN.html` が生成されたこと、`git status` に意図しない変更（翻訳対象と無関係な `data/` の変更など）がないことを確認します。

## 10. コミットとPR

```sh
git add data/<帯>/rfcN-trans.json data/<帯>/rfcN-summary.json html/
git commit -m "翻訳: RFC N を追加"
git push -u origin claude/translate-rfcN
```

`main` 向けのPRを作成します（`gh pr create`、または利用できるGitHub連携のツール）。PRの本文には次を書きます。

- RFC番号と原題・邦題
- 段落数（翻訳した段落数／全段落数）
- lintの最終結果（検出数。残したものがあれば、その理由）
- 原文が曖昧で解釈を選んだ箇所（段落番号と理由）
- 用語表（主要な訳語）

PRを作成する手段がないときは、pushしたブランチ名を報告します。

## 11. 報告

翻訳したRFC、PRのURL、lintの結果、人が確認したほうがよい箇所を簡潔に報告します。

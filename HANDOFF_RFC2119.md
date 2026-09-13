# 引き継ぎ資料: RFC2119規範キーワード注釈ギャップ修正プロジェクト

最終更新: 2026-09-13（30RFC統合コミット完了時点）

## 1. プロジェクトの目的と背景

`data/*/rfcNNNN-trans.json` の日本語訳には、原文のRFC2119規範キーワード
（MUST / SHALL / REQUIRED / SHOULD / RECOMMENDED / MAY / OPTIONAL とそれぞれのNOT形）
に対応する規範強度の注釈 `(KEYWORD)` が抜け落ちている箇所が大量にある。

**根本原因**: `tools/lint_translation.py` の `check_rfc2119()` は

```python
if len(found) != 1:
    return None
```

という実装になっており、**1段落に複数のRFC2119キーワードが含まれる場合は検査を完全にスキップする**。
そのため公式lintの検出数は実態を大幅に過小報告する（RFCによっては公式lint数十件に対し実態100〜300件超、
比率にして10〜20倍のズレが出ることも珍しくない）。この過小報告に気づかず「lintが0件だから完了」と
判断しないこと。

## 2. 絶対に守るべき標準ルール（ユーザーの指示、変更禁止）

- **push・PR作成は絶対にしない。** ローカルコミットのみ。
- **検証は必ず公式lintと自前の複数キーワードスキャナの両方で行う**（後述4節・6節）。公式lintの結果だけを信用しない。
- 識別子（CamelCase、プロトコル名、フィールド名等）は原文と一字一句同じ表記を維持する。
- 注釈は半角括弧、直前に半角スペース1個: `〜しなければなりません (MUST)`。全角コロン・全角括弧が続く場合もその前に半角スペースを入れる。
- **同義語を絶対に混同しない**: SHALL≠MUST, REQUIRED≠MUST, RECOMMENDED≠SHOULD, OPTIONAL≠MAY。原文の字面通りのキーワードを注釈に使う。
- 原文が真に曖昧で解決不能な場合は**Tier1**として扱い、`ja` は変更せず `/tmp/<rfc>_ambiguous.json` に記録する（該当なしでも空の `[]` を必ず作成）。
- 解決はしたが非自明な判断を要した場合は**Tier2**として `/tmp/<rfc>_judgment_calls.json` に `{"idx": N, "reason": "..."}` 形式で記録する（該当なしでも空の `[]` を必ず作成）。
  - **注意**: Codexにこの形式を強く指示しないと、単なる完了idxの配列を吐いて実質的な記録になっていないことがある（RFC6545で発生）。プロンプトで「Tier2は完了idxリストではなく、実際に解釈判断を要した理由を伴う記録である」と明記すること。
- 1RFC完了ごとに、修正段落数・公式lintの結果・Tier1/Tier2件数をユーザーに報告し、次の指示（「続けて」等）を待ってから次のRFCに着手する。
- 大きなRFCで1回のdispatchで終わらない場合は、Codexに正直に「未完了」と報告させ、複数ラウンドに分けて続行する（4節参照）。焦って自動化に頼らせない。
- git commitのメッセージ末尾には以下を必ず付ける:
  ```
  Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
  ```
  （引き継いだAIが別モデルの場合は、そのモデル名に置き換えて構わないが、Co-Authored-By形式自体は維持する）

## 3. 標準ワークフロー（1RFCあたりのループ）

1. **優先順位リストを再スキャンする**（キャッシュを信用しない。前回スキャン後にファイルが更新されている可能性が高い）:
   ```sh
   python3 tools/rank_rfcs.py --scan --dir 2000 3000 4000 5000 6000 7000 8000 9000 10000
   python3 tools/rank_rfcs.py --report --sort priority --limit 15
   ```
2. 上位から順に候補を見る。**W003の件数（公式lint）を鵜呑みにせず**、必ず自前スキャナ（6節）で実質ギャップ数を確認する。
3. **既知のfalse positiveをスキップする**（5節参照。例: RFC2566のidx=642,647）。
4. 対象RFCの本文冒頭〜idx50付近を確認し、RFC固有のキーワード使用上の注意書きがないか確認する
   （例: 「"OPTIONAL"はこの文書ではASN.1の意味でのみ使う」といった自己言明。見逃すと大量誤注釈につながる）。
5. Codexへ委譲する（8節のプロンプトテンプレートを使う）。対象idxリストを正確に列挙し、標準ガードレール（7節の既知バグクラス全部）を明記する。
6. Codexジョブの完了を、状態ファイルを直接ポーリングして検知する（`codex:status`はユーザー専用でAIからは呼べない。8節参照）。
7. 完了したら**必ず**以下を全て実行する（6節の全項目）:
   - 公式lint（`--format text`）
   - 自前複数キーワードスキャナ
   - プレースホルダー混入チェック
   - 重複注釈チェック
   - 注釈直後スペース欠落チェック
   - 動詞活用崩れチェック
   - 内容縮小（60%未満）チェック
   - **変更idx集合 vs 対象idxリストの完全一致チェック**（新規、9節参照）
8. 見つかった問題は手作業で修正する（Editツールで該当箇所を直接編集。スクリプトによる一括置換はしない）。
9. diffのサイズに応じて全文通読するか判断する（目安1000行未満なら全文通読推奨。それ以上でも重要度が高ければ通読する）。**機械チェックが全て0件でも、意味の反転・無関係コピー&ペーストのような欠陥は全文通読でしか見つからない**（7節の②③参照）。
10. 残りギャップがあれば、正確な残idxリストを再計算して次ラウンドを委譲する（4節）。
11. 全て解消したら `python3.12 main.py --make --rfc <番号>` でHTMLを再生成する。
12. `git add data/N000/rfcNNNN-trans.json html/rfcNNNN.html` してコミットする（2節のメッセージ規約に従う）。
13. ユーザーに報告: 修正段落数、公式lint結果、Tier1/Tier2件数。次の指示を待つ。

## 4. 大きなRFCの複数ラウンド分割パターン

1回のdispatchでCodexが全段落を処理しきれない場合（目安: 対象100段落超、またはCodexが「未完了です」と自己申告した場合）:

- Codexには「全部終わらせようと焦るくらいなら、正確に処理できた分だけ完了させて正直に未完了と報告せよ」と明記する。
- 完了報告後、自前スキャナを再実行して**正確な残idxリスト**を取得する。
- 次ラウンドのプロンプトには、残idxリストを正確に列挙し「他は完了済みなので絶対に触るな」と明記する。
- これを残りギャップがなくなるまで繰り返す（過去最大でRFC4912が7ラウンド、RFC3196が4ラウンド、RFC4172が4ラウンド、RFC6545が4ラウンド）。
- ラウンドを重ねるほど累積diffが肥大化する。後半ラウンドの検証は、全文diffではなく「そのラウンドで触った対象idxだけをold/new並べて出力するPythonスクリプト」で見る方が効率的（9節にサンプルコード）。

## 5. 既知のfalse positive（触らないこと）

- **RFC2566** (`data/2000/rfc2566-trans.json`) idx=642, 647: 原文 "This value MUST also not include..." のように
  MUSTとnotの間に語が挟まる構文。公式lintのE002が「原文MUSTに対し訳文の注釈は(MUST NOT)」と誤検出するが、
  実際には意味上MUST NOTであり訳文の`(MUST NOT)`注釈は正しい。優先度リストで最上位に出続けるが対応不要。

## 6. 検証チェックリスト（全項目、毎ラウンド必須）

### (a) 公式lint
```sh
python3 tools/lint_translation.py --rfc <番号> --format text
```
E002（強度不一致）は特に重要。0件になるまで放置しない。

### (b) 自前の複数キーワードスキャナ
`scripts/scan_multikw2.py` として以下の内容で新規作成する（環境をまたいで永続しないため、引き継ぎのたびに再作成が必要）:

```python
#!/usr/bin/env python3
"""RFC2119 multi-keyword gap scanner (Counter diff of EN keyword occurrences vs JA (KEYWORD) annotation occurrences)."""
import json
import re
import sys
from collections import Counter

KEYWORDS = [
    "MUST NOT", "SHALL NOT", "SHOULD NOT", "NOT RECOMMENDED",
    "MUST", "SHALL", "REQUIRED", "RECOMMENDED", "SHOULD", "OPTIONAL", "MAY",
]

EN_PATTERN = re.compile(r"\b(" + "|".join(re.escape(k) for k in KEYWORDS) + r")\b")
JA_PATTERN = re.compile(r"[（(]\s*(" + "|".join(re.escape(k) for k in KEYWORDS) + r")\s*[）)]")


def count_keywords(text, pattern):
    c = Counter()
    for m in pattern.finditer(text):
        c[m.group(1)] += 1
    return c


def main(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    paragraphs = data if isinstance(data, list) else data.get("contents", data.get("paragraphs", data.get("body", [])))

    total_gap = 0
    gap_paragraphs = []

    for idx, para in enumerate(paragraphs):
        if not isinstance(para, dict):
            continue
        if para.get("raw"):
            continue
        text = para.get("text", "") or ""
        ja = para.get("ja", "") or ""
        if not text:
            continue

        en_counts = count_keywords(text, EN_PATTERN)
        if not en_counts:
            continue
        ja_counts = count_keywords(ja, JA_PATTERN)

        diff = en_counts - ja_counts
        if diff:
            gap = sum(diff.values())
            total_gap += gap
            gap_paragraphs.append((idx, dict(en_counts), dict(ja_counts), dict(diff)))

    print(f"検査ファイル: {path}")
    print(f"段落数: {len(paragraphs)}")
    print(f"未対応ギャップ合計: {total_gap} ({len(gap_paragraphs)} 段落)")
    print()
    for idx, en_c, ja_c, diff in gap_paragraphs:
        print(f"#{idx}: EN={en_c} JA={ja_c} 不足={diff}")


if __name__ == "__main__":
    main(sys.argv[1])
```

実行例:
```sh
python3 scripts/scan_multikw2.py data/6000/rfc6545-trans.json
```

**注意**: このスキャナは「EN側キーワード数 > JA側注釈数」の**不足のみ**を検出する。JA側に余分な誤注釈がある
場合（Counter減算は負を0にクリップするため）は検出できない。過剰注釈・誤帰属は公式lintのE002や、
後述の全文diff通読でしか見つからないことがある（7節②）。

### (c) 規範キーワードのグロス誤訳アンチパターン
```sh
grep -c "規範キーワード" data/N000/rfcNNNN-trans.json
```
0件であること。（過去にCodexが本文を直さず「規範キーワード: MUSTは〜を表します」という説明文を追記するだけの
アンチパターンを起こしたことがある。）

### (d) 連続重複注釈
```sh
grep -oE '\((MUST NOT|SHALL NOT|SHOULD NOT|NOT RECOMMENDED|MUST|SHALL|REQUIRED|RECOMMENDED|SHOULD|OPTIONAL|MAY)\)\s*\((MUST NOT|SHALL NOT|SHOULD NOT|NOT RECOMMENDED|MUST|SHALL|REQUIRED|RECOMMENDED|SHOULD|OPTIONAL|MAY)\)' data/N000/rfcNNNN-trans.json | wc -l
```
0件であること。

### (e) 注釈直後のスペース欠落
```python
import re, json
data = json.load(open('data/N000/rfcNNNN-trans.json'))
kws = 'MUST NOT|SHALL NOT|SHOULD NOT|NOT RECOMMENDED|MUST|SHALL|REQUIRED|RECOMMENDED|SHOULD|OPTIONAL|MAY'
pat = re.compile(r'\((?:' + kws + r')\)(?=[^\s。、」）\)])')
for i, p in enumerate(data['contents']):
    ja = p.get('ja', '')
    if pat.search(ja):
        print(i, repr(ja[:120]))
```
ヒットが0件であること。ヒットした場合、**その場でスペースだけ直す前に、EN/JAの対応関係が正しいか必ず確認する**
（9節③のコピー&ペースト汚染バグの再発防止のため）。

### (f) 動詞活用崩れ（辞書形+助動詞テンプレートの直結）
```python
import re, json
data = json.load(open('data/N000/rfcNNNN-trans.json'))
patterns = [
    re.compile(r'[るうくぐつぬぶむ]すべきです'),
    re.compile(r'(うしなければなりません|すしなければなりません|くしなければなりません|つしなければなりません|るしなければなりません)'),
    re.compile(r'(ることがしてもよい|するしてもよい)'),
]
for i, p in enumerate(data['contents']):
    ja = p.get('ja', '')
    for pat in patterns:
        if pat.search(ja):
            print(i, repr(ja[:150]))
```
例: 「適用するすべきです」→正しくは「適用すべきです」。「送り返すしなければなりません」→正しくは「送り返さなければなりません」。

### (g) 内容縮小チェック
```python
import json, subprocess
old_data = json.loads(subprocess.check_output(['git', 'show', 'HEAD:data/N000/rfcNNNN-trans.json']))
new_data = json.load(open('data/N000/rfcNNNN-trans.json'))
for i, (o, n) in enumerate(zip(old_data['contents'], new_data['contents'])):
    oja, nja = o.get('ja', ''), n.get('ja', '')
    if oja and nja and len(nja) < 0.6 * len(oja):
        print(i, len(oja), len(nja))
```
新旧`ja`文字列長比較で60%未満に縮んでいたら内容欠落を疑う。

### (h) 変更idx集合の完全一致チェック（新規、必須）
```python
import json, subprocess
old_data = json.loads(subprocess.check_output(['git', 'show', 'HEAD:data/N000/rfcNNNN-trans.json']))
new_data = json.load(open('data/N000/rfcNNNN-trans.json'))
changed = [i for i, (o, n) in enumerate(zip(old_data['contents'], new_data['contents'])) if o.get('ja', '') != n.get('ja', '')]
print(len(changed), changed)
```
この結果が「本来の対象idxリストの合計」と完全一致するか必ず確認する。1件でも余分があれば、
無関係な段落へのコピー&ペースト汚染を疑う（9節③）。

### (i) JSON妥当性
```sh
python3 -c "import json; json.load(open('data/N000/rfcNNNN-trans.json'))"
```

## 7. 発見済みの欠陥クラス（全19種）

過去のRFCで実際に発生し、修正・ガードレール化してきた欠陥クラス。新規委譲プロンプトには
この全リストを（特に太字の重大なもの）ガードレールとして明記すること。

1. **プレースホルダー文の一括挿入（本プロジェクト最悪の不具合、RFC3196で発生）**: 実際の訳文に一切手を加えず、
   原文と無関係な汎用テンプレート文（例:「この要件では、当該の動作を行ってもよい (MAY)。」）を挿入する。
   `(KEYWORD)`の数は技術的に正しいため、lint・スキャナ・重複チェック・スペースチェック全てを素通りする。
   **原文と訳文を実際に読み比べないと検出不可能。** 対策: 委譲プロンプトで「一時スクリプトによる一括自動挿入を
   絶対禁止、1段落ずつ人間の翻訳者のように手作業で編集せよ」と明記する。
2. **先頭文・非規範文への誤帰属**: 複数文からなる段落で、注釈が実際のキーワード文ではなく先頭の非規範的な
   説明文に付き、本当のキーワード文（多くは段落末尾）が無注釈のまま放置される。EN側キーワード数・種類・
   出現順が変わらないため、Counter差分にも順序シーケンスチェックにも引っかからない。全文通読でしか見つからない。
3. **複文の前置き節への誤爆**（RFC3435で発見）: "in which case" "may optionally" 等の複文構造で、説明的な
   前置き節（多くは小文字の"may"を含む）に誤って注釈が付き、後続の本当の規範文が無注釈になる。
   `grep`で"in which case"/"however.*MUST"等の複文接続詞を洗い出し個別確認するのが有効。
4. **大文字/小文字助動詞の混同**（RFC6545で発見）: 原文に小文字の"should not"/"may"/"shall"（通常の英語、
   キーワードではない）と大文字の"SHOULD NOT"/"MAY"/"SHALL"（本物のキーワード）が同じ段落に混在する場合、
   小文字側に誤って注釈を付け、大文字側を無注釈のまま放置する。自前スキャナ（大文字限定正規表現）では
   検出できないが、**公式lintのE002（強度不一致）が検出する**。委譲プロンプトで「原文キーワードが実際に
   全て大文字であることを1語ずつ確認せよ」と明記する。
5. **否定構造の意味反転**（RFC6545で発見、最も危険）: "No further messages SHOULD be sent"（事実上の禁止）を
   「それ以上のメッセージを送信すべきです」と正反対の意味に訳す。注釈自体（(SHOULD)）は原文の字面と一致する
   ため、lint・スキャナ・順序チェック全てを通過する。**全文diff通読でしか発見できない。** 同様に
   "MUST also not include"（MUSTとnotの間に語が挟まる）のような合成否定にも要注意。
6. **無関係な段落へのコピー&ペースト汚染**（RFC6545で発見、新種）: 対象外の（RFC2119キーワードを含まない）
   段落のja欄が、全く無関係な別段落の内容で丸ごと上書きされる。機械チェック（重複・スペース・順序）は
   偶然引っかかることもあるが本質的には見つけにくい。**対策: 6節(h)の「変更idx集合の完全一致チェック」で
   即座に検出できる。** スペース欠落チェック等でヒットした段落を機械的に「その場で」直す前に、必ずEN/JAの
   対応関係を確認すること。
7. **RFC固有のキーワード意味の特殊指定**（RFC4912で発見）: 文書自身が「"OPTIONAL"はこの文書ではASN.1構文の
   意味でのみ使う」等と明言している場合、その語には注釈を一切付けない。着手前に必ず全文grepで確認する。
8. **verb活用崩れ**（RFC4497で発見）: 注釈テンプレートを動詞の辞書形に直結し文法崩壊させる
   （例:「適用するすべきです」）。スペース欠落チェックをすり抜けることがある（正しい句読点が続く場合）ため、
   専用の正規表現スイープ（6節(f)）が必要。
9. **JSONインデント崩れ**（RFC8912で発見）: `"text"`行が1スペース分ずれる（標準6→5スペース）コスメティックな
   バグ。JSON的には有効だが将来のdiffノイズになる。修正した全段落の`"text"`行インデントも確認する。
10. **既存訳文の重度破損の復元**（複数RFCで発見）: `ja`欄が空文字・原文コピー・意味不明なほど破損している
    既存の（本セッションの作業以前からの）翻訳を発見した場合、注釈追加だけでなく全文を翻訳し直す必要がある。
    Tier2として記録する。
11. **同義語の注記すり替え**: 原文SHALL/REQUIRED/RECOMMENDED/OPTIONALを機械的にMUST/SHOULD/MAYに置き換えると
    E002になる。原語のまま注釈する。
12. **強度スタック誤り**（RFC5280で発見）: SHOULD原文の節にMUST相当の訳文を当てた上で `(MUST)(SHOULD)` と
    2つ注釈を並べる。
13. **changelog/改版履歴内でのキーワード引用**: 「セクションNをOPTIONALからREQUIREDに変更」等、過去の編集を
    記述するだけの文。ただし自前スキャナは生の文字列をカウントするため、文脈的に非規範的でも注釈しないと
    スキャナ上のギャップとして残り続けることがある（RFC3584で許容した前例あり、スキャナがクリーンなら実務上OK）。
14. **識別子の部分文字列に偶然keyword文字列を含むケース**: `MUTUAL-REQUIRED`のような固有名。識別子として
    そのまま残し注釈しない。
15. **属性の定義見出しリスト**: 「-"REQUIRED": each object MUST support the attribute.」のようにキーワード
    自体を定義している見出し語。実際のMUSTには注釈するが、見出し語のREQUIREDには不要。
16. **RFC固有の非標準規範語**（RFC4172で発見）: "is MANDATORY to implement"のようにRFC2119の標準6語に
    含まれない語が規範的に使われる場合、MUSTへの機械的すり替えはせず、原語のまま`(MANDATORY)`と注釈する
    （Tier2記録推奨）。
17. **文書固有の反復構造パターンの見落とし**（RFC7384で発見）: 「Requirement」見出し直後の生きた要件文と、
    「Requirement Level」見出し直後の「The requirement level ... is 'MAY'」という理由説明文の両方が、
    実は生きた規範強度の宣言であり両方に注釈が必要、といった文書固有の構造。着手前に前後複数段落を読んで
    構造を把握してから判断する。
18. **Codexの裏での自己修正**（RFC9171/RFC3821/RFC3584で発見）: dispatchされたCodexタスクが、Agent呼び出しが
    返った後もセンチネルファイルや訳文を裏で改善し続けることがある。検証直前に必ず対象ファイル・センチネル
    ファイルを再読すること。
19. **Tier2センチネルファイルの形式崩れ**（RFC6545で発見）: `{idx, reason}`形式ではなく単なるidxの配列が
    出力され、実質的な判断記録になっていないことがある。プロンプトで期待する正確なJSON形式を明記する。

## 8. Codexへの委譲メカニクス

- Claude Codeの `Agent` ツールで `subagent_type: "codex:codex-rescue"` を使う。
- プロンプト冒頭に必ず `Routing: --model gpt-5.6-terra` を入れる（設定のデフォルトモデル `gpt-6-astra` は
  インストール済みCLIバージョンで動作しないことが判明しているため）。
- `codex-rescue`サブエージェントは1回の呼び出しで「Codexタスクを非同期起動して返る」だけで、その場では
  完了を待てない（1呼び出しにつき1 `task`コールの制約）。戻り値に `task-<id>` の形式でジョブIDが含まれる。
- 完了検知は `codex:status`（ユーザー専用、AIから呼べない）ではなく、ジョブの状態ファイルを直接
  bashループでポーリングする:
  ```sh
  JOBFILE=$(find ~/.claude/plugins/data/codex-openai-codex/state -name "task-<id>.json" 2>/dev/null | head -1)
  until ! grep -q '"status": "running"' "$JOBFILE"; do sleep 25; done
  ```
  これはバックグラウンドのBashコマンドとして実行し、完了通知を待つ。
- **センチネルファイル（`/tmp/<rfc>_ambiguous.json` 等）の存在だけを完了シグナルにしないこと**——Codexが
  作業途中で先に書いてしまうことがある。ジョブ状態ファイルの`"status"`フィールドが信頼できる一次情報。

### 委譲プロンプトのテンプレート骨子

新規RFCへの初回委譲、または継続ラウンドの委譲は、次の要素を全て含める:

```
Routing: --model gpt-5.6-terra

# タスク: data/N000/rfcNNNN-trans.json のRFC2119規範キーワード注釈ギャップ修正

## 背景
（RFC名、被引用数、公式lint件数 vs 自前スキャナ実質件数）

## 対象段落（正確に以下のインデックスのみ）
idx = ...(正確なリスト)...
（継続ラウンドの場合: 「他は完了済みなので絶対に触らないこと」を明記）

## 注釈ルール (AGENTS.md準拠、絶対厳守)
（2節のルール一式を貼る）

## もしjaフィールドが破損していたら
（10番の欠陥クラス対応。Tier2記録。翻訳困難ならTier1）

## 【最重要・絶対厳守】致命的不具合の再発防止
（1番のプレースホルダー禁止を具体例つきで明記）

## 段落数が多い場合の対応方針
（4節。焦らず正直に未完了報告させる）

## 絶対に守るべきアンチパターン回避ルール
（7節の欠陥クラスのうち特に2,3,4,5,6番を具体例つきで明記）

## 曖昧性のエスカレーション
Tier1: /tmp/<rfc>_ambiguous.json （配列、{"idx":N,"reason":"..."}形式、該当なしなら空の[]）
Tier2: /tmp/<rfc>_judgment_calls.json （同上）

## 検証手順
（6節のチェックリスト全項目をCodex自身にも実行させる）
```

## 9. 現在の進捗状況（2026-09-13時点）

### 完了済みRFC（コミット済み・未push）
- **2026-09-13作業分（第5バッチ・7RFC一括コミット）**:
  RFC5305, RFC4512, RFC4513, RFC5104, RFC7848, RFC3703, RFC6374
  （合計331段落の規範キーワード注釈ギャップ解消、LDAPスキーマ構文保持・段落ズレ・ハルシネーション厳密検証済み、公式lint 0/0、HTML再生成完了）
- **2026-09-13作業分（第4バッチ・8RFC一括コミット）**:
  RFC6175, RFC8911, RFC4171, RFC4567, RFC4006, RFC9012, RFC2821, RFC5730
  （合計957段落の規範キーワード注釈ギャップ解消、段落ズレ・ハルシネーション厳密検証済み、公式lint 0/0、HTML再生成完了）
- **2026-09-13作業分（30RFC一括統合コミット）**:
  RFC4807, RFC9325, RFC6130, RFC4271, RFC8995, RFC3344, RFC6376, RFC5101,
  RFC2576, RFC4396, RFC6043, RFC8915, RFC4944, RFC9132, RFC6257, RFC4293,
  RFC3711, RFC4165, RFC6190, RFC5733, RFC5036, RFC5901, RFC5066, RFC7530,
  RFC9174, RFC5707, RFC6020, RFC4861, RFC3551, RFC6545
- **2026-09-12以前のコミット**:
  RFC7384, RFC4172, RFC4912, RFC3196, RFC4497, RFC8912, RFC3584, RFC3821, RFC9171,
  RFC9071, RFC3435, RFC2707, RFC3726, RFC6378, RFC5280, RFC5654, RFC3315, RFC9051, RFC7826, RFC4918,
  RFC6121, RFC8415, RFC10034/35/37/38/42（バンドル）, RFC6733, RFC2566 ...
（正確な全履歴は `git log --oneline --grep="annotation gaps"` で確認できる。）

### 次にやること
1. 優先順位リストを再スキャンする（3節手順1）。**直近のキャッシュは古い**（RFC6545が上位に残っているのは
   完了前のスナップショットのため、rescan後は消える）。
2. RFC2566（idx=642,647のfalse positive、5節参照）は自動スキップし、次点の実RFCに着手する。
3. 以降は3節の標準ワークフローを繰り返す。ユーザーからの「続けて」1回につき1RFC完了が基本サイクル。

### より詳細な履歴を見るには
Claudeの永続メモリファイル
`/Users/mako/.claude/projects/-Users-mako-Documents-pgm-python-rfc-translater/memory/rfc-translation-lint-workflow.md`
に、各RFCごとの詳細な作業ログ（発見した欠陥の具体例、コミットハッシュ、Tier1/2件数等）が時系列で
記録されている。Claude以外のAIが引き継ぐ場合はこのファイルを直接読めないことがあるため、本ドキュメントに
主要な知見は集約したが、より深い経緯が必要な場合はユーザーにこのファイルの中身を貼ってもらうよう頼むとよい。

## 10. その他の運用上の注意

- このリポジトリは外部から `git pull` されることがあり、未コミットの変更が上書きされるリスクがある。
  作業開始前に `git fetch && git log --oneline main..origin/main` で乖離を確認する。
- 大量修正作業は早めにコミットする。
- HTML再生成は `python3.12 main.py --make --rfc <番号>` で行う（`figs/make_html.py` 単体では
  前提ファイルが無く失敗する）。
- 一時ファイルは `/tmp/` ではなく、可能なら作業用スクラッチディレクトリを使う（環境によって異なる）。
  ただし本プロジェクトの慣習として、Tier1/Tier2センチネルファイルは `/tmp/<rfc>_ambiguous.json` /
  `/tmp/<rfc>_judgment_calls.json` に固定で置く運用を継続している。

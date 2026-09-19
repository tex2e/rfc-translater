# 引き継ぎ資料: 図・表・数式の段組み破壊の修復プロジェクト

最終更新: 2026-09-19（RFC2554の単一行ABNF取りこぼし対応を追加）

---

## 1. プロジェクトの目的と背景

`data/*/rfcNNNN-trans.json` には、原文RFCの図・表・数式が**段組みを失った1行のベタテキスト**として
格納され、さらにその壊れた状態のまま日本語に翻訳されてしまっている段落が大量にあった。

例（RFC2623）:

```
"text": "AUTH_NONE none AUTH_SYS sys AUTH_DH dh AUTH_KERB4 krb4",
"ja":   "AUTH_NONEなしAUTH_SYS sys AUTH_DH dh AUTH_KERB4 krb4"
```

本来はこうあるべきだった:

```
AUTH_NONE    none
AUTH_SYS     sys
AUTH_DH      dh
AUTH_KERB4   krb4
```

### 根本原因

RFC8650未満のRFCはTXT版から本文を組み立てている（`src/application/usecase/fetch_rfc_txt.py`）。
図表かどうかの判定は `src/domain/valueobject/rfc/contents/paragraph.py` の
`Paragraph._find_code_pattern()` が行い、`is_code=True` なら `raw: true` として翻訳対象から外れる。

この判定が図表を取りこぼすと、その段落は「本文」とみなされ、`Paragraph.__init__` の末尾で

```python
self.text = re.sub(r'\n *', ' ', self.text)   # 複数行を1行にまとめる
self.text = re.sub(r' +', ' ', self.text)     # 連続した空白を1つにまとめる
```

の平坦化を受ける。**この時点で段組み情報は復元不能な形で失われ**、そのまま翻訳される。

取りこぼしの主な経路:

- `self.is_code = not self._find_list_pattern(self.text) and self._find_code_pattern(self.text)`
  — 段落が `o `, `- `, `1. ` 等で始まると `_find_list_pattern` が先に成立し、図表判定が**拒否**される
- `elif self.is_code and self.is_section_title: self.is_code = False` — 短い図表が見出しと誤認される
- `_find_code_pattern` のヒューリスティクス自体が、左揃えのプロトコル例（SMTP/SIP/LDAP対話、
  HTTPヘッダ、LDIF、MIME）や中央寄せの数式を拾えない

### 方針（ユーザーの明示指示）

> raw:trueの判定処理を修正するのではなく、すでに翻訳済みのファイルに対して図や表・数式が
> 壊れている場合のみ、原本のRFCのtxtを参照して、インデントも調整しながら、正しい原文をjsonに入れる

**`src/` のパイプラインは一切変更していない。** 修復は `data/*/rfc*-trans.json` に対する
後追いの一括処理として実装した。

---

## 2. 絶対に守るべきルール（ユーザーの指示）

- **push・PR作成は絶対にしない。**
- **今回のセッションでは git commit もしていない**（ユーザーが「コミットしない」を選択）。
  作業ツリーに変更が残っている状態で引き継いでいる。コミットする場合は必ずユーザーに確認すること。
- 図表ブロックの既存 `ja` は**空文字にする**（`raw: true` の段落は翻訳しないという既存規約 E004 に従う）。
  ユーザーは「空にする（raw規約どおり）」を選択済み。退避ログは不要と判断された。
- 判定ロジック（`src/domain/valueobject/rfc/contents/paragraph.py`）は**変更しない**。
- git commitのメッセージ末尾には以下を付ける:
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  ```
  （引き継いだAIが別モデルの場合はモデル名を置き換えてよいが、Co-Authored-By形式自体は維持する）

---

## 3. 作成したツール: `tools/fix_broken_figures.py`

**新規ファイル。git未追跡（`git add` されていない）。**

### アルゴリズム

1. 原本のRFC TXT（`https://www.rfc-editor.org/rfc/rfcNNNN.txt`）を取得し `.cache/rfc-txt/` にキャッシュ
2. `fetch_rfc_txt.py` のページ区切り除去・ページ跨ぎ結合を再現（`remove_page_breaks()`）し、
   ページ境界の両側が独立した構文定義の場合だけ結合せず、`\n\n+` で段落ブロックに分割
3. 空白正規化キー（`normalize()`: BREAK制御文字と行末ハイフン結合を吸収し `\s+`→空白・小文字化）で
   `difflib.SequenceMatcher` により **JSONの段落列 ↔ 原文ブロック列** を対応付ける
4. `equal` オペコードの範囲、つまり**正規化後が完全一致するブロックだけ**を修復対象にする
   （これが取り違えを構造的に防ぐ最重要の安全装置）
5. 原文ブロックが「図・表・数式としての配置」を持つか、本文に誤分類された構文定義であり、かつ通常の本文の折り返しでない場合のみ破損と判定
6. 修復内容:
   | フィールド | 値 |
   |---|---|
   | `text` | 原文ブロック（dedent済み） |
   | `indent` | 原文の字下げ幅 |
   | `raw` | `true` |
   | `ja` | `""` |

`raw: true` の段落は `templates/rfc.html` で `<pre>` に `indent` 分の字下げを付けて描画されるため、
これで原文の桁位置が正確に再現される。

### 破損判定の内訳（`detect_reasons()` / `is_prose_reflow()` / `has_hard_code_signal()`）

| 根拠 | 条件 |
|---|---|
| `code` | 既存の `Paragraph._find_code_pattern()` が成立（`_find_list_pattern` の拒否を経由しない） |
| `cols=N` | 行内に3連以上の空白（列揃え）を持つ行が2行以上。本文の「. 」直後の2連空白と区別するため3連以上 |
| `art=N` | 罫線・矢印（`+--`, `----`, `<--`, `-->`, `/\` 等）が3個以上 |
| `formula` | 6行以下・字下げが3種類以上・列揃え1行以上・数式記号あり（中央寄せの数式） |
| `grammar` | ABNF/BNFなどの規則定義。既存コード判定との合意、ABNF固有記号、複数の定義行のいずれかを必須とし、`ANS = stop means ...`のような説明文を除外 |

そのうえで `is_prose_reflow()`（列揃えがなく、2行目以降の字下げが一定＝通常の本文の折り返し）に
該当するものは除外する。**ただし** `has_hard_code_signal()`（罫線だけの行／`S: `・`C: ` 対話／
HTTPリクエスト行・ステータス行／hexdump／`ヘッダ名: 値` 形式の行が3行以上）が成立する場合は
本文とはみなさず修復対象にする。

2026-09-19の追加修正で、単一行の構文定義もhard code signalとして扱うようにした。従来は
`is_prose_reflow()`が単一行を無条件に本文扱いしていたため、RFC2554の
`UPALPHA = %x41-5A`などが翻訳されていた。また、ページ境界の両側が独立した構文定義なら
結合しないようにし、同RFCの`continue_req`と`CR`を別ブロックとして正しく対応付けた。

RFC2554ではこの追加判定で15段落を修復し、単独のコマンド構文2段落も手動で`raw: true`に
修正した。全RFCへのドライランでは600 RFC・2036段落が追加候補になったため、ABNF固有記号、
Formal Syntax等の文脈、数式除外を組み合わせた`--high-confidence-grammar`を追加した。
この高確度条件に一致した226 RFC・644段落は全件適用済み。さらに、引用終端を含み、隣接する
`raw`段落が構文規則である候補を同じ構文ブロックとみなす条件を追加した。判定は固定点まで
反復するため、連続する規則列も1回の実行で取り切る。この条件で100 RFC・322段落を追加適用した。
広義候補2036件のうち、この時点では合計966件を高確度として修復済みである。

その後、ABNFの増分選択演算子`=/`が高確度条件には存在する一方、前段の候補生成では演算子を
除いた右辺だけを検査していたため到達不能になっていることが判明した。`=/`を候補生成でも認識し、
`=`または`=/`の直後で改行する規則にも対応した。RFC3977の
`The =/ notation of ABNF ...`のような説明文は、段落全体の文末とABNFコメントを使って除外する。
この修正で52 RFC・86段落を追加修復した。RFC5259の2規則が1段落に誤結合された箇所は、原本の
2ブロックへ個別に復元し、再対応可能になった直前の平坦化済み規則も復元した。

この `has_hard_code_signal` は後から追加した。左揃えのプロトコル例は列揃えも字下げ差も持たず、
`is_prose_reflow` だけでは本文の折り返しと区別できずに取りこぼしていたため。

### 使い方

```sh
# 検出のみ（既定）
python3 tools/fix_broken_figures.py --rfc 2313 2246
python3 tools/fix_broken_figures.py --dir 3000 --format summary

# 修復を書き込む
python3 tools/fix_broken_figures.py --dir 3000 --apply --format summary --sleep 0

# 高確度のABNF/BNF構文定義だけを全帯へ適用
python3 tools/fix_broken_figures.py --all --high-confidence-grammar --apply --sleep 0

# raw化済みだが平坦化された段落の改行・字下げを復元
python3 tools/fix_broken_figures.py --all --raw-layout --apply --sleep 0

# JSONレポート
python3 tools/fix_broken_figures.py --dir 3000 --format json -o report.json
```

| オプション | 説明 |
|---|---|
| `--rfc N...` | 対象RFC番号 |
| `--dir N...` | 対象データディレクトリ（例: `2000 3000`） |
| `--all` | RFC8650未満をすべて |
| `--apply` | JSONに書き込む（省略時は検出のみ） |
| `--high-confidence-grammar` | ABNF固有記号・Formal Syntax等の文脈、または確定済み構文規則との隣接条件を満たす高確度の構文定義だけに限定 |
| `--raw-layout` | `raw: true`段落の正規化内容が原本と一致する場合に、改行・空白・indentを原本どおりに復元 |
| `--format` | `detail`(既定) / `summary` / `json` |
| `--sleep` | TXT取得の間隔秒（キャッシュ済みなら `0` でよい） |

**べき等**。既に `raw: true` の段落はスキップするので、何度実行しても追加検出分だけが反映される。

### 原文TXTのキャッシュ

`.cache/rfc-txt/`（gitignore済み・364MB・6315件）に取得済み。**再取得は不要。**
消えた場合は rsync で一括取得できる（HTTP個別取得より礼儀正しく速い）:

```sh
python3 -c "
import glob,re
ns=sorted({int(re.search(r'rfc(\d+)-trans',p).group(1)) for p in glob.glob('data/*/rfc*-trans.json')})
open('.cache/rfc-files.txt','w').write('\n'.join(f'rfc{n}.txt' for n in ns if n<8650)+'\n')
"
rsync -a --files-from=.cache/rfc-files.txt ftp.rfc-editor.org::rfcs-text-only/ .cache/rfc-txt/
```

---

## 4. 実装上の注意点（ハマりどころ）

### (a) BREAK（ページ跨ぎ制御文字 `\x07\x07\x07`）の処理順序

`Paragraph` は `textwrap.dedent()` した**後**に BREAK を改行へ戻すため、ページをまたいだ行にだけ
次ページ側の字下げ（通常3スペース）が本文に残る。これは既存パイプラインのバグでもある。

本ツールの `dedent_block()` は**先に BREAK を改行へ戻してから**字下げを測ることでこれを回避している。
この扱いをやめると、桁位置一致が 3826→3524 件（data/2000 帯）に落ちることを実測で確認済み。

```python
def dedent_block(chunk: str) -> tuple[str, int]:
    src = chunk.replace(BREAK, '\n').lstrip('\n').rstrip()
    lines = src.split('\n')
    widths = [len(ln) - len(ln.lstrip(' ')) for ln in lines if ln.strip()]
    indent = min(widths) if widths else 0
    body = '\n'.join(ln[indent:] if ln.strip() else '' for ln in lines)
    return body, indent
```

字下げは**空白のみ**で測っている（タブ始まりの行は字下げ0とみなしタブを削らない）。
描画側が `' ' * indent` で復元するため、タブを含む共通プレフィックスを剥がすと桁がずれるため。

### (b) 既存JSONは生成時期によってパイプラインのバージョンが違う

同じRFCでも、現行コードで再生成した結果と既存JSONが一致しないことがある（段落数がずれるRFCもある）。
そのため**位置による対応付けは使えず**、`difflib.SequenceMatcher` による系列アラインメントが必須。

### (c) 既存JSONには BREAK制御文字がそのまま残っている段落がある

`re.sub(BREAK + r'\s+', ' ', text)` は BREAK の直後が空白でない場合にマッチしないため、
`\x07\x07\x07` が `text` に残留しているケースがある（例: RFC4089）。
検証スクリプトで新旧を比較する際は、BREAK を空白として正規化しないと偽の不一致が出る。

### (d) 行末ハイフン結合

本文の平坦化は `re.sub(r'([a-zA-Z])-\n *', r'\1-', text)` で行末ハイフンを結合する。
復元後の原文は結合していないため、新旧比較時はこれも吸収する必要がある（`normalize()` が対応済み）。

---

## 5. 検証手順（全項目・毎回必須）

一時スクリプトは環境をまたいで永続しないため、全文を以下に掲載する。
リポジトリ直下で実行すること。

### (a) 不変条件チェック（最重要）

「復元後の原文を平坦化すると変更前の本文に一致する」ことを全件で確認する。
これが通れば**別段落との取り違えが起きていないことが機械的に保証される**。

```python
# verify_figures.py
"""fix_broken_figures.py の変更が不変条件を満たすかをHEADと比較して検証する"""
import importlib.util, json, re, subprocess, sys
from collections import Counter

spec = importlib.util.spec_from_file_location('fbf', 'tools/fix_broken_figures.py')
fbf = importlib.util.module_from_spec(spec); spec.loader.exec_module(fbf)
normalize = fbf.normalize   # ツール本体と同じ正規化 (BREAK・行末ハイフン結合を吸収)

out = subprocess.run(['git', 'status', '--porcelain', '--', 'data/'],
                     capture_output=True, text=True).stdout.splitlines()
files = [l[3:].strip() for l in out if l.strip().endswith('-trans.json')]
print(f'変更ファイル: {len(files)}')

p = subprocess.Popen(['git', 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def flatten(text: str) -> str:
    """Paragraph が本文に対して行う平坦化を再現する"""
    t = re.sub(r'([a-zA-Z])-\n *', r'\1-', text)
    t = re.sub(r'\n *', ' ', t)
    return re.sub(r' +', ' ', t)

fail = Counter(); stat = Counter(); samples = []
for f in files:
    cur = json.load(open(f, encoding='utf-8'))
    p.stdin.write(f'HEAD:{f}\n'.encode()); p.stdin.flush()
    head = p.stdout.readline().decode().strip()
    if 'missing' in head:
        fail['head欠落'] += 1; continue
    old = json.loads(p.stdout.read(int(head.split()[2]))); p.stdout.read(1)

    a, b = old.get('contents') or [], cur.get('contents') or []
    if len(a) != len(b):
        fail['contents件数が変化'] += 1; continue
    if {k: v for k, v in old.items() if k != 'contents'} != {k: v for k, v in cur.items() if k != 'contents'}:
        fail['メタ情報が変化'] += 1

    for i, (o, n) in enumerate(zip(a, b)):
        if o == n:
            stat['未変更'] += 1
            continue
        # 手動の訳修正 (text/indent を変えず ja だけ直したもの) は図表修復とは別扱い
        if o.get('text') == n.get('text') and o.get('indent') == n.get('indent'):
            stat['手動の訳修正'] += 1
            continue
        stat['図表修復'] += 1
        if n.get('raw') is not True:
            fail['raw!=true'] += 1
        if n.get('ja') != '':
            fail['ja!=空'] += 1
        if o.get('raw'):
            fail['変更前がraw'] += 1
        if flatten(n.get('text') or '').strip() != (o.get('text') or '').strip():
            if normalize(n.get('text') or '') != normalize(o.get('text') or ''):
                fail['本文が原文と対応しない'] += 1
                if len(samples) < 5:
                    samples.append((f, i, o.get('text'), n.get('text')))
            else:
                stat['空白差のみ(許容)'] += 1
        if set(n) - set(o) - {'raw'} or set(o) - set(n):
            fail['キー構成が不正'] += 1

print('段落:', dict(stat))
print('違反:', dict(fail) if fail else 'なし')
for f, i, o, n in samples:
    print(f'\n!! {f} #{i}\n 旧: {o[:160]!r}\n 新: {n[:160]!r}')
print('\n=> ' + ('OK' if not fail else 'NG'))
sys.exit(1 if fail else 0)
```

### (b) 桁位置チェック

`indent` 込みの描画結果の全行が、原文TXTに**桁位置ごと**存在することを確認する。

```python
# verify_columns.py
"""復元した図表の桁位置が原文TXTと一致するかを全変更ファイルで検証する"""
import json, re, subprocess, textwrap, sys
from collections import Counter

out = subprocess.run(['git', 'status', '--porcelain', '--', 'data/'],
                     capture_output=True, text=True).stdout.splitlines()
files = [l[3:].strip() for l in out if l.strip().endswith('-trans.json')]
print(f'変更ファイル: {len(files)}')

p = subprocess.Popen(['git', 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
stat = Counter(); bad = []
for f in files:
    num = int(re.search(r'rfc(\d+)-trans', f).group(1))
    cur = json.load(open(f, encoding='utf-8'))
    p.stdin.write(f'HEAD:{f}\n'.encode()); p.stdin.flush()
    h = p.stdout.readline().decode().strip()
    if 'missing' in h:
        stat['HEADに存在しない'] += 1; continue
    old = json.loads(p.stdout.read(int(h.split()[2]))); p.stdout.read(1)
    if len(old['contents']) != len(cur['contents']):
        stat['!! contents件数が変化'] += 1; continue
    try:
        txt = open(f'.cache/rfc-txt/rfc{num}.txt', encoding='ascii', errors='ignore').read()
    except FileNotFoundError:
        stat['原文TXT未取得'] += 1; continue
    txt_lines = set(txt.replace('\r', '').split('\n'))
    for o, n in zip(old['contents'], cur['contents']):
        if o == n:
            continue
        rendered = textwrap.indent(n['text'], ' ' * n['indent'])
        miss = [l for l in rendered.split('\n') if l.strip() and l not in txt_lines]
        if miss:
            stat['!! 行不一致'] += 1
            if len(bad) < 8:
                bad.append((f, n['indent'], miss[:2]))
        else:
            stat['全行が原文TXTと桁位置ごと一致'] += 1
print(dict(stat))
for f, ind, m in bad:
    print(f'\n!! {f} indent={ind}')
    for l in m:
        print('   ', repr(l))
sys.exit(1 if any(k.startswith('!!') for k in stat) else 0)
```

**注意**: 手動で `ja` だけ直した散文段落はここで「行不一致」として出るが、これは正常
（散文は原文TXTの1行と一致しないため）。現在3件が該当する（6節参照）。

### (c) 公式lint

```sh
python3 tools/lint_translation.py --format summary
```

E001/E002/E004/E007/E008 がすべて0件であること。特に **E004（raw段落に翻訳が入っている）** は、
本作業が `ja` を空にし忘れていないかの直接の検査になる。

### (d) HTML再生成と3者比較

```sh
RFCS=$(git status --porcelain data/ | sed -E 's|.*rfc([0-9]+)-trans\.json|\1|' | sort -n | tr '\n' ',' | sed 's/,$//')
python3 main.py --rfc "$RFCS" --make
```

生成後、「コミット済みhtml」「HEAD時点のdataから描画した基準」「現在のhtml」の3者を比較し、
**今回の変更と無関係な差分**（元々dataとhtmlが乖離していたもの）を切り分ける:

```python
import json, subprocess, sys, os, re
from collections import Counter
sys.path.insert(0, os.getcwd())
from mako.lookup import TemplateLookup
from src.domain.valueobject.rfc import RfcJsonElem
from src.application.usecase.make_html import RfcHtmlHelper

lookup = TemplateLookup(directories=["./"], input_encoding='utf-8', output_encoding='utf-8')
tpl = lookup.get_template('templates/rfc.html')
files = [l[3:].strip() for l in subprocess.run(['git','status','--porcelain','--','data/'],
         capture_output=True, text=True).stdout.splitlines()]
p = subprocess.Popen(['git','cat-file','--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
def show(path):
    p.stdin.write(f'HEAD:{path}\n'.encode()); p.stdin.flush()
    h = p.stdout.readline().decode().strip()
    if 'missing' in h: return None
    d = p.stdout.read(int(h.split()[2])); p.stdout.read(1); return d.decode('utf-8')

stat = Counter(); stale = []
for f in files:
    num = int(re.search(r'rfc(\d+)-trans', f).group(1)); band = f.split('/')[1]
    obj = json.loads(show(f))
    sp = f'data/{band}/rfc{num}-summary.json'
    s = json.load(open(sp, encoding='utf-8')) if os.path.exists(sp) else None
    base = tpl.render_unicode(ctx=obj, summary=s, is_draft=False,
                              RfcJsonElem=RfcJsonElem, RfcHtmlHelper=RfcHtmlHelper)
    stat['検査'] += 1
    if show(f'html/rfc{num}.html') != base:
        stat['コミット済みhtmlが古かった(今回の変更と無関係)'] += 1; stale.append(num)
    if open(f'html/rfc{num}.html', encoding='utf-8').read() == base:
        stat['!! 今回の変更がhtmlに未反映'] += 1
print(dict(stat)); print('古かったhtml:', len(stale), stale)
```

---

## 6. 現在の進捗（2026-09-19時点）

### 完了内容

RFC8650未満（TXT由来）の**全帯 2000〜8000 に初回適用・検証・HTML再生成まで完了**。

| 帯 | RFC数 | 修復段落 |
|---|---|---|
| data/2000 | 389 | 3836 |
| data/3000 | 340 | 3477 |
| data/4000 | 331 | 2809 |
| data/5000 | 234 | 1634 |
| data/6000 | 215 | 1271 |
| data/7000 | 204 | 1207 |
| data/8000 | 101 | 537 |
| **合計** | **1814** | **14771** |

```
data/  1814 files changed, 51472 insertions(+), 36701 deletions(-)
html/  1814 files changed, 159181 insertions(+), 133425 deletions(-)
```

### ABNF/BNF高確度候補の追加適用

単一行構文の取りこぼし対策後、`--high-confidence-grammar`に一致した候補を追加適用した。

| 帯 | RFC数 | 修復段落 |
|---|---:|---:|
| data/2000 | 28 | 106 |
| data/3000 | 28 | 76 |
| data/4000 | 35 | 98 |
| data/5000 | 36 | 86 |
| data/6000 | 37 | 166 |
| data/7000 | 40 | 72 |
| data/8000 | 22 | 40 |
| **合計** | **226** | **644** |

- 自動修復の累計は初回14771件 + RFC2554追加15件 + 今回644件 = **15430件**
- 644段落すべてで`raw: true`、`ja: ""`、原文との正規化一致、原本TXTとの桁位置一致を確認
- 対象226 RFCの公式lintはE/Wともに0件（検出された既存W003 4件も個別修正）
- 対象226 RFCのHTMLを再生成し、現在のJSONからの描画結果と226/226件一致
- 再走査結果は0件で、べき等性を確認

引用文字列だけを終端として使う単純な規則（例: RFC2846の
`recipient-name = "/ATTN=" pers-name`）は、ABNF固有の`%x`や反復記号を含まないため初回条件から
漏れていた。確定済みの`raw`構文規則との隣接関係を固定点まで伝播する条件を追加し、100 RFC・
322段落を追加修復した。RFC2846では指摘箇所を含む3段落を修復した。

- 自動修復の累計は15430件 + 今回322件 = **15752件**
- 対象100 RFCはJSON構文正常、公式lintはE/Wともに0件、HTML描画結果は100/100件一致
- lintで判明した既存W003（RFC4876の`MUST NOT`、RFC7151の`SHOULD`）も修正
- 全RFC再走査は0件で、高確度判定の収束とべき等性を確認

### ABNF増分選択と改行規則の追加適用

- `=/`および演算子直後で改行する高確度構文を52 RFC・86段落修復
- RFC2846の`pstn-address =/ ...`は本文側・付録側の2出現をともに`raw: true`へ修正
- RFC5259の誤結合1段落を原本どおり2つの`raw`構文ブロックへ分割し、隣接する平坦化済み規則も復元
- RFC3977の`The =/ notation ...`は説明文として非rawのまま維持
- 自動修復の累計は15752件 + 今回86件 = **15838件**（別途RFC5259の3ブロックを個別復元）
- 対象52 RFCの公式lintはE/Wともに0件、JSON構文は全件正常

### raw化済み段落のレイアウト復元

`raw: true`を無条件に検査対象外としていたため、rawフラグと`ja: ""`だけが設定され、翻訳時に
平坦化された改行・列揃え・字下げが残る段落があった。正規化した内容が原本TXTと一致する場合だけ
原本の`text`と`indent`へ戻す`--raw-layout`を追加した。

- RFC3977の指摘箇所を含む4段落を修復
- 全帯で1,633 RFC・7,286段落を追加修復（RFC3977と合わせて7,290段落）
- 内訳は、改行増加887件、改行減少17件、改行数不変で列揃え・空白・indentを復元6,382件
- 7,286/7,286段落で`text`・`indent`・`raw`・`ja`の不変条件を確認
- 全RFC再走査は0件
- 対象1,633 RFCのlintはEコード0件。W003 42件は非raw本文に残る既存の規範語問題
- HTMLはRFC3977を含む1,634/1,634件で現在のJSONからの描画結果と一致
- 原本由来の行末空白は除去し、先頭空白と行内の列揃えだけを保持
- ページ境界の次ページ先頭が深い字下げのABNF・コード継続行なら前段と結合するよう改善し、
  RFC3977を含む11 RFC・13か所の分断を修復
- 複数の隣接raw段落を結合した正規化内容が原本1ブロックと一致する場合の安全な結合を追加し、
  8 RFC・15か所を追加修復。翻訳対象の説明文を含む混在ブロックは除外
- 自動修復の累計は15838件 + 今回7290件 + ページ境界13件 + raw結合15件 = **23156件**
  （別途RFC5259の3ブロックを個別復元）

lint時に検出した既存W003も次の4件を修正した。

| RFC | 段落 | 修正内容 |
|---:|---:|---|
| 4792 | 32 | `SHALL`の必須強度と`EncodingPrefixedType`等の識別子を復元 |
| 6048 | 31 | `OPTIONAL`の任意強度と`LIST`識別子を復元 |
| 6477 | 74 | 欠落していた比較節と`SHOULD`の推奨強度を復元 |
| 8497 | 34 | `Session-ID`を維持し、`MUST`の必須強度を復元 |

### 検証結果（全件）

| 項目 | 結果 |
|---|---|
| 不変条件（取り違え・`raw`/`ja`・件数・メタ情報・キー構成） | **違反なし**（図表修復 14771 / 手動訳修正 3 / 空白差のみ 146） |
| 桁位置が原文TXTと一致 | **14771 / 14771** |
| 公式lint（全7690ファイル） | E001/E002/E004/E007/E008 **すべて0件**。W003 231件は既存の別件 |
| HTML | 1814件すべてに反映。無関係な既存差分は27件のみ |

### 個別に修正した誤訳3件（図表修復とは別件）

作業中に発見した、過去の一括修正・初回機械翻訳に由来する訳文の破損。
ユーザーの指示により個別に修正した。

| 箇所 | 内容 | 混入元 |
|---|---|---|
| `data/2000/rfc2253-trans.json` #18 | 本文の訳が無関係なASN.1コードの訳（`ATTRIBUTE TYPE ::= OCTET STRING ...`）に丸ごと上書きされていた | コミット `03bf8e4003` |
| `data/2000/rfc2274-trans.json` #58 | 「以下を提供しなければなりません (MUST)：」が3回重複 | コミット `03bf8e4003` |
| `data/5000/rfc5525-trans.json` #14 | 原文 `[RFC5351], [RFC5352], [RFC5353]` がすべて `[RFC5352]` に。`[Dre2006]`→`[DRE2006]`、句点重複 | 初回翻訳 `63cde16f17`(2023-03) |

コミット `03bf8e4003`（1076ファイル・1856箇所の `ja` 変更）を全走査した結果、
同種の破損は上記2件のみであることを確認済み。走査に使ったパターンは
「同一の10文字以上のフレーズが3回以上連続」と「新jaが旧jaの40%未満に縮小」。

### git状態

- **未コミット**。`data/` 1814ファイル + `html/` 1814ファイルが作業ツリーに残っている
- `tools/fix_broken_figures.py` は**未追跡**（`git add` が必要）
- `.cache/rfc-txt/` は gitignore 済み
- 旧 `HANDOFF_RFC2119.md` は本ファイルに置き換えて削除済み

---

## 7. 残っている課題・既知の限界

### (a) 原文TXTとアラインメントできない段落は未修復

JSONの `text` を正規化したものが原文ブロックのどれとも一致しない場合、`difflib` の
`equal` に入らないため**意図的にスキップ**している。rfc-editor側の再レンダリングや
正誤訂正で本文が変わったケースが該当する。取り違えを避けるための安全側の判断。

確認済みの例:
- `data/2000/rfc2515-trans.json` #488（MIB定義）
- `data/6000/rfc6917-trans.json` #525（HTTPレスポンス例）

**対処の方向性**: これらは原文TXTとの差分を人間／AIが個別に確認して手作業で直すしかない。
全体でどれだけ残っているかは未計測。計測するなら `inspect()` の中で
`tag != 'equal'` の範囲に落ちた段落のうち図表フィンガープリントを持つものを数えればよい。

### (b) 混在ブロックは翻訳が1文失われる

「導入の1文 + 表」のように本文と図表が1ブロックに同居している場合、ブロック単位で
`raw` 化するため導入文の訳も失われる（例: RFC4818 #33）。
パイプラインも1ブロック1分類なので挙動としては一貫しているが、厳密には劣化。

### (c) RFC8650以降は対象外

XML版から組み立てるため（`src/application/usecase/fetch_rfc_xml.py`）、本問題は発生しない。
ツールも `RFC8650 = 8650` 未満のみを対象にしている。

### (d) 検出漏れの可能性

`detect_reasons()` のヒューリスティクスは網羅的ではない。実測での取りこぼし率は
低い（無作為60RFC・data/2000全帯のサンプル目視で誤検出0件）が、検出漏れは残りうる。
新しい取りこぼしパターンを見つけたら `has_hard_code_signal()` に追加するのが最も安全
（`is_prose_reflow` の判定を上書きする形になっており、散文への誤爆を招きにくい）。

---

## 8. 次にやるとよいこと

1. **ユーザーに差分をレビューしてもらい、コミット方針を確認する。**
   ユーザーは帯ごとの分割コミットと1コミットのどちらも選べる状態で「コミットしない」を選んでいる。
2. `tools/fix_broken_figures.py` を `git add` するか確認する。
3. 7-(a) の未修復段落（アラインメント不成立）の全体件数を計測し、対応方針を相談する。
4. `git log --oneline -S'（疑わしいパターン）'` で、他の一括修正コミットにも
   6節と同種の訳文破損が混入していないか横断的に走査する。
   今回は `03bf8e4003` しか走査していない。

---

## 9. 関連ファイル

| パス | 役割 |
|---|---|
| `tools/fix_broken_figures.py` | **本プロジェクトのツール（新規・未追跡）** |
| `tools/lint_translation.py` | 翻訳品質linter（既存）。E004が本作業の直接の検査になる |
| `tools/verify_changes.py` | 一括修正の検証（既存）。`ja` の変更を前提にしており本作業とは想定が異なる |
| `tools/rank_rfcs.py` | 優先順位付け（既存） |
| `src/application/usecase/fetch_rfc_txt.py` | TXTからの本文組み立て。ページ区切り処理の原典 |
| `src/domain/valueobject/rfc/contents/paragraph.py` | `_find_code_pattern` 等の図表判定。**変更禁止** |
| `src/application/usecase/nlp_summarize_rfc.py` | `RFC8650 = 8650` 定数の定義箇所（コメント付き） |
| `templates/rfc.html` | `raw: true` を `<pre>` + indent で描画するテンプレート |
| `.cache/rfc-txt/` | 原文TXTキャッシュ（gitignore済み、6315件） |

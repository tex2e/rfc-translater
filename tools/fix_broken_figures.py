# ------------------------------------------------------------------------------
# 図・表・数式・構文定義の誤分類の検出と修復
#
# RFC8650未満のRFCはTXT版から本文を組み立てている (fetch_rfc_txt.py)。このとき
# Paragraph._find_code_pattern が図表・数式を検出できなかった段落は「本文」と
# みなされ、`\n *` -> 空白 / ` +` -> 空白 の平坦化を受けたうえで翻訳される。
# 結果として data/*/rfc*-trans.json には段組みが壊れた図表・数式が残っている。
#
# このツールは raw 判定処理そのものは変更せず、すでに翻訳済みのJSONに対して
# 原本のRFC TXTを参照し、壊れている段落や本文に誤分類された構文定義だけを
# 原文どおりに復元する。
#   text   -> 原文ブロック (dedent済み)
#   indent -> 原文の字下げ幅
#   raw    -> true
#   ja     -> "" (図表は翻訳しない。E004の規約に合わせる)
#
# 使い方:
#   python3 tools/fix_broken_figures.py --rfc 2313            # 検出のみ (既定)
#   python3 tools/fix_broken_figures.py --rfc 2313 --apply    # 修復を書き込む
#   python3 tools/fix_broken_figures.py --dir 3000 --apply    # 帯ごと
#   python3 tools/fix_broken_figures.py --all --format summary
#   python3 tools/fix_broken_figures.py --all --high-confidence-grammar --apply
# ------------------------------------------------------------------------------

import argparse
import difflib
import glob
import json
import os
import re
import sys
import textwrap
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.domain.services.rfcutils import RfcUtils                        # noqa: E402
from src.domain.valueobject.rfc.contents.paragraph import Paragraph, BREAK  # noqa: E402

# RFCがXML形式に対応した最小RFC番号。これ以降はTXTを経由しないため対象外。
RFC8650 = 8650

CACHE_DIR = os.environ.get('RFC_TXT_CACHE', os.path.join('.cache', 'rfc-txt'))

# Paragraph の判定メソッドを借用するためのダミーインスタンス
# (is_code=True にして __init__ 内の判定処理をスキップさせる)
_P = Paragraph('x', is_code=True)


# ------------------------------------------------------------------------------
# 原文TXTの取得と、fetch_rfc_txt.py と同じ前処理の再現
# ------------------------------------------------------------------------------

def fetch_txt(num: int, sleep: float = 0.0) -> str:
    """原本のRFC TXTを取得する (ローカルキャッシュ付き)"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f'rfc{num}.txt')
    if not os.path.exists(path):
        url = f'https://www.rfc-editor.org/rfc/rfc{num}.txt'
        req = urllib.request.Request(url, headers={'User-agent': '', 'referer': url})
        with urllib.request.urlopen(req, timeout=60) as res:
            body = res.read()
        with open(path, 'wb') as f:
            f.write(body)
        if sleep:
            time.sleep(sleep)
    with open(path, 'rb') as f:
        return f.read().decode('ascii', errors='ignore')


def remove_page_breaks(text: str) -> str:
    """fetch_rfc_txt.py のページ区切り除去・ページ跨ぎ結合を再現する。

    ただしページ境界の両側が独立した構文定義なら結合しない。元処理は末尾の
    句点だけを手掛かりにするため、RFC 2554 の continue_req と CR のような
    別々の規則を一段落に連結してしまう。
    """
    contents = text.split("\n\n")
    contents = [con for con in contents if len(con) > 0]
    contents_len = len(contents)
    for i, content in enumerate(contents):
        if not re.search(r'\x0c', content):
            continue
        contents[i + 0] = ''
        if i + 1 >= contents_len:
            continue
        prev_last_line = contents[i - 1].rstrip('\n').split('\n')[-1]
        next_first_line = contents[i + 1].lstrip('\n').split('\n')[0]
        indent1 = RfcUtils.get_indent(prev_last_line)
        indent2 = RfcUtils.get_indent(next_first_line)
        separate_definitions = bool(
            GRAMMAR_RULE.match(prev_last_line) and GRAMMAR_RULE.match(next_first_line))
        grammar_continuation = bool(
            GRAMMAR_RULE.search(contents[i - 1])
            and indent2 > indent1
            and re.match(r'^\s*(?:/|\*|\d+\*|\[|\()', next_first_line))
        ordinary_continuation = bool(
            re.match(r'^ *[a-zA-Z0-9(]', next_first_line)
            and indent1 == indent2)
        if not prev_last_line.endswith('.') \
                and not re.search(r'[;|]$', prev_last_line) \
                and not separate_definitions \
                and (ordinary_continuation or grammar_continuation):
            contents[i + 1] = contents[i - 1].rstrip('\n') + BREAK + contents[i + 1].lstrip('\n')
            contents[i - 1] = ''
    return '\n\n'.join(contents).strip()


def dedent_block(chunk: str) -> tuple[str, int]:
    """段落ブロックを (dedent済み本文, 字下げ幅) に分解する。

    Paragraph は dedent したあとに BREAK (ページ跨ぎ) を改行へ戻すため、
    ページをまたいだ行にだけ次ページ側の字下げが残ってしまう。ここでは先に
    改行へ戻してから字下げを測ることで、原文TXTの桁位置を正確に再現する。
    """
    src = chunk.replace(BREAK, '\n').lstrip('\n').rstrip()
    lines = src.split('\n')
    # 字下げは空白のみで測る (タブ始まりの行は字下げ0とみなし、タブを削らない)
    widths = [len(ln) - len(ln.lstrip(' ')) for ln in lines if ln.strip()]
    indent = min(widths) if widths else 0
    # 行末空白は桁位置に寄与せず、HTMLにも不要な空白を残すため除去する。
    # 先頭空白と行内の列揃えはそのまま保持する。
    body = '\n'.join((ln[indent:] if ln.strip() else '').rstrip()
                     for ln in lines)
    return body, indent


def split_blocks(num: int, sleep: float = 0.0) -> list[tuple[str, int]]:
    """原文TXTを段落ブロックに分割し、(dedent済み本文, 字下げ幅) の配列を返す"""
    text = remove_page_breaks(fetch_txt(num, sleep))
    return [dedent_block(chunk) for chunk in re.compile(r'\n\n+').split(text)]


# ------------------------------------------------------------------------------
# 破損判定
# ------------------------------------------------------------------------------

# 罫線・矢印などの図形要素
ART = re.compile(r'\+--|--\+|\+-\+|\|\s|\s\||-{4,}|={4,}|~{3,}|\*{4,}|_{4,}'
                 r'|<-{2,}|-{2,}>|/\s*\\|\\\s*/|\.-{2,}')
# 数式に現れる記号
MATH = re.compile(r'[=^]|\bSUM\b|\bXOR\b|\bmod\b|\*\*')
# 行内の3連以上の空白 = 列揃え (本文の「. 」直後の2連空白と区別するため3連以上)
COLUMN = re.compile(r'\S {3,}\S')

# 本文には現れない、行の並び自体が意味を持つことが明らかなパターン。
# HTTPやプロトコルの実例は全行が左端に揃うため列揃えも字下げ差も持たず、
# is_prose_reflow だけでは本文の折り返しと区別できないので個別に拾う。
HARD_CODE = [
    re.compile(r'^[ \t]*[-=~*_+]{4,}[ \t]*$', re.MULTILINE),                    # 罫線だけの行
    re.compile(r'^[ \t]*[SC]: ', re.MULTILINE),                                 # サーバ/クライアント対話
    re.compile(r'^[ \t]*(?:GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH) \S+ HTTP/',
               re.MULTILINE),                                                   # HTTPリクエスト行
    re.compile(r'^[ \t]*HTTP/\d\.\d \d{3}', re.MULTILINE),                      # HTTPステータス行
    re.compile(r'^[ \t]*[0-9a-f]{2}(?: [0-9a-f]{2}){7}', re.MULTILINE),         # hexdump
]
# 「ヘッダ名: 値」の形の行 (HTTPヘッダ、MIBの属性など)
HEADER_LINE = re.compile(r'^[ \t]*[A-Za-z][\w-]*:[ \t]\S', re.MULTILINE)
# ABNF/BNF の規則定義候補。RFC 5234 の rulename より少し広く underscore も
# 許容し、旧RFCの AUTH_CHAR のような定義も拾う。ただし「ANS = stop means ...」
# のような説明文との区別は is_grammar_definition() で行う。
GRAMMAR_RULE = re.compile(
    r'^[ \t]*[A-Za-z][A-Za-z0-9_-]*[ \t]+=(?:/)?'
    r'(?:[ \t]+|[ \t]*\n[ \t]+)(?P<rhs>\S.*)$',
    re.MULTILINE)
# ABNF の右辺に現れる、散文ではほぼ使われない記号。引用符や丸括弧だけでは
# 数式を説明する本文にも頻出するため、ここでは数値表現・選択・反復・ABNFの
# 二重セミコロンコメントに限定する。
GRAMMAR_SYNTAX = re.compile(
    r'%[bBdDxX][0-9A-Fa-f.-]+|(?:^|\s)/(?:\s|$)'
    r'|(?<!\w)(?:\d+\*\d*|\d*\*\d+|\*\()(?=[A-Za-z0-9("\[])|;;')

# 全RFCへの一括適用に使う、誤検出を抑えた構文定義の追加条件。
# `%x`・`=/` はABNF固有、反復は数式でない場合に限定する。その他の規則は
# Formal Syntax / ABNF / BNF 等の文脈と構文演算子の両方を要求する。
HIGH_GRAMMAR_UNIQUE = re.compile(
    r'%[bBdDiIsSxX](?:[0-9A-Fa-f.\-]+|["\'])')
HIGH_GRAMMAR_REPEAT = re.compile(
    r'(?<!\w)(?:\d+\*\d*|\d*\*\d+|\*\()(?=[A-Za-z0-9("\[])')
HIGH_GRAMMAR_MATH = re.compile(
    r'\^|\bmod\b|\b(?:sin|cos|log|sum)\b|\+\s*\w+\s*=|,\s*\n?[A-Za-z]\w*\s*=',
    re.IGNORECASE)
HIGH_GRAMMAR_OPERATOR = re.compile(
    r'\s/\s|["\']|\[[^\]]*\]'
    r'|\b(?:ALPHA|BIT|CHAR|CR|CRLF|CTL|DIGIT|DQUOTE|HEXDIG|HTAB|LF|LWSP|OCTET|SP|VCHAR|WSP)\b')
HIGH_GRAMMAR_CONTEXT = re.compile(
    r'ABNF|BNF|Backus-Naur|formal syntax|syntax specification'
    r'|collected grammar|formal grammar', re.IGNORECASE)


def is_incremental_grammar_match(match, block: str = '') -> bool:
    """ABNFの増分選択`=/`を、同記号を説明する通常文と区別する。"""
    if not re.search(r'=\s*/', match.group(0)):
        return False
    rhs = match.group('rhs').rstrip()
    # `The =/ notation ... is used.` は規則ではない。一方、セミコロン以降は
    # ABNFコメントなので、コメントが句点で終わる規則は許容する。
    source = block.rstrip() or rhs
    if ';' in source:
        return True
    # 引用終端の `"."` は末尾が引用符なのでここには該当しない。
    return not (len(list(GRAMMAR_RULE.finditer(source))) == 1
                and source.endswith(('.', '!', '?')))


def has_raw_grammar_neighbor(contents: list[dict], index: int) -> bool:
    """隣接する raw 段落が構文規則なら、同じ構文ブロック内とみなす。"""
    for pos in (index - 1, index + 1):
        if not 0 <= pos < len(contents):
            continue
        neighbor = contents[pos]
        text = neighbor.get('text') or ''
        if neighbor.get('raw') and GRAMMAR_RULE.search(text) \
                and is_grammar_definition(text):
            return True
    return False


def is_grammar_definition(orig: str, code_pattern=None) -> bool:
    """代入を含む説明文を除外し、構文・コード上の定義だけを判定する。"""
    matches = list(GRAMMAR_RULE.finditer(orig))
    if not matches:
        return False
    if code_pattern is None:
        code_pattern = bool(_P._find_code_pattern(orig))
    # 既存判定との合意、構文記号、または複数の定義行があることを根拠にする。
    syntax_rhs = any(GRAMMAR_SYNTAX.search(m.group('rhs')) for m in matches)
    incremental = any(is_incremental_grammar_match(m, orig) for m in matches)
    # 引用リテラルを含み、通常の英文の句点で終わらない右辺も構文とみなす。
    # これにより `continue_req = "334" SPACE ...` を拾いつつ、
    # `Tcur = "A" (i.e., ...)` のような説明文は除外する。
    quoted_rhs = any('"' in m.group('rhs') and
                     not re.search(r'[.!?]["\']?$', m.group('rhs').rstrip())
                     for m in matches)
    return code_pattern or len(matches) >= 2 or syntax_rhs or incremental or quoted_rhs


def is_high_confidence_grammar(contents: list[dict], index: int, orig: str) -> bool:
    """全RFCへ安全に横展開できる高確度のABNF/BNF定義かを判定する。"""
    lines = [line for line in orig.splitlines() if line.strip()]
    first = next((line for line in lines
                  if not line.lstrip().startswith((';', '#', '//'))), '')
    # 導入文と構文が同居する混在ブロックは一括適用しない。
    grammar_start = orig.find(first)
    if grammar_start < 0 or not GRAMMAR_RULE.match(orig[grammar_start:]):
        return False

    matches = list(GRAMMAR_RULE.finditer(orig))
    if any(is_incremental_grammar_match(match, orig) for match in matches):
        return True
    if any(HIGH_GRAMMAR_UNIQUE.search(match.group(0)) for match in matches):
        return True
    if not HIGH_GRAMMAR_MATH.search(orig) and any(
            HIGH_GRAMMAR_REPEAT.search(match.group(0)) for match in matches):
        return True

    # 単純な quoted-string 終端だけを使う規則は、ABNF 固有の `%x` や反復を
    # 含まない。隣接段落が既に raw の構文規則なら、同じ構文ブロックとして
    # 安全に拾う（例: `recipient-name = "/ATTN=" pers-name`）。
    has_quoted_terminal = any('"' in match.group('rhs') or "'" in match.group('rhs')
                              for match in matches)
    if has_quoted_terminal and has_raw_grammar_neighbor(contents, index):
        return True

    section = ''
    for pos in range(index - 1, -1, -1):
        if contents[pos].get('section_title'):
            section = contents[pos].get('text') or ''
            break
    lead_in = ' '.join((contents[pos].get('text') or '')
                       for pos in range(max(0, index - 5), index))
    has_context = HIGH_GRAMMAR_CONTEXT.search(section + ' ' + lead_in)
    has_operator = any(HIGH_GRAMMAR_OPERATOR.search(match.group('rhs'))
                       for match in matches)
    return bool(has_context and has_operator)


def filter_high_confidence_grammar(contents: list[dict], findings: list) -> list:
    """隣接する構文規則の判定を、追加候補がなくなるまで伝播させる。"""
    shadow = [dict(item) for item in contents]
    remaining = list(findings)
    selected = []
    while remaining:
        newly_selected = [
            finding for finding in remaining
            if is_high_confidence_grammar(
                shadow, finding.index, finding.after_text)
        ]
        if not newly_selected:
            break
        selected.extend(newly_selected)
        selected_ids = {id(finding) for finding in newly_selected}
        remaining = [finding for finding in remaining
                     if id(finding) not in selected_ids]
        for finding in newly_selected:
            shadow[finding.index]['text'] = finding.after_text
            shadow[finding.index]['raw'] = True
    return sorted(selected, key=lambda finding: finding.index)


def has_hard_code_signal(orig: str) -> bool:
    """本文の折り返しではありえない、確実なコード・図表の signal を持つか"""
    if any(p.search(orig) for p in HARD_CODE):
        return True
    if is_grammar_definition(orig):
        return True
    return len(HEADER_LINE.findall(orig)) >= 3


def _lines(orig: str) -> list[str]:
    return [ln for ln in orig.split('\n') if ln.strip()]


def is_prose_reflow(orig: str) -> bool:
    """通常の本文の折り返しか (= 平坦化されても情報を失っていないか)"""
    lines = _lines(orig)
    if len(lines) < 2:
        return True
    if any(COLUMN.search(ln) for ln in lines):
        return False
    # 2行目以降の字下げが一定なら、箇条書きを含む通常の本文とみなす
    indents = [len(ln) - len(ln.lstrip()) for ln in lines[1:]]
    return len(set(indents)) <= 1


def detect_reasons(orig: str) -> list[str]:
    """原文ブロックが図・表・数式としての配置を持つ根拠を列挙する"""
    lines = _lines(orig)
    cols = sum(1 for ln in lines if COLUMN.search(ln))
    art = len(ART.findall(orig))
    indents = {len(ln) - len(ln.lstrip()) for ln in lines}
    reasons = []
    code_pattern = bool(_P._find_code_pattern(orig))
    if code_pattern:
        reasons.append('code')
    if is_grammar_definition(orig, code_pattern):
        reasons.append('grammar')
    if cols >= 2:
        reasons.append(f'cols={cols}')
    if art >= 3:
        reasons.append(f'art={art}')
    # 数式: 短く、字下げが揃っておらず、列揃えと数式記号を持つ
    if len(lines) <= 6 and len(indents) >= 3 and cols >= 1 and MATH.search(orig):
        reasons.append('formula')
    return reasons


def normalize(text: str) -> str:
    """JSONの平坦化済み本文と原文ブロックを突き合わせるための正規化キー"""
    text = text.replace(BREAK, ' ')
    text = re.sub(r'([a-zA-Z])-\s+', r'\1-', text)  # 行末ハイフンの結合を吸収
    return re.sub(r'\s+', ' ', text).strip().lower()


# ------------------------------------------------------------------------------
# 1ファイルの検査
# ------------------------------------------------------------------------------

class Finding:
    def __init__(self, index, reasons, before_text, before_indent, after_text,
                 after_indent, ja, end_index=None):
        self.index = index
        self.end_index = index + 1 if end_index is None else end_index
        self.reasons = reasons
        self.before_text = before_text
        self.before_indent = before_indent
        self.after_text = after_text
        self.after_indent = after_indent
        self.ja = ja


def inspect(path: str, num: int, sleep: float = 0.0,
            restore_raw_layout: bool = False):
    """壊れている段落を検出する。戻り値: (JSONオブジェクト, Findingの配列, 整合率)"""
    with open(path, encoding='utf-8') as f:
        obj = json.load(f)
    contents = obj.get('contents') or []
    blocks = split_blocks(num, sleep)

    matcher = difflib.SequenceMatcher(
        a=[normalize(c.get('text') or '') for c in contents],
        b=[normalize(b[0]) for b in blocks], autojunk=False)

    findings = []
    for tag, i1, i2, j1, _j2 in matcher.get_opcodes():
        if restore_raw_layout and tag == 'replace' \
                and i2 - i1 >= 2 and _j2 - j1 == 1:
            orig, indent = blocks[j1]
            current = contents[i1:i2]
            joined = ' '.join(c.get('text') or '' for c in current)
            if all(c.get('raw') for c in current) \
                    and not any(c.get('toc') or c.get('section_title')
                                for c in current) \
                    and normalize(joined) == normalize(orig) \
                    and has_hard_code_signal(orig):
                findings.append(Finding(
                    i1, ['raw-layout', 'merge'], joined,
                    current[0].get('indent'), orig, indent, '', end_index=i2))
            continue
        if tag != 'equal':
            continue
        for k in range(i2 - i1):
            c = contents[i1 + k]
            orig, indent = blocks[j1 + k]
            # 見出し・目次は対象外。raw段落は明示指定時に限り、内容を変えず
            # 原本の改行と字下げだけを復元する。
            if c.get('toc') or c.get('section_title'):
                continue
            if c.get('raw'):
                if restore_raw_layout and (
                        (c.get('text') or '') != orig
                        or c.get('indent') != indent):
                    findings.append(Finding(
                        i1 + k, ['raw-layout'], c.get('text') or '',
                        c.get('indent'), orig, indent, c.get('ja') or ''))
                continue
            reasons = detect_reasons(orig)
            if not reasons:
                continue
            # 本文の折り返しは対象外。ただし確実なコード signal があれば優先する
            if is_prose_reflow(orig) and not has_hard_code_signal(orig):
                continue
            findings.append(Finding(i1 + k, reasons, c.get('text') or '',
                                    c.get('indent'), orig, indent, c.get('ja') or ''))
    return obj, findings, matcher.ratio()


def apply_findings(obj: dict, findings: list) -> None:
    """検出結果をJSONオブジェクトへ反映する"""
    contents = obj['contents']
    # 複数段落を1段落へ戻すfindingがあるため、後方から適用してindexを保つ。
    for f in sorted(findings, key=lambda finding: finding.index, reverse=True):
        c = dict(contents[f.index])
        c['indent'] = f.after_indent
        c['text'] = f.after_text
        c['raw'] = True
        c['ja'] = ''
        contents[f.index:f.end_index] = [c]


# ------------------------------------------------------------------------------
# エントリポイント
# ------------------------------------------------------------------------------

def target_paths(args) -> list[tuple[str, int]]:
    paths = []
    if args.rfc:
        for n in args.rfc:
            num = int(n)
            paths.append((f'data/{num // 1000 * 1000}/rfc{num}-trans.json', num))
    else:
        dirs = args.dir or sorted(
            d for d in os.listdir('data') if re.fullmatch(r'\d+', d))
        for d in dirs:
            for p in sorted(glob.glob(f'data/{d}/rfc*-trans.json')):
                m = re.search(r'rfc(\d+)-trans\.json$', p)
                if m:
                    paths.append((p, int(m.group(1))))
    return [(p, n) for p, n in paths if n < RFC8650 and os.path.exists(p)]


def main() -> int:
    p = argparse.ArgumentParser(description='図・表・数式の段組み破壊を検出/修復する')
    p.add_argument('--rfc', nargs='*', help='対象RFC番号 (例: 2313 2246)')
    p.add_argument('--dir', nargs='*', help='対象データディレクトリ (例: 2000 3000)')
    p.add_argument('--all', action='store_true', help='RFC8650未満をすべて対象にする')
    p.add_argument('--apply', action='store_true', help='検出結果をJSONに書き込む')
    p.add_argument('--high-confidence-grammar', action='store_true',
                   help='高確度のABNF/BNF構文定義だけを対象にする')
    p.add_argument('--raw-layout', action='store_true',
                   help='raw化済み段落の改行と字下げを原本どおりに復元する')
    p.add_argument('--format', choices=['detail', 'summary', 'json'], default='detail')
    p.add_argument('--limit-samples', type=int, default=3, help='RFCごとの表示件数')
    p.add_argument('--sleep', type=float, default=0.3, help='TXT取得の間隔(秒)')
    p.add_argument('-o', '--output', help='--format json の出力先')
    args = p.parse_args()

    if not (args.rfc or args.dir or args.all):
        p.error('--rfc / --dir / --all のいずれかを指定してください')

    total_files = total_findings = 0
    report = []
    for path, num in target_paths(args):
        try:
            obj, findings, ratio = inspect(
                path, num, args.sleep, restore_raw_layout=args.raw_layout)
            if args.raw_layout and not args.high_confidence_grammar:
                findings = [f for f in findings
                            if 'raw-layout' in f.reasons]
            if args.high_confidence_grammar:
                contents = obj.get('contents') or []
                raw_layout = [f for f in findings if 'raw-layout' in f.reasons]
                grammar = [f for f in findings if 'raw-layout' not in f.reasons]
                findings = raw_layout + filter_high_confidence_grammar(
                    contents, grammar)
                findings.sort(key=lambda finding: finding.index)
        except urllib.error.HTTPError as e:
            print(f'[-] RFC{num}: TXT取得失敗 ({e.code})', file=sys.stderr)
            continue
        except Exception as e:  # 原文が取得できない/構造が違う場合は飛ばす
            print(f'[-] RFC{num}: {type(e).__name__}: {e}', file=sys.stderr)
            continue
        if not findings:
            continue
        total_files += 1
        total_findings += len(findings)
        report.append({'rfc': num, 'path': path, 'align_ratio': round(ratio, 4),
                       'findings': [{'index': f.index, 'reasons': f.reasons,
                                     'end_index': f.end_index,
                                     'before': f.before_text, 'after': f.after_text,
                                     'indent': f.after_indent, 'ja': f.ja}
                                    for f in findings]})

        if args.format == 'detail':
            print(f'\n===== RFC{num} ({len(findings)}件, align={ratio:.3f}) {path}')
            for f in findings[:args.limit_samples]:
                print(f'\n  -- #{f.index} [{",".join(f.reasons)}] '
                      f'indent {f.before_indent} -> {f.after_indent}')
                print('  現在:', repr(f.before_text[:150]))
                print('  原文:')
                print(textwrap.indent(f.after_text[:400], '       | '))
            if len(findings) > args.limit_samples:
                print(f'\n  ... 他 {len(findings) - args.limit_samples} 件')
        elif args.format == 'summary':
            print(f'RFC{num}: {len(findings)}件 (align={ratio:.3f})')

        if args.apply:
            apply_findings(obj, findings)
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                json.dump(obj, f, ensure_ascii=False, indent=2)

    print(f'\n[*] 対象RFC {total_files} 件 / 破損段落 {total_findings} 件'
          f'{" を修復しました" if args.apply else " を検出しました (--apply で修復)"}')

    if args.format == 'json':
        out = json.dumps(report, ensure_ascii=False, indent=2)
        if args.output:
            with open(args.output, 'w', encoding='utf-8', newline='\n') as f:
                f.write(out)
        else:
            print(out)
    return 0


if __name__ == '__main__':
    sys.exit(main())

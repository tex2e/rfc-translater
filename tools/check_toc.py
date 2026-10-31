"""目次を全件検査する。原文TXTがある場合だけ、照合済みの字下げを補正できる。"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.application.usecase.rfc_toc import make_toc_rows, _parts
from src.application.usecase.make_html import RfcHtmlHelper


class TocLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.pairs = Counter(), [], []
        self.depth, self.grid, self.cell = 0, None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids[attrs['id']] += 1
        if tag == 'div':
            self.depth += 1
            if 'toc-grid' in attrs.get('class', '').split():
                self.grid = self.depth
                self.pairs.append([])
        if self.grid is not None:
            if tag == 'pre' and 'toc-cell' in attrs.get('class', '').split():
                self.pairs[-1].append(None)
                self.cell = len(self.pairs[-1]) - 1
            if tag == 'a' and attrs.get('href', '').startswith('#'):
                target = attrs['href'][1:]
                self.links.append(target)
                if self.cell is not None:
                    self.pairs[-1][self.cell] = target

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.cell = None
        if tag == 'div':
            if self.depth == self.grid:
                self.grid = None
            self.depth -= 1


def check_html(html):
    parser = TocLinks()
    parser.feed(html)
    issues = []
    for target in sorted(set(parser.links)):
        if parser.ids[target] != 1:
            issues.append({'kind': 'invalid_target', 'severity': 'error', 'target': target,
                           'matches': parser.ids[target]})
    for cells in parser.pairs:
        if len(cells) % 2 or any(a != b for a, b in zip(cells[::2], cells[1::2])):
            issues.append({'kind': 'paired_target_mismatch', 'severity': 'error'})
    return issues


def inspect(obj, source=None, apply=False):
    contents = obj['contents']
    rows = make_toc_rows(contents, RfcHtmlHelper.make_paragraph_ids(contents), RfcHtmlHelper.text_to_id)
    issues, changes = [], []
    original_lines = defaultdict(list)
    if source is not None:
        if not re.search(r'Requests? for Comments?:\s*' + str(obj['number']) + r'\b', source[:2000], re.IGNORECASE):
            raise ValueError('原文TXTのRFC番号が一致しません')
        for page_number, page in enumerate(source.split('\f')):
            first_content = page_number > 0
            for line in page.splitlines():
                if not line.strip() or (first_content and re.match(r'^RFC\s+\d+\b', line)):
                    continue
                original_lines[line.lstrip(' ')].append((line, first_content))
                first_content = False
    for index, entries in rows.items():
        for entry in entries:
            if entry['issue']:
                issues.append({'block': index, 'kind': entry['issue'], 'severity': 'warning',
                               'number': entry['number'], 'text': entry['en'].strip()})
        paragraph = contents[index]
        lines = paragraph['text'].split('\n')
        # 階層ごとの字下げの多数派との相違は候補の抽出だけに使う。
        # ここから推測した値を自動適用してはならない。
        levels = defaultdict(Counter)
        for line in lines:
            key, _, _ = _parts(line)
            if key:
                levels[key.count('.')][len(line) - len(line.lstrip(' '))] += 1
        confirmed = any(e['confirmed'] for e in entries)
        for offset, line in enumerate(lines):
            key, _, _ = _parts(line)
            leading = len(line) - len(line.lstrip(' '))
            if key and levels[key.count('.')].most_common(1)[0][1] >= 3:
                common = levels[key.count('.')].most_common(1)[0][0]
                if leading != common:
                    issues.append({'block': index, 'line': offset, 'kind': 'indent_candidate',
                                   'severity': 'warning', 'number': key, 'indent': leading, 'usual': common})
            candidates = original_lines.get(line.lstrip(' '), [])
            if source is None or not confirmed or not line.strip() or len(candidates) != 1:
                continue
            original, page_start = candidates[0]
            absolute_indent = len(original) - len(original.lstrip(' '))
            base = paragraph.get('indent', 0)
            if absolute_indent < base:
                issues.append({'block': index, 'line': offset, 'kind': 'source_indent_unrepresentable',
                               'severity': 'warning'})
                continue
            corrected = ' ' * (absolute_indent - base) + line.lstrip(' ')
            if corrected != line:
                # この不具合が作る差は、改ページ直後に残る段落共通の字下げ。
                # それ以外の差（XML/TXTの書式差など）は原文に一致しても自動適用しない。
                repairable = page_start and base > 0 and leading - (absolute_indent - base) == base
                change = {'block': index, 'line': offset,
                          'kind': 'source_indent_mismatch' if repairable else 'source_indent_review',
                          'severity': 'warning', 'before': line, 'after': corrected}
                issues.append(change)
                if repairable:
                    changes.append(change)
                if apply and repairable:
                    lines[offset] = corrected
        if apply:
            paragraph['text'] = '\n'.join(lines)
    return issues, changes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rfc', nargs='+', type=int)
    ap.add_argument('--root', type=Path, default=ROOT)
    ap.add_argument('--source-dir', type=Path, help='原RFCの rfcNNNN.txt を保存したディレクトリ')
    ap.add_argument('--apply-indent', action='store_true', help='原文に一意一致する先頭空白だけを補正')
    ap.add_argument('--fetch-sources', action='store_true', help='字下げ候補のあるRFCの原文TXTを取得（通常の検査は通信しない）')
    ap.add_argument('--check-html', action='store_true')
    ap.add_argument('--output', type=Path)
    ap.add_argument('--compare-base', help='指定コミットよりエラー件数が増えた場合だけ失敗')
    args = ap.parse_args()
    if (args.apply_indent or args.fetch_sources) and not args.source_dir:
        ap.error('--apply-indent / --fetch-sources requires --source-dir')
    if args.compare_base and not args.check_html:
        ap.error('--compare-base requires --check-html')
    report, before_errors = [], 0
    before_keys = set()
    paths = sorted((args.root / 'data').glob('[0-9]*/*-trans.json'))
    if args.rfc:
        paths = [p for p in paths if int(re.fullmatch(r'rfc(\d+)-trans.json', p.name)[1]) in args.rfc]
    if args.fetch_sources:
        args.source_dir.mkdir(parents=True, exist_ok=True)
        numbers = []
        for path in paths:
            obj = json.loads(path.read_text())
            if args.rfc or any(x['kind'] == 'indent_candidate' for x in inspect(obj)[0]):
                numbers.append(obj['number'])
        def fetch(number):
            target = args.source_dir / f'rfc{number}.txt'
            if target.exists():
                return
            with urlopen(f'https://www.rfc-editor.org/rfc/rfc{number}.txt', timeout=20) as response:
                data = response.read().decode('ascii', errors='ignore')
            if not re.search(r'Requests? for Comments?:\s*' + str(number) + r'\b', data[:2000], re.IGNORECASE):
                raise ValueError('RFC番号が一致しません')
            target.write_text(data)
        with ThreadPoolExecutor(max_workers=6) as pool:
            pending = {pool.submit(fetch, n): n for n in numbers}
            for i, future in enumerate(as_completed(pending), 1):
                try:
                    future.result()
                except Exception as error:
                    report.append({'rfc': pending[future], 'kind': 'source_unavailable',
                                   'severity': 'warning', 'error': str(error)})
                if i % 50 == 0 or i == len(numbers):
                    print(f'Source TXT: {i}/{len(numbers)}', flush=True)
    for path in paths:
        number = int(re.fullmatch(r'rfc(\d+)-trans.json', path.name)[1])
        if args.rfc and number not in args.rfc:
            continue
        raw = path.read_text()
        obj = json.loads(raw)
        source_path = args.source_dir / f'rfc{number}.txt' if args.source_dir else None
        source = source_path.read_text() if source_path and source_path.exists() else None
        issues, changes = inspect(obj, source, args.apply_indent)
        if args.apply_indent and changes:
            # JSON全体を整形し直さず、変更した目次textフィールドだけを置換する。
            original = json.loads(raw)
            for index, paragraph in enumerate(obj['contents']):
                old = original['contents'][index]['text']
                new = paragraph['text']
                if old != new:
                    a, b = json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)
                    if raw.count(a) != 1:
                        raise ValueError(f'{path}: textフィールドが一意ではありません')
                    raw = raw.replace(a, b, 1)
            path.write_text(raw)
        html_path = args.root / 'html' / f'rfc{number}.html'
        if args.check_html and html_path.exists():
            issues += check_html(html_path.read_text())
        if args.compare_base and args.check_html:
            import subprocess
            result = subprocess.run(['git', 'show', f'{args.compare_base}:html/rfc{number}.html'],
                                    cwd=args.root, capture_output=True, text=True)
            if result.returncode == 0:
                old_issues = check_html(result.stdout)
                before_errors += len(old_issues)
                before_keys.update(json.dumps({'rfc': number, **issue}, sort_keys=True)
                                   for issue in old_issues)
        report.extend({'rfc': number, **issue} for issue in issues)
    counts = Counter(x['kind'] for x in report)
    result = {'counts': dict(sorted(counts.items())), 'issues': report}
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['counts'], ensure_ascii=False, indent=2))
    errors = sum(x['severity'] == 'error' for x in report)
    if args.compare_base:
        print(f'HTML errors: {before_errors} -> {errors}')
        introduced = [issue for issue in report if issue['severity'] == 'error'
                      and json.dumps(issue, sort_keys=True) not in before_keys]
        print(f'New HTML errors: {len(introduced)}')
        return int(bool(introduced))
    return int(bool(errors))


if __name__ == '__main__':
    sys.exit(main())

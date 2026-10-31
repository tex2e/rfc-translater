"""Audit untranslated markup examples without stripping legitimate inline tags.

block_candidate needs inspection; inline_or_placeholder includes normal prose
and protocol variables. Reports are deliberately read-only: restoring line
breaks requires comparison with the official RFC TXT, not guessed formatting.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.domain.valueobject.rfc.contents.html_example import (
    TAGS, is_html_example, is_xml_example)

MARKUP = re.compile(rf'<(?:/?(?:{TAGS})(?=[\s/>])|!doctype\s+html\b)', re.I)


def inspect(obj):
    findings = []
    for i, paragraph in enumerate(obj['contents']):
        if paragraph.get('raw') or paragraph.get('section_title'):
            continue
        text = paragraph['text']
        if not MARKUP.search(text):
            continue
        block = is_html_example(text) or is_xml_example(text)
        findings.append({'rfc': obj['number'], 'paragraph': i,
                         'kind': 'block_candidate' if block else 'inline_or_placeholder',
                         'text': text})
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rfc', type=int, nargs='+')
    parser.add_argument('--format', choices=['text', 'json'], default='text')
    parser.add_argument('--check', action='store_true', help='Fail on standalone block candidates')
    args = parser.parse_args()
    findings = []
    count = 0
    for path in sorted((ROOT / 'data').glob('*/*-trans.json')):
        match = re.fullmatch(r'rfc(\d+)-trans.json', path.name)
        if not match:
            continue
        number = int(match[1])
        if args.rfc and number not in args.rfc:
            continue
        count += 1
        findings.extend(inspect(json.loads(path.read_text())))
    counts = Counter(f['kind'] for f in findings)
    if args.format == 'json':
        print(json.dumps({'scanned': count, 'counts': counts, 'findings': findings}, ensure_ascii=False, indent=2))
    else:
        print(f'Scanned {count} RFCs: {dict(counts)}')
        for f in findings:
            print(f"RFC {f['rfc']} [{f['paragraph']}] {f['kind']}: {f['text'][:160]}")
    return int(args.check and counts['block_candidate'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())

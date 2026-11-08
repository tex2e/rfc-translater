"""Find prose marked raw because a quoted omission (....) resembled TOC leaders.

Read-only audit of this specific misclassification; it does not classify every
kind of untranslated prose or change actual figures, tables, or code.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.domain.valueobject.rfc.contents.paragraph import Paragraph


def inspect(obj):
    classifier = Paragraph('x', is_code=True)
    findings = []
    for i, paragraph in enumerate(obj['contents']):
        if not paragraph.get('raw') or paragraph.get('toc'):
            continue
        text = paragraph['text']
        if classifier._without_prose_ellipses(text) == text:
            continue
        if not classifier._find_code_pattern(text):
            findings.append({'rfc': obj['number'], 'paragraph': i, 'text': text})
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rfc', type=int, nargs='+')
    parser.add_argument('--format', choices=['text', 'json'], default='text')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    findings = []
    scanned = 0
    for path in sorted((ROOT / 'data').glob('*/*-trans.json')):
        match = re.fullmatch(r'rfc(\d+)-trans\.json', path.name)
        if not match or (args.rfc and int(match[1]) not in args.rfc):
            continue
        scanned += 1
        findings.extend(inspect(json.loads(path.read_text())))
    if args.format == 'json':
        print(json.dumps({'scanned': scanned, 'findings': findings}, ensure_ascii=False, indent=2))
    else:
        print(f'Scanned {scanned} RFCs: {len(findings)} prose ellipsis candidates')
        for row in findings:
            print(f"RFC {row['rfc']} [{row['paragraph']}]: {row['text'][:160]}")
    return int(args.check and bool(findings))


if __name__ == '__main__':
    raise SystemExit(main())

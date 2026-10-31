"""Find untranslated prose for human review; preserve literal RFC material.

English-only text is not automatically a translation defect. This read-only
audit excludes raw blocks, references, author addresses and obvious literals.
--check-guidance checks only unambiguous example/model introduction phrases.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.lint_translation import update_reference_section_state

JAPANESE = re.compile(r'[\u3040-\u30ff\u3400-\u9fff]')
AUTHOR_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*\.?\s+)?(?:authors?|editors?|contributors?)(?:'s?|’s?)?\s+(?:addresses|address|information)\s*$", re.I)
GUIDANCE = re.compile(
    r'^(?:with an input of:|for example, with an input of:|an HTML formatter might generate:|'
    r'content model:(?: only text content\.| this element does not have any contents\.)?|'
    r'in (?:any|this) order:|in any order, but at least one of:|allowed values:)$', re.I)


def is_bibliography_or_names(text, context=''):
    # A citation can occur outside a recognized References section, including
    # numbered references in older RFCs. Do not translate its document title.
    if re.fullmatch(r'RFC \d+ [A-Z]: "[^"]+" \([^)]+\)', text):
        return True
    if re.fullmatch(r'[o*+-] "[^"]+" \[[^\]]+\]', text):
        return True
    if re.match(r'^\[[^\]]+\] [A-Z][\w\'-]+, "', text) and re.search(r'\b(?:18|19|20)\d{2}\b', text):
        return True
    if (re.match(r"^\[[^\]]+\]\s+(?:[A-Z][\w'-]+,\s+[A-Z]\.|(?:IANA|IETF|IEEE|W3C|ISO|ITU|NIST)\b)", text)
            and re.search(r'"[^"]+"', text)
            and re.search(r'\b(?:18|19|20)\d{2}\b|https?://|\bDOI\b', text)):
        return True
    if text.startswith('o RFC ') and len(re.findall(r'\bRFC \d+', text)) >= 3:
        return True
    # Pure contributor lists have no prose to translate.
    names = re.split(r',\s*(?:and\s+)?|\s+and\s+', re.sub(r'\s*\([^)]*\)', '', text.rstrip('.')))
    people_context = re.search(r'acknowledg|contribut|authors?|editors?|list of people|following (?:people|individuals)|thanks', context, re.I)
    name_word = r"(?:[A-ZÀ-ÖØ-Þ][\w'-]*\.?|de|van|von|da|del|der|den|la|le)"
    if people_context and len(names) >= 3 and all(re.fullmatch(name_word + r'(?: ' + name_word + r'){1,5}', name) for name in names):
        return True
    return False


def inspect(obj):
    findings = []
    references = authors = False
    section = previous = ''
    for i, paragraph in enumerate(obj['contents']):
        text = ' '.join(paragraph.get('text', '').split())
        ja = paragraph.get('ja', '')
        heading = bool(paragraph.get('section_title'))
        if heading:
            section = text
        context = section + ' ' + previous
        previous = text
        references = update_reference_section_state(references, text, heading)
        if AUTHOR_HEADING.fullmatch(text):
            authors = True
            continue
        if heading or re.match(r'^(?:Full Copyright Statement|Copyright Notice|Intellectual Property)', text, re.I):
            authors = False
        if paragraph.get('raw') or paragraph.get('toc') or JAPANESE.search(ja):
            continue
        if references and not heading or authors:
            continue
        if is_bibliography_or_names(text, context):
            continue
        # Hyphen-separated words in a lone identifier are not English prose.
        if re.fullmatch(r'(?:[o*+-]\s+)?[A-Za-z][\w.-]*', text):
            continue
        if re.fullmatch(r'[o*+-] [A-Za-z][\w-]* \(\d{4}-\d{2}-\d{2}\)', text):
            continue
        if heading and re.fullmatch(r"[\d.A-Z]+\s+<[^>]+>\s*=\s*'[^']+'", text):
            continue
        if heading and re.fullmatch(r'[\d.]+\s+\x27[\w-]+\x27(?:\s+\(0x[0-9a-fA-F]+\))?', text):
            continue
        if re.match(r'^(?:Copyright\b|https?://|urn:|\S+@\S+|#|--|BEGIN\b|END\b|HTTP/|v=0\b)', text, re.I):
            continue
        words = re.findall(r'[A-Za-z]+', text)
        if GUIDANCE.fullmatch(text):
            kind = 'guidance'
        elif (len(words) >= 5
              and re.search(r'\b(?:the|this|these|that|with|for|should|must|may|are|is|can|will|from|only|when|one|and)\b', text)
              and not re.search(r'[{}]|::=', text)):
            kind = 'prose_candidate'
        else:
            continue
        findings.append({'rfc': obj['number'], 'paragraph': i, 'kind': kind,
                         'empty': not ja.strip(), 'text': paragraph['text'], 'ja': ja})
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rfc', nargs='+', type=int)
    parser.add_argument('--format', choices=['text', 'json'], default='text')
    parser.add_argument('--check-guidance', action='store_true')
    args = parser.parse_args()
    findings = []
    count = 0
    for path in sorted((ROOT / 'data').glob('*/rfc[0-9]*-trans.json')):
        obj = json.loads(path.read_text())
        if args.rfc and obj['number'] not in args.rfc:
            continue
        count += 1
        findings.extend(inspect(obj))
    if args.check_guidance:
        findings = [f for f in findings if f['kind'] == 'guidance']
    counts = Counter(f['kind'] for f in findings)
    if args.format == 'json':
        print(json.dumps({'scanned': count, 'counts': counts, 'findings': findings}, ensure_ascii=False, indent=2))
    else:
        print(f'Scanned {count} RFCs: {dict(counts)}')
        for f in findings:
            print(f"RFC {f['rfc']} [{f['paragraph']}] {f['kind']}: {f['text'][:180]}")
    return int(args.check_guidance and counts['guidance'] > 0)


if __name__ == '__main__':
    raise SystemExit(main())

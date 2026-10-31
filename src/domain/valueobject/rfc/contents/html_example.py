"""Conservative recognition of literal HTML examples in RFC plain text.

Angle-bracket protocol variables and inline tag explanations are prose.  Only
physical line boundaries may separate an example from its surrounding prose.
"""

import re
from xml.etree import ElementTree


TAGS = r'html|head|body|title|meta|link|img|a|p|div|span|form|input|table|tr|td|th|object|iframe|embed|script|style|h[1-6]|br|hr|ul|ol|li|blockquote|pre|b|i'
START = re.compile(rf'^\s*<(?:!doctype\s+html\b|/?(?:{TAGS})(?=[\s/>]))', re.I)
TOKEN = re.compile(r'''<[^<>"']*(?:"[^"]*"[^<>"']*|'[^']*'[^<>"']*)*>''', re.S)
VOID = re.compile(r'^<(?:img|meta|link|input|br|hr|embed)\b', re.I)


def is_xml_example(text):
    text = text.strip()
    if not text.startswith('<'):
        return False
    try:
        ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return False
    return True


def is_html_example(text):
    text = text.strip()
    if not START.match(text):
        return False
    if re.match(r'<!doctype\s+html\b', text, re.I):
        return True  # RFCs also use intentionally abbreviated declarations.
    tokens = list(TOKEN.finditer(text))
    if not tokens:
        return False
    # Bare tags are examples only when the entire line is markup, not when a
    # protocol field such as "<head> is omitted ..." is being described.
    if not TOKEN.sub('', text).strip():
        return True
    if re.fullmatch(r'<html>\s*\.\.\.', text, re.I):
        return True
    return bool(re.search(r'<[^>]+\s[\w:-]+\s*=', text)
                and re.search(r'</[a-z][\w:-]*\s*>', text, re.I))


def split_html_examples(text):
    """Yield (text, force_raw) while retaining every original source line."""
    lines = text.splitlines(keepends=True)
    prose = []
    i = 0
    while i < len(lines):
        rest = ''.join(lines[i:])
        if START.match(lines[i]):
            first = TOKEN.match(rest.lstrip())
            # A void element can end before prose in the same paragraph.  Do
            # not split an inline mention on the same physical line.
            if first and VOID.match(first.group()):
                end = len(rest) - len(rest.lstrip()) + first.end()
                tail = rest[end:]
                if not tail.strip() or tail.startswith('\n'):
                    count = rest[:end].count('\n') + 1
                    if prose:
                        yield ''.join(prose), False
                        prose = []
                    yield ''.join(lines[i:i + count]), True
                    i += count
                    continue
            if is_html_example(rest):
                if prose:
                    yield ''.join(prose), False
                yield rest, True
                return
        prose.append(lines[i])
        i += 1
    if prose:
        yield ''.join(prose), False


def ends_with_markup_example(text):
    if is_xml_example(text):
        return True
    parts = list(split_html_examples(text))
    return bool(parts and parts[-1][1])

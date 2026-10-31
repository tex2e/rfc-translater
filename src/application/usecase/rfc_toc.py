"""原文の目次と本文見出しから、保存を伴わない対訳表示データを作る。"""

from __future__ import annotations

import re
import textwrap
import unicodedata


LABEL = re.compile(
    r'^(?P<indent>[ \t]*)(?P<label>Appendix\s+[A-Z]\.?|'
    r'\d+(?:\.\d+)*[a-z]?\.?|[A-Z](?:\.\d+)+\.?|[A-Z]\.)'
    r'(?P<gap>[ \t]+)(?P<title>.*)$')
PAGE = re.compile(r'(?P<leader>[ .]*\.[ .]*\.[ .]*)(?P<page>\d+|[ivxlcdm]+)\s*$', re.IGNORECASE)


def _normalize(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', text).split()).casefold()


def _parts(text: str) -> tuple[str | None, str, str]:
    """正規化した番号、原文どおりの番号・空白、タイトル。"""
    match = LABEL.match(text)
    if not match:
        indent = text[:len(text) - len(text.lstrip(' \t'))]
        return None, indent, text[len(indent):]
    key = re.sub(r'^Appendix\s+', '', match['label']).rstrip('.')
    return key, match['indent'] + match['label'] + match['gap'], match['title']


def _without_page(text: str) -> str:
    return PAGE.sub('', text).rstrip()


def _width(text: str) -> int:
    """点線の計算用。原文の空白自体は変更しない。"""
    return sum(0 if unicodedata.combining(c) else
               2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1
               for c in text.expandtabs(8))


def _japanese_title(text: str, numbered: bool) -> str:
    if not numbered:
        return text.strip()
    # 本文見出しの番号は捨て、目次原文の番号と空白を再利用する。
    text = re.sub(r'^付録\s*([A-Z](?:\.\d+)*)[.．:]?\s*', '', text.strip())
    key, _, title = _parts(text)
    if key is not None:
        return title.strip()
    return re.sub(r'^(?:\d+(?:\.\d+)*[a-z]?|[A-Z](?:\.\d+)*)[.．]\s*', '', text).strip()


def make_toc_rows(contents: list[dict], paragraph_ids: list[str | None],
                  heading_id) -> dict[int, list[dict]]:
    """TOCブロックごとの対訳行。raw本文とjaには一切書き込まない。

    番号は本文の見出しだけから解決し、番号なしは原文タイトルの一意一致で解決する。
    不明・曖昧な項目は英語を残し、呼び出し元が未対応として報告できるようにする。
    """
    by_number, by_title = {}, {}
    for i, paragraph in enumerate(contents):
        if paragraph.get('raw') or paragraph.get('toc'):
            continue
        text = paragraph['text'].strip()
        key, _, title = _parts(text)
        target = heading_id(text) if paragraph.get('section_title') else paragraph_ids[i]
        heading = {'ja': paragraph.get('ja', '').strip(), 'target': target,
                   'title': _normalize(title if paragraph.get('section_title') else text)}
        if paragraph.get('section_title') and key is not None:
            by_number.setdefault(key, []).append(heading)
        by_title.setdefault(_normalize(title if paragraph.get('section_title') else text), []).append(heading)

    result = {}
    for i, paragraph in enumerate(contents):
        if not (paragraph.get('raw') and paragraph.get('toc')):
            continue
        # 各項目は原文の物理行を保持する。番号のない独立項目も本文との一致で識別する。
        entries = []
        for line in paragraph['text'].split('\n'):
            key, _, title = _parts(line)
            is_title = _normalize(_without_page(title)) in by_title
            # 継続行の単語が別の章名と一致しても、その章へ誤リンクしない。
            if entries and key is None and line.strip():
                previous = entries[-1]
                previous_key, _, _ = _parts(previous[0])
                leading = len(line) - len(line.lstrip(' \t'))
                previous_leading = len(previous[0]) - len(previous[0].lstrip(' \t'))
                if (previous_key is not None and leading > previous_leading
                        and not PAGE.search(previous[-1])):
                    previous.append(line)
                    continue
            if (key is not None or is_title or not line.startswith((' ', '\t')) or not line.strip() or not entries
                    or not entries[-1][-1].strip()):
                entries.append([line])
            else:
                entries[-1].append(line)
        rows = []
        for lines in entries:
            key, prefix, first_title = _parts(lines[0])
            title = _without_page(' '.join([first_title] + [s.strip() for s in lines[1:]]))
            candidates = by_number.get(key, []) if key is not None else by_title.get(_normalize(title), [])
            # 同じ番号が複数あるときは、先勝ちで誤った章へリンクしない。
            heading = candidates[0] if len(candidates) == 1 else None
            page = PAGE.search(lines[-1])
            # 長い題名の直後に「.89」だけが付く古い形式。本文題名の一致を確認して
            # ページ番号と判定し、TLS 1.3のような題名の一部を誤って切り落とさない。
            if heading and heading['title'] != _normalize(title):
                single_dot = re.search(r'\.(\d+)$', title)
                if single_dot and heading['title'] == _normalize(title[:single_dot.start()]):
                    title = title[:single_dot.start()]
                    page = re.search(r'(?P<page>\d+)$', lines[-1])
            if heading and heading['title'] != _normalize(title):
                heading = None
            ja = _japanese_title(heading['ja'], key is not None) if heading else ''
            source = '\n'.join(lines)
            translated = bool(ja)
            if ja:
                ja = prefix + ja
                if page:
                    dots = max(2, _width(lines[-1]) - _width(ja) - len(page['page']) - 1)
                    ja += ' ' + '.' * dots + page['page']
            else:
                ja = source
            # 共通の字下げも復元する。空行には空白を追加しない。
            indent = ' ' * paragraph.get('indent', 0)
            rows.append({'en': textwrap.indent(source, indent), 'ja': textwrap.indent(ja, indent),
                         'target': heading['target'] if heading else None,
                         'translated': translated, 'blank': not source.strip()})
        result[i] = rows
    return result

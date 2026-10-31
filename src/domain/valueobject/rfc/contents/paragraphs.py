
# fetch_rfc_txt.py でのみ使用するデータ構造

import re
from .paragraph import Paragraph
from .html_example import split_html_examples


class Paragraphs:
    # 段落(Paragraph)の集まり
    #
    # Properties:
    # * paragraphs: 段落(Paragraph)の配列

    @staticmethod
    def _ldap_schema_end(text):
        """Find the end of an LDAP schema definition, respecting quoted DESC."""
        if not re.match(r"^\s*\(\s*(?:[0-9.]+|[A-Za-z][\w.-]*)\s+NAME\s+['\"]", text):
            return None
        depth = 0
        quote = None
        escaped = False
        for i, char in enumerate(text):
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif quote:
                if char == quote:
                    quote = None
            elif char in "'\"":
                quote = char
            elif char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    return i + 1
        return None

    def __init__(self, text: str, ignore_header=True):
        # Arguments:
        # * text: 全ての段落を含む1つの文字列（段落の区切りは\n\n）
        # * ignore_header: 最初の段落（ヘッダ）は翻訳しない

        # 2つ以上改行が連続する部分が段落区切りなので、段落ごとに文字列を分割する
        chunks = re.compile(r'\n\n+').split(text)
        # Complete HTML documents may contain blank lines (RFC 5707). Keep
        # their text nodes and split attribute lines in one literal block.
        grouped = []
        i = 0
        while i < len(chunks):
            chunk = chunks[i]
            start = re.match(r'^\s*(?:<!doctype\s+html\b|<html\b|<\?xml\b)', chunk, re.I)
            if re.match(r'^\s*<\?xml\b', chunk):
                following = chunk + ('\n' + chunks[i + 1] if i + 1 < len(chunks) else '')
                start = start and re.search(r'<html\b|<!doctype\s+html\b', following, re.I)
            if re.fullmatch(r'\s*(?:<html>|<!doctype\s+html[^\n]*)\s*\.\.\.\s*', chunk, re.I):
                start = False
            if start:
                for j in range(i, len(chunks)):
                    if re.search(r'</html\s*>', chunks[j], re.I):
                        candidate = '\n\n'.join(chunks[i:j + 1])
                        if re.search(r'<html\b|<!doctype\s+html\b', candidate, re.I):
                            chunk = candidate
                            i = j
                        break
                    # Do not consume subsequent sections to find an unrelated
                    # closing tag after an intentionally abbreviated example.
                    if j > i and re.match(r'^\d+\.\s+[A-Z]', chunks[j]):
                        break
            grouped.append(chunk)
            i += 1
        chunks = grouped
        self.paragraphs = []
        literal_end = None
        state_table = False
        for i, chunk in enumerate(chunks):
            # MIB modules and explicitly fenced source files contain English
            # DESCRIPTION strings too. They remain code across blank lines.
            if literal_end is None:
                candidate_end = None
                if re.search(r'<CODE BEGINS\b', chunk, re.I):
                    candidate_end = re.compile(r'<CODE ENDS\b', re.I)
                elif re.search(r'^ *[\w-]+\s+DEFINITIONS\s*::=\s*BEGIN\b', chunk, re.M):
                    candidate_end = re.compile(r'^ *END(?:[ \t]*--[^\n]*)?[ \t]*$', re.M)
                if candidate_end and candidate_end.search('\n\n'.join(chunks[i:])):
                    literal_end = candidate_end
            if literal_end is not None:
                paragraph = Paragraph(chunk, is_code=True)
                paragraph.is_code = True
                paragraph.is_section_title = False
                paragraph.is_toc = False
                self.paragraphs.append(paragraph)
                if literal_end.search(chunk):
                    literal_end = None
                continue
            # State transition tables in RFC TXT use blank lines between
            # rows. Retain their column alignment rather than translating
            # isolated event descriptions as prose (e.g. RFC 7275).
            table_header = re.search(
                r'^ *STATE +EVENT +(?:NEW|NEXT) STATE *\n *[-=]{10,}', chunk, re.M | re.I)
            table_row = re.search(r'\S {4,}[A-Z][A-Z0-9_-]{2,}[ \t]*$', chunk, re.M)
            if table_header or state_table and table_row:
                state_table = True
                paragraph = Paragraph(chunk, is_code=True)
                paragraph.is_toc = False
                paragraph.is_section_title = False
                self.paragraphs.append(paragraph)
                continue
            state_table = False
            # LDAP schemas contain English DESC strings, and old TXT sources
            # can put explanatory prose immediately after their closing ')'.
            schema_end = self._ldap_schema_end(chunk)
            if schema_end is not None:
                self.paragraphs.append(Paragraph(chunk[:schema_end], is_code=True))
                chunk = re.sub(r'^(?:[ \t]*\n)+', '', chunk[schema_end:])
                if not chunk.strip():
                    continue
            # Annotated CBOR blocks use / comments / inside array literals.
            if (re.match(r'^\s*\[\s*\d+,\s*/\s*type code\s*/', chunk)
                    and chunk.rstrip().endswith(']')):
                self.paragraphs.append(Paragraph(chunk, is_code=True))
                continue
            # 最初の段落は著者の情報などのメタ情報のため翻訳しない
            is_header = (i == 0 and ignore_header)
            # RFC 7991/7992 show XML input mixed with ordinary text nodes.
            # An explicit introduction makes the following paragraph an
            # example; inline markup elsewhere must remain translatable.
            input_example = i > 0 and re.search(
                r'(?:with an input of|for this input|for example)\s*:\s*$', chunks[i - 1], re.I)
            input_example = bool(input_example and re.search(r'<[\w:-]+\s+[\w:-]+\s*=', chunk))
            # 文字列を段落にしてから配列に追加していく
            # Keep existing XML/code blocks intact, including text nodes that
            # happen to use HTML tag names such as <body> or <input>.
            paragraph = Paragraph(chunk, is_code=is_header or input_example)
            introduction = re.match(r'^\s*[A-Za-z][^<>\n]*:\n', chunk)
            if paragraph.is_code and (is_header or not introduction):
                self.paragraphs.append(paragraph)
                continue
            parts = split_html_examples(chunk)
            for part, is_example in parts:
                paragraph = Paragraph(part, is_code=is_header or is_example)
                self.paragraphs.append(paragraph)

    def __getitem__(self, key: int) -> Paragraph:
        assert isinstance(key, int)
        return self.paragraphs[key]

    def __iter__(self) -> iter:
        return iter(self.paragraphs)



# fetch_rfc_txt.py でのみ使用するデータ構造

import re
from .paragraph import Paragraph
from .html_example import split_html_examples


class Paragraphs:
    # 段落(Paragraph)の集まり
    #
    # Properties:
    # * paragraphs: 段落(Paragraph)の配列

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
        for i, chunk in enumerate(chunks):
            # 最初の段落は著者の情報などのメタ情報のため翻訳しない
            is_header = (i == 0 and ignore_header)
            # 文字列を段落にしてから配列に追加していく
            # Keep existing XML/code blocks intact, including text nodes that
            # happen to use HTML tag names such as <body> or <input>.
            paragraph = Paragraph(chunk, is_code=is_header)
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


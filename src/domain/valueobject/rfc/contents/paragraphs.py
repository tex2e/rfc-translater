
# fetch_rfc_txt.py でのみ使用するデータ構造

import re
from .paragraph import Paragraph


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
        self.paragraphs = []
        for i, chunk in enumerate(chunks):
            # 最初の段落は著者の情報などのメタ情報のため翻訳しない
            is_header = (i == 0 and ignore_header)
            # 文字列を段落にしてから配列に追加していく
            paragraph = Paragraph(chunk, is_code=is_header)
            self.paragraphs.append(paragraph)

    def __getitem__(self, key: int) -> Paragraph:
        assert isinstance(key, int)
        return self.paragraphs[key]

    def __iter__(self) -> iter:
        return iter(self.paragraphs)


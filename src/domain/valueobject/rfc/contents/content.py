
# fetch_rfc_xml.py でのみ使用するデータ構造

import re


# RFCの段落情報を格納するクラス
class Content:
    def __init__(self, text: str, indent=0, title=False, section_title=False, 
                 raw=False, toc=False, tag='') -> None:
        self.text = text
        self.indent = indent
        self.title = title
        self.section_title = section_title
        self.raw = raw
        self.toc = toc
        self.tag = tag
        self._normalize_text()

    def __eq__(self, other: object) -> bool:
        return (
            self.text == other.text and
            self.indent == other.indent and
            self.title == other.title and
            self.section_title == other.section_title and
            self.raw == other.raw and
            self.toc == other.toc
        )

    def __repr__(self) -> str:
        return (
            f'<Content indent="{self.indent}" title="{self.title}" ' +
            f'sectitle="{self.section_title}" raw="{self.raw}" ' +
            f'toc="{self.toc}" text="{self.text}">')

    def _normalize_text(self):
        # 文章のときの処理
        if not self.raw:
            self.text = re.sub(r'([a-zA-Z])-\n *', r'\1-', self.text)  # ハイフンを繋げる
            self.text = re.sub(r'\n *', ' ', self.text)  # 複数行を1行にまとめる
            self.text = re.sub(r' +', ' ', self.text)  # 連続した空白を1つにまとめる
        # 以下xml2rfc対応処理
        self.text = re.sub(r'\xa0', ' ', self.text)  # "Section 1" の空白を正規化する
        self.text = re.sub(r'‑', '-', self.text)  # "[QUIC‑RECOVERY]" のハイフンを正規化する
        # Line Separator (\x2028) と Paragraph Separator (\x2029) の削除
        self.text = re.sub(r'\u2028|\u2029', ' ', self.text)

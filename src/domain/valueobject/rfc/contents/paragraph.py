
# fetch_rfc_txt.py でのみ使用するデータ構造

import re
import textwrap
from ....services.rfcutils import RfcUtils


# 段落がページをまたぐことを表す文字
BREAK = '\x07\x07\x07'
# 箇条書き（複数行）で改行を表す文字列
BREAK_INSERT = '\x06\x06\x06'


class Paragraph:
    # 段落情報を持つクラス。コードや図表かの判定はここで行う。
    #
    # Properties:
    # * text: 段落の文章
    # * indent: 段落のインデント数
    # * is_code: コードや図表かどうかのフラグ。Trueの場合は翻訳処理を行わない
    # * is_section_title: 見出しかどうかのフラグ
    # * is_toc: 目次かどうかのフラグ

    TYPE_CODE = 'code'
    TYPE_SECTIOIN_TITLE = 'section_title'
    TYPE_TOC = 'toc'
    TYPE_SENTENCE = 'sentence'

    def __init__(self, text: str, is_code=None):
        # 段落文章（インデントは除く）
        self.text = textwrap.dedent(text.lstrip('\n').rstrip())
        # インデント数の取得
        self.indent = RfcUtils.get_line_len_diff(text, self.text)
        # コード・図表の判定
        self.is_code = is_code
        if not self.is_code:
            self.is_code = \
                not self._find_list_pattern(self.text) \
                and self._find_code_pattern(self.text)
        # 箇条書き（複数行）の判定
        is_ul_li = False
        if not self.is_code:
            if is_ul_li := self._find_ul_li(self.text):
                self.text = self._insert_newline_between_li(self.text)
                # pprint(self.text)

        # 見出しの判定
        self.is_section_title = \
            self.indent <= 2 and \
            self._find_section_title_pattern(self.text)
        # 目次の判定
        self.is_toc = self._find_toc_pattern(self.text)
        # 引用・注釈の判定
        if self._find_note(self.text):
            self.is_code = False  # 本文と見なす
            self.indent += 15  # 引用だとわかるように字下げする
            self.text = self._convert_note_from_figure_to_text(self.text)  # 「|  」の除去

        # 複数に分類された時の優先順位: 目次 > セクション > 図やコード
        if self.is_toc:
            self.is_code = True
            self.is_section_title = False
        elif self.is_code and self.is_section_title:
            self.is_code = False

        # BREAKの置き換え (段落がページをまたいだときの処理)
        if self.is_code:
            # 図表・コードのときは、改行に置き換える
            self.text = self.text.replace(BREAK, '\n')
        else:
            # 箇条書き（複数行）以外の文章のときは、空白1つに置き換える (ページ間の余分な空白も取り除く)
            self.text = re.sub(BREAK + r'\s+', ' ', self.text)

        # 文章のときの処理
        if not self.is_code:
            self.text = re.sub(r'([a-zA-Z])-\n *', r'\1-', self.text)  # ハイフンを繋げる
            self.text = re.sub(r'\n *', ' ', self.text)  # 複数行を1行にまとめる
            self.text = re.sub(r' +', ' ', self.text)  # 連続した空白を1つにまとめる

        if is_ul_li:
            # 箇条書き（複数行）の場合、項目同士の間に空行を入れる
            self.text = re.sub(r' *' + BREAK_INSERT + r' *', '\n\n', self.text).strip("\n")
            # pprint(is_ul_li)

    def __str__(self):
        return 'Paragraph: level: %d, is_code: %s\n%s' % \
            (self.indent, self.is_code, self.text)

    def get_text_type(self):
        if self.is_toc:
            return self.TYPE_TOC
        if self.is_code:
            return self.TYPE_CODE
        if self.is_section_title:
            return self.TYPE_SECTIOIN_TITLE
        return self.TYPE_SENTENCE

    # 目次の判定
    def _find_toc_pattern(self, text: str) -> bool:
        cond1 = re.search(r'\.{6}|(?:\. ){6}', text)
        # 1. Introduction から始まって Authors' Addresses で終わるとき
        cond2 = \
            re.search(r'\A\s*1\. +(?:Introduction|Overview|Purpose)', text, re.MULTILINE) and \
            re.search(r'Author(?:s\'|\'s) Address(?:es)?\s*\Z', text, re.MULTILINE)
        return (cond1 or cond2)

    # 箇条書きなどの判定（1行）
    def _find_list_pattern(self, text: str) -> bool:
        return re.match(r'(?:[-o*+]|\d{1,2}\.) +[a-zA-Z]', text)

    # 箇条書きの判定（複数行）
    def _find_ul_li(self, text: str) -> bool:
        lines = text.split('\n')
        if len(lines) <= 2:
            return False
        indent = RfcUtils.get_indent(lines[0])
        regex = re.compile(rf'^(?: {{{indent}}}\*  | {{{indent+3}}})[a-zA-Z0-9_<]', re.MULTILINE)
        return all(re.match(regex, line) for line in lines)

    # 箇条書き（複数行）の場合は、各項目の間に改行を入れる
    # 例：
    #    *  Item1      <---この後ろに改行を入れる
    #    *  Item2
    def _insert_newline_between_li(self, text: str) -> str:
        lines = text.split('\n')
        res = []
        for line in lines:
            if re.match(r'^ *\*  ', line):
                res.append(BREAK_INSERT)
            res.append(line)
        return "\n".join(res).strip("\n")

    # 図表・ソースコード・数式の判定
    def _find_code_pattern(self, text: str) -> bool:
        if (re.search(r'\A\s*As described in \[RFC\d+\],', text)):  # For RFC9015
            return False

        conds = []
        conds.append(re.search(r'----|___|~~~|\+\+\+|\*\*\*|\+-\+-\+-\+|=====', text))  # fig
        conds.append(re.search(r'   -{1,3}>|<-{1,3}   ', text))  # fig
        conds.append(re.search(r'\.{4}|(?:\. ){4}', text))  # TOC
        conds.append(text.find('+--') >= 0)  # directory tree
        conds.append(re.search(r'^\/\*|(?<=\s)\/\* | \*\/$', text))  # src
        conds.append(re.search(r'(?:enum|struct|object) \{', text))  # tls
        conds.append(re.search(r'(?:HEADERS)\n\s*:[a-z]+ = ', text))  # http/2
        conds.append(re.search(r'\s::=\s', text))  # syntax
        conds.append(re.search(r'\s\*\("', text))  # syntax
        conds.append(re.search(r'": (?:[\[\{\"\']|true,|false,)', text))  # json
        conds.append(re.search(r'= +[\[\(\{<*%#&]', text))  # src, syntax
        conds.append(len(re.compile(r'[{}]$', re.MULTILINE).findall(text)) >= 2)  # src
        conds.append(len(re.compile(r'[;]$', re.MULTILINE).findall(text)) >= 3)  # src
        conds.append(len(re.compile(r'^</', re.MULTILINE).findall(text)) >= 2)  # xml
        conds.append(re.search(r'[/|\\] +[/|\\]', text))  # figure
        conds.append(len(re.compile(r'^\s*\|', re.MULTILINE).findall(text)) >= 3)  # table
        conds.append(len(re.compile(r'\*\s*$', re.MULTILINE).findall(text)) >= 3)  # table
        conds.append(len(re.compile(r'[0-9a-zA-Z] {10,}[0-9a-zA-Z]', re.MULTILINE).findall(text)) >= 2)  # table
        conds.append(len(re.compile(r'^\s*/', re.MULTILINE).findall(text)) >= 3)  # syntax
        conds.append(len(re.compile(r'^\s*;', re.MULTILINE).findall(text)) >= 3)  # syntax
        conds.append(len(re.compile(r'^\s*\[(?![A-Z])', re.MULTILINE).findall(text)) >= 3)  # syntax
        conds.append(len(re.compile(r'\]\s*$', re.MULTILINE).findall(text)) >= 3)  # syntax
        conds.append(len(re.compile(r'^\s*:', re.MULTILINE).findall(text)) >= 3)  # src
        conds.append(len(re.compile(r'^\s*o ', re.MULTILINE).findall(text)) >= 4)  # list
        conds.append(re.match(r'^E[Mm]ail: ', text))  # Authors' Addresses
        conds.append(re.search(r'(?:[0-9A-F]{2} ){8} (?:[0-9A-F]{2} ){7}[0-9A-F]{2}', text))  # hexdump
        conds.append(re.search(r'000 {2,}(?:[0-9a-f]{2} ){16} ', text))  # hexdump
        conds.append(re.search(r'[0-9a-zA-Z]{32,}$', text))  # hex
        conds.append(re.search(r'" [\|/] "', text))  # BNF syntax
        conds.append(re.match(r'^\s*[-\w\d]+\s+=\s+[-\w\d /]{1,40}$', text))  # syntax
        conds.append(re.match(r'^\s*[-\w\d]+\s+=\s+"[-\w\d ]{1,20}"$', text))  # syntax
        conds.append(re.search(r'^\s*[-\w\d]+\s+=\s+1\*.', text))  # syntax
        conds.append(len(re.compile(r'^\s*Content-Type:\s+[a-z]+/[a-z]+\s*$', re.MULTILINE).findall(text)) >= 1)  # HTML
        conds.append(len(re.compile(r'^\s*[SC]: ', re.MULTILINE).findall(text)) >= 2)  # server-client
        conds.append(len(re.compile(r'^\s*-- ', re.MULTILINE).findall(text)) >= 2)  # syntax
        conds.append(len(re.compile(r'^\s*[0-9a-f]0: ', re.MULTILINE).findall(text)) >= 3)  # hexdump
        conds.append(len(re.compile(r'^\s*(?:IN   |OUT  ).', re.MULTILINE).findall(text)) >= 2)  # SNMP Dispatcher
        conds.append(re.search(r' {2,}---> {2,}', text))  # fig
        conds.append(re.search(r' =/ "', text))  # syntax
        conds.append(re.search(r'   =/ ', text))  # syntax
        conds.append(re.search(r'" ":" ', text))  # syntax
        if any(conds):
            return True

        # 数式やプログラムを検出する
        # 以下のパターンが (3 + 行数-1) 個出現した場合、数式やプログラムと判断する：
        #   * 記号「~+*=!#<>{}^@:;」が含まれること
        #   * 丸括弧「(」の場合、直前には空白がないこと
        #   * マイナス「-」やスラッシュ「/」の場合、直前に空白があること
        #   * HTTPのContent-Typeのパターンがある場合
        lines_num = len(text.split("\n"))
        threshold = 3 + (lines_num - 1) * 1
        if len(re.findall(r'[~+*=!#<>{}^@:;]|[^ ]\(| [-/]|(?:application|text)/', text)) >= threshold \
                and (not re.search(r'[,:]\)?$|(?<!\.\.)[.]\)?$', text)):  # 文末が「.,:」ではない
            return True
        return False

    # 見出しの判定
    def _find_section_title_pattern(self, text: str) -> bool:
        # "N." が現れたときは見出しとして検出する
        if len(text.split('\n')) > 2:  # 3行以上の場合は除外
            return False
        if len(text.split('\n')) == 2:  # 2行の場合、1行目が「〜.」の形式かつ2行目の開始位置が1行目と揃っていないとき除外
            split_text = text.split('\n')
            if m := re.match(r'^((?:[^ ]+\.)+[ ]+)', split_text[0]):
                first_line_start_pos = len(m[1])
                if not re.match(r'[ ]{%d}\b' % first_line_start_pos, split_text[1]):
                    return False
        if text.endswith('.'):  # 末尾が「.」で終了
            return False
        if text.endswith(':'):
            return False
        if text.endswith(','):
            return False
        if re.match(r'^Appendix [A-Z](?:\. [-a-zA-Z0-9\'\.: ]+)?$', text):
            return True
        return re.match(r'^(?:\d{1,2}\.)+(?:\d{1,2})? |^[A-Z]\.(?:\d{1,2}\.)+(?:\d{1,2})? |^[A-Z]\.\d{1,2} ', text)

    # 引用・注釈の正規表現
    REGEX_PATTERN_NOTE1 = r'\A(?:   ){0,3}\|  _?(?=[a-zA-Z0-9"\'\[\(])'     # 1行目〜L-1行目
    REGEX_PATTERN_NOTE2 = r'\A(?:   ){0,3}\|  (?=[a-zA-Z0-9"\'\[\(]).*\.$'  # L行目

    # 引用・注釈の判定
    def _find_note(self, text: str) -> bool:
        # 段落全体が | から始まる場合は引用・注釈と見なす。最後の行は必ず「.」で終わっていることが条件。
        lines = text.split("\n")
        for line in lines[:-1]:
            if not re.search(self.__class__.REGEX_PATTERN_NOTE1, line):
                return False
        for line in lines[-1:]:
            if not re.search(self.__class__.REGEX_PATTERN_NOTE2, line):  # 追加で行末が「.」かどうか確認する
                return False
        return True

    # 注釈を図表からテキストに変換する
    def _convert_note_from_figure_to_text(self, text: str) -> str:
        # 各行の行頭文字列「  |  」を取り除く。
        lines_with_pipe = text.split("\n")
        lines_without_pipe = []
        for line in lines_with_pipe:
            tmp = re.sub(self.__class__.REGEX_PATTERN_NOTE1, ' ', line)
            lines_without_pipe.append(tmp)
        return "\n".join(lines_without_pipe).strip()


import requests
from lxml import html
import re
import textwrap
import json
import os

from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')

# 段落がページをまたぐことを表す文字
BREAK = '\n\x07\n'

class Paragraph:
    # 段落情報を持つクラス
    #
    # Properties:
    # * text: 段落の文章
    # * indent: 段落のインデント数
    # * is_code: コードや図表かどうかのフラグ。Trueの場合は翻訳処理を行わない
    # * is_section_title: 見出しかどうかのフラグ
    # * is_toc: 目次かどうかのフラグ

    def __init__(self, text, is_code=None):
        # 段落文章（インデントは除く）
        self.text = textwrap.dedent(text.lstrip('\n').rstrip())
        # インデント数の取得
        self.indent = _get_line_len_diff(text, self.text)
        # コード・図表の判定
        self.is_code = is_code
        if not self.is_code:
            self.is_code = (
                not self._find_list_pattern(self.text)
                and self._find_code_pattern(self.text))
        # 見出しの判定
        self.is_section_title = (
            self.indent <= 2 and
            self._find_section_title_pattern(self.text))
        # 目次の判定
        self.is_toc = self._find_toc_pattern(self.text)

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
            # 文章のときは、空白1つに置き換える (ページ間の余分な空白も取り除く)
            self.text = re.sub(BREAK + r'\s+', ' ', self.text)

        # 文章のときの処理
        if not self.is_code:
            self.text = re.sub(r'([a-zA-Z])-\n *', r'\1-', self.text)  # ハイフンを繋げる
            self.text = re.sub(r'\n *', ' ', self.text)  # 複数行を1行にまとめる
            self.text = re.sub(r' +', ' ', self.text)  # 連続した空白を1つにまとめる

    def __str__(self):
        return 'Paragraph: level: %d, is_code: %s\n%s' % \
            (self.indent, self.is_code, self.text)

    # 目次の判定
    def _find_toc_pattern(self, text):
        return (re.search(r'\.{6}|(?:\. ){6}', text) or
               # 1. Introduction から始まって Authors' Addresses で終わるとき
               (re.search(r'\A\s*1\. +Introduction', text, re.MULTILINE) and
                re.search(r'Author(?:s\'|\'s) Address(?:es)?\s*\Z', text, re.MULTILINE)))

    # 箇条書きなどの判定
    def _find_list_pattern(self, text):
        return re.match(r'(?:[-o*+]|\d{1,2}\.) +[a-zA-Z]', text)

    # 図表・ソースコード・数式の判定
    def _find_code_pattern(self, text):
        if (re.search(r'---|__|~~~|\+\+\+|\*\*\*|\+-\+-\+-\+|=====', text)  # fig
                or re.search(r'\.{4}|(?:\. ){4}', text)  # TOC
                or text.find('+--') >= 0  # directory tree
                or re.search(r'^\/\*|\/\* | \*\/$', text)  # src
                or re.search(r'(?:enum|struct) \{', text)  # tls
                or text.find('::=') >= 0  # syntax
                or re.search(r'": (?:[\[\{\"\']|true,|false,)', text)  # json
                or re.search(r'= +[\[\(\{<*%#&]', text) # src, syntax
                or len(re.compile(r'[;{}]$', re.MULTILINE).findall(text)) >= 2  # src
                or len(re.compile(r'^</', re.MULTILINE).findall(text)) >= 2  # xml
                or re.search(r'[/|\\] +[/|\\]', text)  # figure
                or len(re.compile(r'^\s*\|', re.MULTILINE).findall(text)) >= 3  # table
                or len(re.compile(r'\*\s*$', re.MULTILINE).findall(text)) >= 3  # table
                or len(re.compile(r'^\s*/', re.MULTILINE).findall(text)) >= 3  # syntax
                or len(re.compile(r'^\s*;', re.MULTILINE).findall(text)) >= 3  # syntax
                or len(re.compile(r'^\s*\[', re.MULTILINE).findall(text)) >= 3  # syntax
                or len(re.compile(r'\]\s*$', re.MULTILINE).findall(text)) >= 3  # syntax
                or len(re.compile(r'^\s*:', re.MULTILINE).findall(text)) >= 3  # src
                or len(re.compile(r'^\s*o ', re.MULTILINE).findall(text)) >= 4  # list
                or re.match(r'^E[Mm]ail: ', text)  # Authors' Addresses
                or re.search(r'(?:[0-9A-F]{2} ){8} (?:[0-9A-F]{2} ){7}[0-9A-F]{2}', text)  # hexdump
                or re.search(r'000 {2,}(?:[0-9a-f]{2} ){16} ', text)  # hexdump
                or re.search(r'[0-9a-zA-Z]{32,}$', text)  # hex
                or re.search(r'" [\|/] "', text)  # BNF syntax
                or re.match(r'^\s*[-\w\d]+\s+=\s+[-\w\d /]{1,40}$', text) # syntax
                or re.match(r'^\s*[-\w\d]+\s+=\s+"[-\w\d ]{1,20}"$', text) # syntax
                or re.search(r'^\s*[-\w\d]+\s+=\s+1\*.', text) # syntax
                or len(re.compile(r'^\s*Content-Type:\s+[a-z]+/[a-z]+\s*$', re.MULTILINE).findall(text)) >= 1 # HTML
                or len(re.compile(r'^\s*[SC]: ', re.MULTILINE).findall(text)) >= 2 # server-client
                or len(re.compile(r'^\s*-- ', re.MULTILINE).findall(text)) >= 2 # syntax
                or len(re.compile(r'^\s*[0-9a-f]0: ', re.MULTILINE).findall(text)) >= 3 # hexdump
                or len(re.compile(r'^\s*(?:IN   |OUT  ).', re.MULTILINE).findall(text)) >= 2 # SNMP Dispatcher
                ):
            return True

        # 数式やプログラムを検出する
        # 記号が(3 + 行数-1)文字以上のとき
        # (ただし、丸括弧は直前には空白がないことが条件)
        # (ただし、マイナスは直前に空白があることが条件)
        lines_num = len(text.split("\n"))
        threshold = 3 + (lines_num - 1) * 1
        if (len(re.findall(r'[~+*/=!#<>{}^@:;]|[^ ]\(| -', text)) >= threshold
                and (not re.search(r'[.,:]\)?$', text)) # 文末が「.,:」ではない
                ):
            return True

        return False

    def _find_section_title_pattern(self, text):
        # セクションのタイトルの判定
        # "N." が現れたときはセクションのタイトルとして検出する
        if len(text.split('\n')) >= 2:
            return False
        if text.endswith('.'):
            return False
        if text.endswith(':'):
            return False
        if text.endswith(','):
            return False
        if re.match(r'^Appendix [A-F](?:\. [-a-zA-Z0-9\'\. ]+)?$', text):
            return True
        return re.match(r'^(?:\d{1,2}\.)+(?:\d{1,2})? |^[A-Z]\.(?:\d{1,2}\.)+(?:\d{1,2})? |^[A-Z]\.\d{1,2} ', text)


class Paragraphs:
    # 段落(Paragraph)の集まり
    #
    # Properties:
    # * paragraphs: 段落(Paragraph)の配列

    def __init__(self, text, ignore_header=True):
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

    def __getitem__(self, key):
        assert isinstance(key, int)
        return self.paragraphs[key]

    def __iter__(self):
        return iter(self.paragraphs)

# 単一行の2つの文字列のインデントの差を求める関数
def _get_indent(text):
    return len(text) - len(text.lstrip())

# 複数行の2つの文字列のインデントの差を求める関数
def _get_line_len_diff(text1, text2):
    first_line1 = text1.split('\n')[0]
    first_line2 = text2.split('\n')[0]
    return abs(len(first_line1) - len(first_line2))


# RFC取得先リンクにデータが存在しないときのエラークラス
class RFCNotFound(Exception):
    pass

# 本文中にあるaタグ（RFCへのリンクなど）を削除する
def _cleanhtml(raw_html):
    cleaner = re.compile(rb'<a href="./rfc\d+[^"]*"[^>]*>')
    cleantext = re.sub(cleaner, b'', raw_html)
    return cleantext

# [EntryPoint]
# RFCの取得処理
def fetch_rfc(number, force=False):
    url = 'https://tools.ietf.org/html/rfc%d' % number
    output_dir = 'data/%04d' % (number//1000%10*1000)
    output_file = '%s/rfc%d.json' % (output_dir, number)

    # すでに出力ファイルが存在する場合は終了 (--forceオプションが有効なとき以外)
    if not force and os.path.isfile(output_file):
        return 0

    # 出力先ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)

    # RFCページのDOMツリーの取得
    headers = {'User-agent': '', 'referer': url}
    page = requests.get(url, headers, timeout=(36.2, 180))
    tree = html.fromstring(_cleanhtml(page.content))

    # タイトルの取得
    title = tree.xpath('//title/text()')
    if len(title) == 0:
        raise RFCNotFound

    # ページが存在するか確認
    content_h1 = tree.xpath('//div[@class="content"]/h1/text()')
    if len(content_h1) >= 1 and content_h1[0].startswith('Not found:'):
        raise RFCNotFound

    # タイトルの設定
    # MEMO: RFCのHTMLの構造が変化したときは、ここで対応できないか検討すること！
    content_h1 = tree.xpath('//span[@class="h1"]/text()')
    if len(content_h1) == 0:
        raise "Cannot extract RFC Title!"
    title = "RFC %s - %s" % (number, content_h1[0])

    # DOMツリーから文章を取得
    # MEMO: RFCのHTMLの構造が変化したときは、ここで対応できないか検討すること！
    contents = tree.xpath(
        '//pre[not(contains(@class,"meta-info"))]/text() | '    # 本文（ただし文書冒頭のメタ情報は除く）
        '//pre[not(contains(@class,"meta-info"))]/a/text() | '  # 本文中のリンク
        # セクションのタイトル
        '//pre/span[@class="h1" or @class="h2" or @class="h3" or '
                   '@class="h4" or @class="h5" or @class="h6"]//text() |'
        '//pre/span/a[@class="selflink"]/text() |'  # セクションの番号
        '//a[@class="invisible"]'  # ページの区切り
    )

    # ページ区切りで段落がページをまたぐ場合の処理（RFC8650～はページ区切りが無くなったので関係ない）
    contents_len = len(contents)
    for i, content in enumerate(contents):
        # ページ区切りのとき
        if (isinstance(content, html.HtmlElement) and
                content.get('class') == 'invisible'):

            contents[i-1] = contents[i-1].rstrip() # 前ページの末尾の空白を除去
            contents[i+0] = '' # ページ区切りの除去
            if i + 1 >= contents_len: 
                continue
            contents[i+1] = '' # 余分な改行の除去
            if i + 2 >= contents_len: 
                continue
            contents[i+2] = '' # 余分な空白の除去
            if i + 3 >= contents_len: 
                continue
            if not isinstance(contents[i+3], str): 
                continue
            contents[i+3] = contents[i+3].lstrip('\n') # 次ページの先頭の改行を除去

            # ページをまたぐ文章に対応する処理
            first, last = 0, -1
            prev_last_line = contents[i-1].split('\n')[last]    # 前ページの最後の行
            next_first_line = contents[i+3].split('\n')[first]  # 次ページの最初の行
            indent1 = _get_indent(prev_last_line)
            indent2 = _get_indent(next_first_line)
            # print('newpage:', i)
            # print('  ', indent1, prev_last_line)
            # print('  ', indent2, next_first_line)

            # 以下の条件のとき、段落がページをまたいでいると判断する
            #   1) 前ページの最後の段落の字下げの幅と、次ページの最初の段落の字下げの幅が同じとき
            #   2) 前ページの最後の段落が、文終端の「.」や「;」ではないとき
            if (not prev_last_line.endswith('.') and
                not prev_last_line.endswith(';') and
                    re.match(r'^ *[a-zA-Z0-9(]', next_first_line) and
                    indent1 == indent2):
                # 内容がページをまたぐ場合、BREAKを挿入する
                # BREAK は文章のときは空白に置き換えて、コードのときは改行の置き換える。
                contents[i+3] = BREAK + contents[i+3]
            else:
                # 内容がページをまたがない場合、段落区切り(改行2つ)を挿入する
                contents[i+0] = '\n\n'

    # ページ番号を非表示にする
    contents[-1] = re.sub(r'.*\[Page \d+\]$', '', contents[-1].rstrip()).rstrip()
    # 全ての段落を結合する（段落の区切りは\n\n）
    text = ''.join(contents).strip()

    # 文字列を段落の配列に変換する
    paragraphs = Paragraphs(text)

    # 段落情報をJSONに変換する
    obj = {
        'title': {'text': title},
        'number': number,
        'created_at': str(datetime.now(JST)),
        'updated_by': '',
        'contents': [],
    }
    for paragraph in paragraphs:
        obj['contents'].append({
            'indent': paragraph.indent,
            'text': paragraph.text,
        })
        if paragraph.is_section_title:
            obj['contents'][-1]['section_title'] = True
        if paragraph.is_code:
            obj['contents'][-1]['raw'] = True
        if paragraph.is_toc:
            obj['contents'][-1]['toc'] = True

    # JSONの保存
    json_file = open(output_file, 'w', encoding="utf-8")
    json.dump(obj, json_file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_number', type=int)
    args = parser.parse_args()

    fetch_rfc(args.rfc_number)

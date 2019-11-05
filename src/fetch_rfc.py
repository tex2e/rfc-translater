
import requests
from lxml import html
import re
import textwrap
import json
import os

from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')

class Paragraph:
    def __init__(self, text, is_code=None):
        self.text = textwrap.dedent(text.lstrip('\n').rstrip())
        self.indent = get_line_len_diff(text, self.text)
        self.is_code = is_code
        if not self.is_code:
            self.is_code = (
                not self._find_list_pattern(self.text)
                and self._find_code_pattern(self.text) )
        self.is_section_title = (
            self.indent <= 2 and
            self._find_section_title_pattern(self.text) )
        self.is_toc = self._find_toc_pattern(self.text)

        # 複数に分類された時の優先順位: 目次 > セクション > 図やコード
        if self.is_toc:
            self.is_code = True
            self.is_section_title = False
        elif self.is_code and self.is_section_title:
            self.is_code = False

        if not self.is_code:
            self.text = re.sub(r'([a-zA-Z])-\n *', r'\1-', self.text) # ハイフンを繋げる
            self.text = re.sub(r'\n *', ' ', self.text) # 複数行を1行にまとめる
            self.text = re.sub(r' +', ' ', self.text) # 連続した空白を1つにまとめる

    def __str__(self):
        return 'Paragraph: level: %d, is_code: %s\n%s' % \
            (self.indent, self.is_code, self.text)

    def _find_toc_pattern(self, text):
        return re.search(r'\.{6}|(?:\. ){6}', text)

    def _find_list_pattern(self, text):
        return re.match(r'(?:[-o*+]|\d{1,2}\.) +[a-zA-Z]', text)

    def _find_code_pattern(self, text):
        # "---" や "___" などの特定の文字列が現れたときは図・表・ソースコードとして検出する
        if (re.search(r'---|__|~~~|\+\+\+|\*\*\*|\+-\+-\+-\+|=====', text) # fig
            or re.search(r'\.{4}|(?:\. ){4}', text) # TOC
            or text.find('+--') >= 0 # directory tree
            or text.find('/*') >= 0 # src
            or re.search(r'(?:enum|struct) \{', text) # tls
            or text.find('::=') >= 0 # syntax
            or re.search(r'": (?:[\[\{\"\']|true,|false,)', text) # json
            or re.search(r'= [\[\(\{*%#&]', text) # src
            or len(re.compile(r';$', re.MULTILINE).findall(text)) >= 2 # src
            or len(re.compile(r'^</', re.MULTILINE).findall(text)) >= 2 # xml
            or re.search(r'[/|\\] +[/|\\]', text) # figure
            or re.match(r'^Email: ', text) # Authors' Addresses
            or re.search(r'(?:[0-9A-F]{2} ){8} (?:[0-9A-F]{2} ){7}[0-9A-F]{2}', text) # hexdump
            or re.search(r'000 {2,}(?:[0-9a-f]{2} ){16} ', text) # hexdump
            or re.search(r'[0-9a-zA-Z]{32,}$', text) # hex
            ):
            return True

        # 数式やプログラムを検出する
        # 記号が(3 + 行数-1)文字以上のとき
        # (ただし、丸括弧は直前には空白がないことが条件)
        # (ただし、マイナスは直前に空白があることが条件)
        lines_num = len(text.split("\n"))
        threshold = 3 + (lines_num - 1) * 1
        if (len(re.findall(r'[~+*/=!#<>{})^@:;]|[^ ]\(| -', text)) >= threshold
            and (not re.search(r'[.,:]\)?$', text)) # 文末が「.,:」ではない
            ):
            return True

        return False

    def _find_section_title_pattern(self, text):
        # "N." が現れたときはセクションのタイトルとして検出する
        if len(text.split('\n')) >= 2:
            return False
        if text.endswith('.'): return False
        if text.endswith(':'): return False
        if text.endswith(','): return False
        if re.match(r'^Appendix [A-F]. ', text):
            return True
        return re.match(r'^(?:\d{1,2}\.)+ |^[A-Z]\.(?:\d{1,2}\.)+ ', text)


class Paragraphs:
    def __init__(self, text, has_header=True):
        is_header = has_header
        chunks = re.compile(r'\n\n+').split(text)
        self.paragraphs = []
        for i, chunk in enumerate(chunks):
            is_header = (i == 0 and has_header)
            self.paragraphs.append(Paragraph(chunk, is_code=is_header))

    def __getitem__(self, key):
        return self.paragraphs[key]

    def __iter__(self):
        return iter(self.paragraphs)


def get_indent(text):
    return len(text) - len(text.lstrip())

def get_line_len_diff(text1, text2):
    first_line1 = text1.split('\n')[0]
    first_line2 = text2.split('\n')[0]
    return abs(len(first_line1) - len(first_line2))


class RFCNotFound(Exception):
    pass


def fetch_rfc(number, force=False):

    url = 'https://tools.ietf.org/html/rfc%d' % number
    output_dir = 'data/%04d' % (number//1000%10*1000)
    output_file = '%s/rfc%d.json' % (output_dir, number)

    if not force and os.path.isfile(output_file):
        return 0

    os.makedirs(output_dir, exist_ok=True)

    headers = { 'User-agent': '', 'referer': url }
    page = requests.get(url, headers)
    tree = html.fromstring(page.content)

    title = tree.xpath('//title/text()')
    if len(title) == 0:
        raise RFCNotFound
    title = title[0]

    content_h1 = tree.xpath('//div[@class="content"]/h1/text()')
    if len(content_h1) >= 1 and content_h1[0].startswith('Not found:'):
        raise RFCNotFound

    contents = tree.xpath(
        '//pre/text() | ' # 本文
        '//pre/a/text() | ' # 本文中のリンク
        # セクションのタイトル
        '//pre/span[@class="h1" or @class="h2" or @class="h3" or '
                   '@class="h4" or @class="h5" or @class="h6"]/text() |'
        '//pre/span/a[@class="selflink"]/text() |' # セクションの番号
        '//a[@class="invisible"]' # ページの区切り
    )

    contents_len = len(contents)
    for i, content in enumerate(contents):
        # ページ区切りのとき
        if (isinstance(content, html.HtmlElement) and
                content.get('class') == 'invisible'):

            contents[i-1] = contents[i-1].rstrip() # 前ページの末尾の空白を除去
            contents[i+0] = '' # ページ区切りの除去
            if i + 1 >= contents_len: continue
            contents[i+1] = '' # 余分な改行の除去
            if i + 2 >= contents_len: continue
            contents[i+2] = '' # 余分な空白の除去
            if i + 3 >= contents_len: continue
            if not isinstance(contents[i+3], str): continue
            contents[i+3] = contents[i+3].lstrip('\n') # 次ページの先頭の改行を除去

            # ページをまたぐ文章に対応する処理
            first, last = 0, -1
            prev_last_line = contents[i-1].split('\n')[last]   # 前ページの最後の行
            next_first_line = contents[i+3].split('\n')[first] # 次ページの最初の行
            indent1 = get_indent(prev_last_line)
            indent2 = get_indent(next_first_line)
            # print('newpage:', i)
            # print('  ', indent1, prev_last_line)
            # print('  ', indent2, next_first_line)
            if (not prev_last_line.endswith('.') and
                not prev_last_line.endswith(';') and
                    re.match(r'^ *[a-zA-Z0-9(]', next_first_line) and
                    indent1 == indent2):
                # 内容がページをまたぐ場合、次ページの先頭の空白を1つにまとめる
                contents[i+3] = ' ' + contents[i+3].lstrip()
            else:
                # 内容がページをまたがない場合、ページの境界を明確にするために改行を挿入する
                contents[i+0] = '\n\n'

    contents[-1] = re.sub(r'.*\[Page \d+\]$', '', contents[-1].rstrip()).rstrip()
    text = ''.join(contents).strip()

    paragraphs = Paragraphs(text)

    obj = {
        'title': { 'text': title },
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

    json_file = open(output_file, 'w')
    json.dump(obj, json_file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_number', type=int)
    args = parser.parse_args()

    fetch_rfc(args.rfc_number)

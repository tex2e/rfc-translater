
import requests
from lxml import html
import re
import textwrap
import json
import os

from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')

class Paragraph:
    def __init__(self, text, is_code=False):
        self.text = textwrap.dedent(text.lstrip('\n').rstrip())
        self.indent = get_line_len_diff(text, self.text)
        self.is_code = is_code if is_code else self._find_code_pattern(self.text)
        self.is_section_title = self._find_section_title_pattern(self.text)

        if not self.is_code:
            self.text = re.sub(r'([a-zA-Z])-\n *', r'\1-', self.text) # ハイフンを繋げる
            self.text = re.sub(r'\n *', ' ', self.text) # 複数行を1行にまとめる
            self.text = re.sub(r' +', ' ', self.text) # 連続した空白を1つにまとめる

    def __str__(self):
        return 'Paragraph: level: %d, is_code: %s\n%s' % \
            (self.indent, self.is_code, self.text)

    def _find_code_pattern(self, text):
        # "---" や "___" が現れたときは図・表
        # "........" が現れたときは目次
        # ソースコードなども図に分類する
        return (text.find('---') >= 0 # figure and table
                or text.find('___') >= 0 # figure
                or text.find('~~~') >= 0 # figure
                or text.find('+-+-+-+') >= 0 # figure
                or text.find('.........') >= 0 # TOC
                or text.find('. . . . . . . ') >= 0 # TOC
                or text.find('=========') >= 0 # table
                or text.find('+--') >= 0 # directory tree
                or text.find('/*') >= 0 # src
                or text.find('enum {') >= 0 # tls
                or text.find('struct {') >= 0 # tls
                or text.find('::=') >= 0 # syntax
                or text.find('": [') >= 0 # json
                or text.find('": {') >= 0 # json
                or text.find('": "') >= 0 # json
                or text.find('": \'') >= 0 # json
                or text.find('": true,') >= 0 # json
                or text.find('": false,') >= 0 # json
                or len(re.compile(r';$', re.MULTILINE).findall(text)) >= 2 # src
                )

    def _find_section_title_pattern(self, text):
        # "N." が現れたときはセクションのタイトルとする
        if len(text.split('\n')) >= 2:
            return False
        return re.match(r'^\d+\.', text)


class Paragraphs:
    def __init__(self, text, has_header=True):
        is_header = has_header
        prev_indent = 0
        chunks = re.compile(r'\n\n+').split(text)
        self.paragraphs = []
        for i, chunk in enumerate(chunks):
            # indent = get_indent(chunk)
            indent = get_line_len_diff(chunk, textwrap.dedent(chunk))
            if i >= 1 and indent <= 3:
                is_header = False
            is_large_indent = (indent - prev_indent > 3)

            is_oneline = (len(chunk.split('\n')) == 1)

            if (is_header or (not is_oneline and is_large_indent)):
                flag = True
            else:
                flag = None
            self.paragraphs.append(Paragraph(chunk, is_code=flag))
            prev_indent = indent

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


def fetch_rfc(number):

    url = 'https://tools.ietf.org/html/rfc%d' % number
    output_dir = 'data/%04d/%03d' % (number//1000%10*1000, number//100%10*100)
    output_file = '%s/rfc%d.json' % (output_dir, number)

    if os.path.isfile(output_file):
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
                    re.match(r'^ *[a-z(]', next_first_line) and indent1 == indent2):
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

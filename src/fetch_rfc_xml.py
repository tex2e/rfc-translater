
import re
from pprint import pprint
from lxml import etree
from rfc_utils import RfcUtils
from rfc_const import RfcFile

class Content:
    def __init__(self, text: str, indent=0, section_title=False, raw=False, toc=False) -> None:
        self.text = text
        self.indent = indent
        self.section_title = section_title
        self.raw = raw
        self.toc = toc

    def append_content(self, content):
        self.text += content.text
        return self

contents: list[Content] = []

url = RfcFile.get_url_rfc_xml(9000)
page = RfcUtils.fetch_url(url)
xml = page.content

import textwrap
from io import BytesIO

def get_elem_path(nests) -> str:
    return '/' + '/'.join([str(elem.tag) for elem in nests])

def get_indent(nests) -> int:
    def _convert_to_int(indent_str: str) -> int:
        if indent_str == 'adaptive':
            return 0
        return int(indent_str)
    return sum([_convert_to_int(elem.attrib.get('indent', '0')) for elem in nests])

def start_tag(nests, elem, contents):
    elem_path = get_elem_path(nests)

    if re.match(r'^/rfc/.*?/section/name$', elem_path) and elem.tag == 'name':

        # セクションのタイトル
        text = elem.text
        parent_pn = nests[-2].attrib.get('pn', '')
        pre_text = re.sub(r'section-(?:abstract.*|boilerplate.*|toc.*)?', '', parent_pn)
        if len(pre_text) > 0:
            text = f'{pre_text} {text}'
        contents.append(Content(text, section_title=True))

        # TODO: elem.tail で取りこぼしたテキストも要素に加える

    elif elem.tag in ('link', 'seriesInfo', 'date'):
        pass

    elif elem.tag in ('eref', 'xref'):

        # リンク
        if elem.tag == 'eref':
            text = elem.attrib.get('target')
            contents[-1].append_content(Content(text))
        elif elem.tag == 'xref':
            if elem.text and len(elem.text) > 0:
                # TOC
                text = elem.text
                contents[-1].append_content(Content(text))
            elif elem.attrib.get('target') == elem.attrib.get('derivedContent'):
                # "defined in [QUIC]"
                text = f"[{elem.attrib.get('derivedContent')}]"
                contents[-1].append_content(Content(text))
            else:
                # "shown in Appendix A.1"
                text = f"{elem.attrib.get('derivedContent')}"
                contents[-1].append_content(Content(text))

        # タグ終了後のテキスト (tタグ)
        text = elem.tail
        if text is not None:
            contents[-1].append_content(Content(text))

    elif elem.tag in ('t'):

        # タグ内のテキスト (tタグ)
        indent = get_indent(nests)
        text = elem.text
        if text is None:
            text = ''
        contents.append(Content(text, indent=indent))

    elif elem.tag in ('dt'):

        # 定義 (dl,dt,ddタグ)
        indent = get_indent(nests)
        text = elem.text
        if text is None:
            text = ''
        contents.append(Content(text, indent=indent))

    elif elem.tag in ('table'):
        pass
        # TODO: !!! HTMLテーブルをMarkdownテーブルに変換する処理が必要。表のタイトルも下に追加する

    elif elem.tag in ('figure'):
        pass
        # TODO: !!! raw=Trueでcontentsに追加する。加えて図のタイトルも下に追加する


def end_tag(nests, elem, contents):
    pass

nests = []
contents: list[Content] = []

context = etree.iterparse(BytesIO(xml), events=("start", "end"))
for action, elem in context:
    # print("%s: %s" % (action, elem.tag))
    if action == 'start':
        nests.append(elem)
        start_tag(nests, elem, contents)
    elif action == 'end':
        if nests[-1].tag == elem.tag:
            nests.pop()
        end_tag(nests, elem, contents)


for content in contents:
    print(f'[*]')
    if content.section_title:
        print(f'\n### {content.text}')
    else:
        print(f'indent={content.indent}')
        print(textwrap.indent(content.text, prefix=(" " * content.indent)))


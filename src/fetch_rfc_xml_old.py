
import re
import sys
import textwrap
from io import BytesIO
from pprint import pprint
import lxml.etree
from rfc_utils import RfcUtils
from rfc_const import RfcFile
from rfc_draw_txt import TextWriter, MAX_WIDTH


class Content:
    def __init__(self, text: str, indent=0, section_title=False, raw=False, toc=False, list_item=False) -> None:
        self.text = text
        self.indent = indent
        self.section_title = section_title
        self.raw = raw
        self.toc = toc
        self.list_item = list_item

    def append_content(self, content):
        self.text += content.text
        return self

contents: list[Content] = []

url = RfcFile.get_url_rfc_xml(9000)
page = RfcUtils.fetch_url(url)
xml = page.content

# RfcFile.write_html_file('zzz_fetched.xml', xml.decode('utf-8'))

def get_elem_path(nests) -> str:
    return '/' + '/'.join([str(elem.tag) for elem in nests])

def get_indent(nests) -> int:
    def _convert_to_indent_int(elem) -> int:
        if elem.tag == 'aside':
            return 6
        indent_str = elem.attrib.get('indent', '0')
        if indent_str == 'adaptive':  # RFC9000: <ol indent="adaptive">
            return 0
        return int(indent_str)
    return sum([_convert_to_indent_int(elem) for elem in nests])

def get_ul_nest_count(nests) -> int:
    return sum([1 for elem in nests if elem.tag == 'ul'])

def get_ul_li_symbol(nest_count: int) -> str:
    LIST_SYMBOLS = ('*', '-', 'o', '+')
    return LIST_SYMBOLS[(nest_count - 1) % 4]

def start_tag(nests, elem, contents):
    elem_path = get_elem_path(nests)

    # if elem.attrib.get('pn', '').startswith('section-1.3-'):
    #     print(elem_path, file=sys.stderr)
    #     print(elem, file=sys.stderr)
    #     print(elem.attrib, file=sys.stderr)
    #     print(elem.text, file=sys.stderr)
    #     print(elem.tail, file=sys.stderr)
    #     print(etree.tostring(elem), file=sys.stderr)

    if elem.tag == 'name':
        # タイトル
        if re.match(r'^/rfc/.*?/section/name$', elem_path):
            # セクションのタイトル
            text = elem.text
            parent_pn = nests[-2].attrib.get('pn', '')
            pre_text = re.sub(r'section-(?:abstract.*|boilerplate.*|toc.*)?', '', parent_pn)
            if len(pre_text) > 0:
                text = f'{pre_text}. {text}'
            contents.append(Content(text, section_title=True))

    elif elem.tag in ('link', 'seriesInfo', 'date'):
        pass

    elif elem.tag in ('eref', 'xref'):
        # リンク
        if re.match(r'^/rfc/.*?/table/', elem_path):
            # 表の中のリンクはtableタグの解析で取得するため、ここでは何もしない
            pass
        elif elem.tag == 'eref':
            # erefタグ
            text = elem.attrib.get('target')
            contents[-1].append_content(Content(text))
        elif elem.tag == 'xref':
            # xrefタグ
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

    elif elem.tag in ('t', 'li'):
        # タグ内のテキスト (tタグ)
        text = elem.text
        if text is None:
            text = ''

        indent = get_indent(nests)
        if re.match(r'^/rfc/.*?/dd/t$', elem_path):
            # 定義のときは定義内容にインデントを追加する
            indent += 3

        if re.match(r'^/rfc/.*?/ul/li$', elem_path):
            # 箇条書き
            if re.match(r'^/rfc/.*?/toc', elem_path):
                # TOCの目次の箇条書きを新規追加する
                contents.append(Content(text, indent=indent, toc=True))
            else:
                # 箇条書きを新規追加する
                ul_nest_count = get_ul_nest_count(nests)
                ul_li_symbol = get_ul_li_symbol(ul_nest_count)
                contents.append(Content(text, indent=indent, list_item=ul_li_symbol))
        # elif re.match(r'^/rfc/.*?/ol/li$', elem_path):
        #     # 順序付き箇条書きを追加する
        #     ul_nest_count = get_ul_nest_count(nests)
        #     ul_li_symbol = get_ul_li_symbol(ul_nest_count)
        #     contents.append(Content(text, indent=indent, list_item=ul_li_symbol))

        elif re.match(r'^/rfc/.*?/ul/li/t$', elem_path):
            # 箇条書き直下のtタグの内容を直前の要素（liの想定）追加する
            contents[-1].append_content(Content(text))
        else:
            # 新規追加する
            contents.append(Content(text, indent=indent))

    elif elem.tag in ('dt'):
        # 定義 (dl,dt,ddタグ)
        indent = get_indent(nests)
        text = elem.text
        if text is None:
            text = ''
        contents.append(Content(text, indent=indent))

    elif elem.tag in ('table'):
        # 表
        textwriter = TextWriter()
        table_lines = textwriter.render_table(elem, width=MAX_WIDTH, joiners={})
        # text = '\n'.join([table_line.text for table_line in table_lines])
        # contents.append(Content(text, raw=True))
        # 表の内容
        break_pos = 0
        text = ''
        for i, table_line in enumerate(table_lines):
            # print(i, table_line.mybreak, table_line.text, file=sys.stderr)
            if table_line.mybreak:
                # print(i, file=sys.stderr)
                break_pos = i
                break
            text += table_line.text + '\n'
        indent = RfcUtils.get_indent(text)
        contents.append(Content(text, indent=indent, raw=True))
        # 表のタイトル
        text = ''
        for i, table_line in enumerate(table_lines[break_pos+1:]):
            text += table_line.text + '\n'
        indent = RfcUtils.get_indent(text)
        contents.append(Content(text, indent=indent))

    elif elem.tag in ('figure'):
        # 図
        textwriter = TextWriter()
        figure_lines = textwriter.render_figure(elem, width=MAX_WIDTH, joiners={})
        # text = '\n'.join([figure_line.text for figure_line in figure_lines])
        # contents.append(Content(text, raw=True))
        # 図の内容
        break_pos = 0
        text = ''
        for i, figure_line in enumerate(figure_lines):
            # print(i, figure_line.mybreak, figure_line.text, file=sys.stderr)
            if figure_line.mybreak:
                # print(i, file=sys.stderr)
                break_pos = i
                break
            text += figure_line.text + '\n'
        indent = RfcUtils.get_indent(text)
        contents.append(Content(text, indent=indent, raw=True))
        # 表のタイトル
        text = ''
        for i, figure_line in enumerate(figure_lines[break_pos+1:]):
            text += figure_line.text + '\n'
        indent = RfcUtils.get_indent(text)
        contents.append(Content(text, indent=indent))

    elif len(nests) > 1 and nests[-2].tag == 't':
        # 任意のtタグ内のタグ (例：<bcp14>MUST NOT</bcp14>)
        text = elem.text
        if text:
            contents[-1].append_content(Content(text))

    elif elem.tag == 'abstract':
        # 概要（セクションのタイトル）
        text = 'Abstract'
        contents.append(Content(text, section_title=True))

    # タグ終了後の取りこぼしを追加する
    tail = elem.tail
    if tail and re.match(r'^/rfc/.*?/(?:t|li)/.*?$', elem_path):
        text = tail
        contents[-1].append_content(Content(text))


def end_tag(nests, elem, contents):
    return

nests = []
contents: list[Content] = []

parser = lxml.etree.XMLPullParser(["start", "end"])
parser.feed(xml.decode('utf-8'))
for action, elem in parser.read_events():
    # print("%s: %s" % (action, elem.tag))
    if action == 'start':
        nests.append(elem)
        start_tag(nests, elem, contents)
    elif action == 'end':
        if nests[-1].tag == elem.tag:
            nests.pop()
        end_tag(nests, elem, contents)

# デバッグ
for content in contents:
    if content.section_title:
        print(f'\n### {content.text}')
        print('')
    else:
        print(f'[*] indent={content.indent}, toc={content.toc}, raw={content.raw}')
        content_text = textwrap.dedent(content.text)
        content_text = re.sub(re.compile(r'^\n', re.MULTILINE), '', content_text)
        content_text = re.sub(re.compile(r'\n$', re.MULTILINE), '', content_text)
        if not content.raw:
            content_text = content_text.lstrip()
        if content.list_item:
            content_text = f'{content.list_item}  {content_text}'
        print(textwrap.indent(content_text, prefix=(" " * content.indent)))
        print('')


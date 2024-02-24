
import os
import re
import sys
import textwrap
import datetime
from pprint import pprint
import lxml.etree
import xml2rfc
from xml2rfc.writers.base import default_options
from xml2rfc.writers.text import TextWriter
from rfc_utils import RfcUtils
from rfc_const import RfcFile, RfcJsonElem


class Content:
    def __init__(self, text: str, indent=0, section_title=False, raw=False,
                 toc=False, list_item=False, tag='') -> None:
        self.text = text
        self.indent = indent
        self.section_title = section_title
        self.raw = raw
        self.toc = toc
        self.list_item = list_item
        self.tag = tag

contents: list[Content] = []

dt_now = datetime.datetime.now()
default_options.date = dt_now
default_options.pagination = False

def get_parent(elem):
    return elem.find('..')

def has_ancestor(elem, tagname: str) -> bool:
    current = elem
    while True:
        parent = get_parent(current)
        if parent is None:
            return False
        if parent.tag == tagname:
            return True
        current = parent

def get_tag_path(elem) -> str:
    return '/' + '/'.join([a.tag for a in elem.iterancestors()][::-1]) + '/' + elem.tag

# nameタグ
textwriter_render_name = TextWriter.render_name
def new_textwriter_render_name(self, e, width, **kwargs):
    res = textwriter_render_name(self, e, width, **kwargs)
    parent_e = get_parent(e)
    if parent_e.tag in ('section'):
        # 親要素がセクション(sectionタグ)のとき
        pre_text = ''
        pn = parent_e.get('pn', 'unknown-unknown')
        if parent_e.get('numbered') == 'true':
            _, num, _ = self.split_pn(pn)
            pre_text = num.title() + '.'
            if self.is_appendix(pn) and self.is_top_level_section(num):
                pre_text = 'Appendix %s' % pre_text
        text = f'{pre_text}  {res}'
        contents.append(Content(text, section_title=True, tag=get_tag_path(e)))
    elif parent_e.tag in ('references'):
        # 親要素が参考資料(referencesタグ)のとき
        pn = parent_e.get('pn')
        pre_text = pn.split('-',1)[1].replace('-', ' ').title() +'.'
        text = f'{pre_text}  {res}'
        contents.append(Content(text, section_title=True, tag=get_tag_path(e)))
    return res
TextWriter.render_name = new_textwriter_render_name

# tタグ
textwriter_render_t = TextWriter.render_t
def new_textwriter_render_t(self, e, width, **kwargs):
    res = textwriter_render_t(self, e, width, **kwargs)
    # 箇条書きのとき、最も近い親要素が ul か ol かを判定する
    ancestor_ul_or_ol = None
    for parent in e.iterancestors():
        if parent.tag in ('ul', 'ol'):
            ancestor_ul_or_ol = parent.tag
            break
    if has_ancestor(e, tagname='dd') or has_ancestor(e, tagname='toc'):
        # 親要素が定義(dd)、目次(toc) のときは何もしない
        pass
    elif ancestor_ul_or_ol == 'ul':
        # 親要素が箇条書きリスト(ul > li)のとき
        ancestor_ols = [ a for a in e.iterancestors('ol') ]
        ancestor_uls = [ a for a in e.iterancestors('ul') ]
        ancestor_ul = ancestor_uls[0]
        pre_text = ancestor_ul._initial_text(e, ancestor_ul)
        text = '\n'.join([r.text for r in res])
        text = f'{pre_text}{text}'
        indent = (sum([a._padding for a in ancestor_ols if hasattr(a, '_padding')]) + \
                  sum([a._padding for a in ancestor_uls if hasattr(a, '_padding')]))
        contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    elif ancestor_ul_or_ol == 'ol':
        # 親要素が順序リスト(ol > li)のとき
        ancestor_ols = [ a for a in e.iterancestors('ol') ]
        ancestor_uls = [ a for a in e.iterancestors('ul') ]
        pre_text = e.get('derivedCounter', '1.')
        text = '\n'.join([r.text for r in res])
        text = f'{pre_text} {text}'
        indent = (sum([a._padding for a in ancestor_ols if hasattr(a, '_padding')]) + \
                  sum([a._padding for a in ancestor_uls if hasattr(a, '_padding')]))
        contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    elif e.attrib.get('pn'):
        # 親要素が定義(dd)、目次(toc)ではないとき
        text = '\n'.join([r.text for r in res])
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        indent = j.indent
        if get_parent(e).tag == 'aside':
            indent += 6
        contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    return res
TextWriter.render_t = new_textwriter_render_t

# dtタグ
textwriter_render_dt = TextWriter.render_dt
def new_textwriter_render_dt(self, e, width, **kwargs):
    res = textwriter_render_dt(self, e, width, **kwargs)
    if e.attrib.get('pn'):
        text = '\n'.join([r.text for r in res])
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        indent = j.indent + 3  # インデント追加
        contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    return res
TextWriter.render_dt = new_textwriter_render_dt

# ddタグ
textwriter_render_dd = TextWriter.render_dd
def new_textwriter_render_dd(self, e, width, **kwargs):
    res = textwriter_render_dd(self, e, width, **kwargs)
    if e.attrib.get('pn'):
        text = '\n'.join([r.text for r in res])
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        indent = j.indent + 3  # インデント追加
        contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    return res
TextWriter.render_dd = new_textwriter_render_dd

# figureタグ
textwriter_render_figure = TextWriter.render_figure
def new_textwriter_render_figure(self, e, width, **kwargs):
    res = textwriter_render_figure(self, e, width, **kwargs)
    if e.attrib.get('pn'):
        text = '\n'.join([r.text for r in res])
        if matchobj := re.finditer(re.compile(r'^\s*Figure \d+:', re.MULTILINE), text):
            m = [m for m in matchobj][-1]
            fig = text[0:m.start()]
            figname = text[m.start():]
            # 図
            indent = RfcUtils.get_indent(fig)
            contents.append(Content(fig, indent=indent, raw=True, tag=get_tag_path(e)))
            # 図の表題
            indent = RfcUtils.get_indent(figname)
            contents.append(Content(figname, indent=indent, tag=get_tag_path(e)))
        else:
            indent = RfcUtils.get_indent(text)
            contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_figure = new_textwriter_render_figure

# tableタグ
textwriter_render_table = TextWriter.render_table
def new_textwriter_render_table(self, e, width, **kwargs):
    res = textwriter_render_table(self, e, width, **kwargs)
    if e.attrib.get('pn'):
        text = '\n'.join([r.text for r in res])
        if matchobj := re.finditer(re.compile(r'^\s*Table \d+:', re.MULTILINE), text):
            m = [m for m in matchobj][-1]
            table = text[0:m.start()]
            tablename = text[m.start():]
            # 表
            indent = RfcUtils.get_indent(table)
            contents.append(Content(table, indent=indent, raw=True, tag=get_tag_path(e)))
            # 表の表題
            indent = RfcUtils.get_indent(tablename)
            contents.append(Content(tablename, indent=indent, tag=get_tag_path(e)))
        else:
            indent = RfcUtils.get_indent(text)
            contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_table = new_textwriter_render_table

# tocタグ
textwriter_render_toc = TextWriter.render_toc
def new_textwriter_render_toc(self, e, width, **kwargs):
    res = textwriter_render_toc(self, e, width, **kwargs)
    if len(res) > 0 and re.match(r'Table[\s]of[\s]Contents', res[0].text):
        res = res[1:]  # 最初の行 ("Table of Contents") は削除
        text = '\n'.join([r.text for r in res])
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        indent = j.indent
        contents.append(Content(text, indent=indent, raw=True, toc=True, tag=get_tag_path(e)))
    return res
TextWriter.render_toc = new_textwriter_render_toc

# referenceタグ
textwriter_render_reference = TextWriter.render_reference
def new_textwriter_render_reference(self, e, width, **kwargs):
    res = textwriter_render_reference(self, e, width, **kwargs)
    if e.get('anchor'):
        text = '\n'.join([r.text for r in res])
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        indent = j.indent
        contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_reference = new_textwriter_render_reference

# authorタグ
textwriter_render_author = TextWriter.render_author
def new_textwriter_render_author(self, e, width, **kwargs):
    res = textwriter_render_author(self, e, width, **kwargs)
    if e.get('role'):
        text = '\n'.join([r.text for r in res])
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        indent = j.indent
        contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_author = new_textwriter_render_author




# RFC取得先リンクにデータが存在しないときは、RFCNotFoundエラーを投げること。
# このエラーを投げると、html/rfcXXXX-not-found.html が作成される。
class RFCNotFound(Exception):
    pass


# [EntryPoint]
# RFCの取得処理
def fetch_rfc(rfc_number: int | str, force=False) -> None:

    if type(rfc_number) is int:
        # RFCのとき
        is_draft = False
        url = RfcFile.get_url_rfc_html(rfc_number)
        url_xml = RfcFile.get_url_rfc_xml(rfc_number)
        output_file = RfcFile.get_filepath_data_json(rfc_number)
    elif m := re.match(r'draft-(?P<rfc_draft_id>.+)', rfc_number):
        # Draft版RFCのとき
        is_draft = True
        rfc_draft_id = m['rfc_draft_id']
        url = RfcFile.get_url_rfc_html(rfc_draft_id)
        url_xml = RfcFile.get_url_rfc_xml(rfc_draft_id)
        output_file = RfcFile.get_filepath_data_json(rfc_draft_id)
    else:
        raise RuntimeError(f"fetch_rfc: Unknown format number={rfc_number}")

    # すでに出力ファイルが存在する場合は終了 (--forceオプションが有効なとき以外)
    if not force and os.path.isfile(output_file):
        return

    # RFCページのDOMツリーの取得
    page = RfcUtils.fetch_url(url)
    tree = lxml.html.fromstring(RfcUtils.html_rm_link_tag(page.content))

    # タイトル取得
    title = tree.xpath('//title/text()')
    if len(title) == 0:
        raise RFCNotFound
    title = title[0].strip()

    # タイトルの取得（パターンマッチ）
    if re.match(r'RFC [^ ]+ - .*$', title):  # RFC
        tmp = title
        tmp = re.sub(r' ?\(RFC \d+\)$', '', tmp)
        tmp = re.sub(r' ?\(Internet-Draft, \d+\)$', '', tmp)
        tmp = re.sub(r'^RFC (\d+) -', f'RFC {rfc_number} -', tmp)  # 廃止RFCの場合、最新RFCにリダイレクトされるため
        # title = "RFC %s - %s" % (number, tmp)
        title = tmp
    elif re.match(r'draft-[-a-zA-Z0-9]+\d$', title):  # Draft版
        title = title
    else:
        # タイトルがRFC形式と一致しない場合
        raise Exception("[-] Cannot extract RFC Title!: RFC=%s, title=%s" % (rfc_number, title))

    # RFC (XML) の取得
    global contents
    contents: list[Content] = []
    # url: str = RfcFile.get_url_rfc_xml(9000)
    page = RfcUtils.fetch_url(url_xml)
    xml: bytes = page.content

    # XML解析
    options_for_xmlrfcparser = dict()
    parser = xml2rfc.XmlRfcParser(None, quiet=False, options=default_options, **options_for_xmlrfcparser)
    parser.text = xml
    xmlrfc = parser.parse()
    writer = xml2rfc.TextWriter(xmlrfc, quiet=True)
    rfc_txt = writer.process()


    # デバッグ
    for content in contents:
        if content.section_title:
            print(f'\n### {content.text}')
            print('')
        else:
            print(f'[*] indent={content.indent}, toc={content.toc}, raw={content.raw}, tag={content.tag}')
            content_text = textwrap.dedent(content.text)
            content_text = re.sub(re.compile(r'^\n', re.MULTILINE), '', content_text)
            content_text = re.sub(re.compile(r'\n$', re.MULTILINE), '', content_text)
            if not content.raw:
                content_text = content_text.lstrip()
            if content.list_item:
                content_text = f'{content.list_item}  {content_text}'
            print(textwrap.indent(content_text, prefix=(" " * content.indent)))
            print('')

    paragraphs = contents


    # 段落情報をJSONに変換する
    obj = {
        RfcJsonElem.TITLE: {RfcJsonElem.Title.TEXT: title},
        RfcJsonElem.NUMBER: rfc_number,
        RfcJsonElem.CREATED_AT: str(RfcUtils.get_now()),
        RfcJsonElem.UPDATED_BY: '',
        RfcJsonElem.CONTENTS: [],
    }
    if is_draft:
        obj[RfcJsonElem.IS_DRAFT] = True

    for paragraph in paragraphs:
        obj[RfcJsonElem.CONTENTS].append({
            RfcJsonElem.Contents.INDENT: paragraph.indent,
            RfcJsonElem.Contents.TEXT: paragraph.text,
        })
        if paragraph.is_section_title:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.SECTION_TITLE] = True
        if paragraph.is_code:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.RAW] = True
        if paragraph.is_toc:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.TOC] = True

    # JSONの保存
    RfcFile.write_json_file(output_file, obj)


if __name__ == '__main__':
    fetch_rfc(9000)

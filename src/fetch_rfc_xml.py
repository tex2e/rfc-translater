# ------------------------------------------------------------------------------
# IETFのWebサイトからRFCをXML形式で取得し、文章・図・表・コードの判定をするためのプログラム
# ------------------------------------------------------------------------------

import os
import re
import sys
import textwrap
import datetime
# from pprint import pprint
import lxml.etree
import xml2rfc
from xml2rfc.writers.base import default_options
from xml2rfc.writers.text import TextWriter
from .rfc_utils import RfcUtils
from .rfc_const import RfcFile, RfcJsonElem, RfcXmlElem


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
        self.normalize_text()

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
        # text = textwrap.shorten(self.text, width=30, placeholder='...')
        text = self.text
        return f'<Content indent="{self.indent}" title="{self.title}" sectitle="{self.section_title}" raw="{self.raw}" toc="{self.toc}" text="{text}">'

    def normalize_text(self):
        # 文章のときの処理
        if not self.raw:
            self.text = re.sub(r'([a-zA-Z])-\n *', r'\1-', self.text)  # ハイフンを繋げる
            self.text = re.sub(r'\n *', ' ', self.text)  # 複数行を1行にまとめる
            self.text = re.sub(r' +', ' ', self.text)  # 連続した空白を1つにまとめる
        # 以下xml2rfc対応処理
        self.text = re.sub(r'\xa0', ' ', self.text)  # "Section 1" の空白を正規化する
        self.text = re.sub(r'‑', '-', self.text)  # "[QUIC‑RECOVERY]" のハイフンを正規化する
        # # Line Separator (\x2028) と Paragraph Separator (\x2029) の削除
        # self.text = re.sub(r'\x2028|\x2029', '', self.text)


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


# xml2rfc
# https://github.com/ietf-tools/xml2rfc/blob/main/xml2rfc/writers/text.py

# xml2rfcのデフォルト値設定
dt_now = datetime.datetime.now()
default_options.date = dt_now
default_options.pagination = False
default_options.rfc = True

# nameタグ
#   section > name
#   references > name
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
        text = f'{pre_text} {res}'.strip()
        self._contents.append(Content(text, section_title=True, tag=get_tag_path(e)))
    elif parent_e.tag in ('references'):
        # 親要素が参考資料(referencesタグ)のとき
        pn = parent_e.get('pn')
        pre_text = pn.split('-',1)[1].replace('-', ' ').title() +'.'
        text = f'{pre_text}  {res}'
        self._contents.append(Content(text, section_title=True, tag=get_tag_path(e)))
    return res
TextWriter.render_name = new_textwriter_render_name

# tタグ
#   ul > li > t
#   ol > li > t
#   aside > t
textwriter_render_t = TextWriter.render_t
def new_textwriter_render_t(self, e, width, **kwargs):
    res = textwriter_render_t(self, e, width, **kwargs)
    # 箇条書きのとき、最も近い親要素が ul か ol かを判定する
    ancestor_tag = None
    for parent in e.iterancestors():
        if parent.tag in ('ul', 'ol'):
            ancestor_tag = parent.tag
            break
        elif parent.tag in ('dl'):
            ancestor_tag = parent.tag
            break
    if has_ancestor(e, tagname='toc'):
        # 親要素が目次(toc) のときは何もしない
        pass
    elif has_ancestor(e, tagname='table'):
        # 親要素が表(table) のときは何もしない
        pass
    elif ancestor_tag == 'ul':
        # 親要素が箇条書きリスト(ul > li)のとき
        ancestor_ols = [ a for a in e.iterancestors('ol') ]
        ancestor_uls = [ a for a in e.iterancestors('ul') ]
        ancestor_ul = ancestor_uls[0]
        pre_text = ancestor_ul._initial_text(e, ancestor_ul)
        text = '\n'.join([r.text for r in res])
        text = f'{pre_text}{text}'
        indent = (sum([a._padding * 2 for a in ancestor_ols if hasattr(a, '_padding')]) + \
                  sum([a._padding * 2 for a in ancestor_uls if hasattr(a, '_padding')]))
        self._contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    elif ancestor_tag == 'ol':
        # 親要素が順序リスト(ol > li)のとき
        ancestor_ols = [ a for a in e.iterancestors('ol') ]
        ancestor_uls = [ a for a in e.iterancestors('ul') ]
        # 自分自身がliのとき
        pre_text = e.get('derivedCounter', None)
        if not pre_text:
            # 自分自身がtで親がliのとき
            ancestor_lis = [ a for a in e.iterancestors('li') ]
            if len(ancestor_lis) > 0:
                pre_text = ancestor_lis[0].get('derivedCounter', '1.')
            else:
                pre_text = '1.'
        text = '\n'.join([r.text for r in res])
        text = f'{pre_text} {text}'
        indent = (sum([a._padding * 2 for a in ancestor_ols if hasattr(a, '_padding')]) + \
                  sum([a._padding * 2 for a in ancestor_uls if hasattr(a, '_padding')]))
        self._contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    elif ancestor_tag == 'dl':
        # 親要素が定義(dl)のとき
        text = '\n'.join([r.text for r in res]).rstrip('\n').lstrip()
        ancestors = [ a for a in e.iterancestors() if a.tag in ('ul', 'ol', 'dl') ]
        indent = len(ancestors) * 3 + 9
        self._contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    elif e.attrib.get('pn'):
        # tタグ
        text = '\n'.join([r.text for r in res])
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        indent = j.indent
        if get_parent(e).tag == 'aside':
            # 引用のときはインデント追加
            indent += 12
        self._contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    return res
TextWriter.render_t = new_textwriter_render_t

# dtタグ
#   dl > dt
textwriter_render_dt = TextWriter.render_dt
def new_textwriter_render_dt(self, e, width, **kwargs):
    res = textwriter_render_dt(self, e, width, **kwargs)
    if e.attrib.get('pn'):
        text = '\n'.join([r.text for r in res]).rstrip('\n')
        ancestors = [ a for a in e.iterancestors() if a.tag in ('ol', 'ul', 'dl') ]
        ancestors_count = len(ancestors)
        indent = ancestors_count * 3
        self._contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
    return res
TextWriter.render_dt = new_textwriter_render_dt

# artworkタグ
#   section > artwork
textwriter_render_artwork = TextWriter.render_artwork
def new_textwriter_render_artwork(self, e, width, **kwargs):
    res = textwriter_render_artwork(self, e, width, **kwargs)
    if not has_ancestor(e, tagname='figure'):
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        base_indent = j.indent
        artwork = '\n'.join([r.text for r in res]).rstrip('\n')
        artwork = artwork.strip('\n')
        indent = base_indent + RfcUtils.get_indent_multiline(artwork)
        text = textwrap.dedent(artwork)
        self._contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_artwork = new_textwriter_render_artwork

# figureタグ
#   section > figure > artwork
textwriter_render_figure = TextWriter.render_figure
def new_textwriter_render_figure(self, e, width, **kwargs):
    res = textwriter_render_figure(self, e, width, **kwargs)
    if e.attrib.get('pn'):
        text = '\n'.join([r.text for r in res]).rstrip('\n')
        matchobj = re.finditer(re.compile(r'^\s*Figure \d+:', re.MULTILINE), text)
        mlist = [x for x in matchobj]
        if len(mlist) > 0:
            m = mlist[-1]
            fig = text[0:m.start()]
            figname = text[m.start():]
            # 基本のインデント
            joiners = kwargs['joiners']
            j = joiners[e.tag] if e.tag in joiners else joiners[None]
            base_indent = j.indent
            # 図
            fig = fig.strip('\n')
            indent = base_indent + RfcUtils.get_indent_multiline(fig)
            text = textwrap.dedent(fig)
            self._contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
            # 図の表題
            figname = figname.strip('\n')
            indent = base_indent + RfcUtils.get_indent_multiline(figname)
            text = textwrap.dedent(figname)
            self._contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
        else:
            indent = RfcUtils.get_indent_multiline(text)
            self._contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_figure = new_textwriter_render_figure

# tableタグ
#   table > tr > td
textwriter_render_table = TextWriter.render_table
def new_textwriter_render_table(self, e, width, **kwargs):
    res = textwriter_render_table(self, e, width, **kwargs)
    if e.attrib.get('pn'):
        text = '\n'.join([r.text for r in res])
        matchobj = re.finditer(re.compile(r'^\s*Table \d+:', re.MULTILINE), text)
        mlist = [x for x in matchobj]
        if len(mlist) > 0:
            m = mlist[-1]
            table = text[0:m.start()]
            tablename = text[m.start():]
            # 表
            table = table.strip('\n')
            indent = RfcUtils.get_indent_multiline(table) + 3  # インデント追加
            text = textwrap.dedent(table)
            self._contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
            # 表の表題
            tablename = tablename.strip('\n')
            indent = RfcUtils.get_indent_multiline(tablename) + 3  # インデント追加
            text = textwrap.dedent(tablename)
            self._contents.append(Content(text, indent=indent, tag=get_tag_path(e)))
        else:
            indent = RfcUtils.get_indent_multiline(text)
            self._contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_table = new_textwriter_render_table

# first_page_top (frontタグ)  -- RFCのヘッダー部分
#   rfc > front
textwriter_render_first_page_top = TextWriter.render_first_page_top
def new_textwriter_render_first_page_top(self, e, width, **kwargs):
    res = textwriter_render_first_page_top(self, e, width, **kwargs)
    text = res
    matchobj = re.finditer(re.compile(r'\n\n', re.MULTILINE), text)
    mlist = [x for x in matchobj]
    if len(mlist) > 0:
        m = mlist[-1]
        front = text[0:m.start()]
        fronttitle = text[m.start():]
        # ヘッダー
        indent = RfcUtils.get_indent(front)
        self._contents.append(Content(front, indent=indent, raw=True, tag=get_tag_path(e)))
        # タイトル
        indent = RfcUtils.get_indent(fronttitle.lstrip('\n'))
        fronttitle = textwrap.dedent(fronttitle.lstrip('\n'))
        self._contents.append(Content(fronttitle, indent=indent, title=True, section_title=True, tag=get_tag_path(e)))
    return res
TextWriter.render_first_page_top = new_textwriter_render_first_page_top

# abstractタグ
#   rfc > front > abstract
textwriter_render_abstract = TextWriter.render_abstract
def new_textwriter_render_abstract(self, e, width, **kwargs):
    text = 'Abstract'
    self._contents.append(Content(text, indent=0, section_title=True, tag=get_tag_path(e)))
    res = textwriter_render_abstract(self, e, width, **kwargs)
    return res
TextWriter.render_abstract = new_textwriter_render_abstract

# tocタグ
#   rfc > front > toc
textwriter_render_toc = TextWriter.render_toc
def new_textwriter_render_toc(self, e, width, **kwargs):
    res = textwriter_render_toc(self, e, width, **kwargs)
    if len(res) > 0 and re.match(r'Table[\s]of[\s]Contents', res[0].text):
        res = res[1:]  # 最初の行 ("Table of Contents") は削除
        toc = '\n'.join([r.text for r in res]).rstrip('\n')
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        base_indent = j.indent
        toc = toc.strip('\n')
        indent = base_indent + RfcUtils.get_indent_multiline(toc)
        text = textwrap.dedent(toc)
        self._contents.append(Content(text, indent=indent, raw=True, toc=True, tag=get_tag_path(e)))
    return res
TextWriter.render_toc = new_textwriter_render_toc

# referencegroupタグ
#   rfc > back > references > referencegroup > reference
textwriter_render_referencegroup = TextWriter.render_referencegroup
def new_textwriter_render_referencegroup(self, e, width, **kwargs):
    res = textwriter_render_referencegroup(self, e, width, **kwargs)
    if e.get('anchor'):
        text = '\n'.join([r.text for r in res]).rstrip('\n')
        indent = 3
        self._contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_referencegroup = new_textwriter_render_referencegroup

# referenceタグ
#   rfc > back > references > reference
textwriter_render_reference = TextWriter.render_reference
def new_textwriter_render_reference(self, e, width, **kwargs):
    res = textwriter_render_reference(self, e, width, **kwargs)
    if e.get('anchor') and not has_ancestor(e, tagname='referencegroup'):
        text = '\n'.join([r.text for r in res]).rstrip('\n')
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        indent = j.indent
        self._contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_reference = new_textwriter_render_reference

# authorタグ
#   section > author
textwriter_render_author = TextWriter.render_author
def new_textwriter_render_author(self, e, width, **kwargs):
    res = textwriter_render_author(self, e, width, **kwargs)
    if get_parent(e).tag == 'section':
        text = '\n'.join([r.text for r in res]).rstrip('\n')
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        indent = j.indent
        self._contents.append(Content(text, indent=indent, raw=True, tag=get_tag_path(e)))
    return res
TextWriter.render_author = new_textwriter_render_author


# xml2rfcのTextWriterのインスタンスを作成する
def generate_text_writer(xml: bytes):
    options_for_xmlrfcparser = dict()
    parser = xml2rfc.XmlRfcParser(None, quiet=True, options=default_options, **options_for_xmlrfcparser)
    parser.text = xml
    xmlrfc = parser.parse()
    text_writer = xml2rfc.TextWriter(xmlrfc, quiet=True)
    # 解析後はグローバル変数contentsに段落ごとの情報が格納される
    setattr(text_writer, '_contents', [])
    return text_writer


# [EntryPoint]
# RFCの取得処理 (XML版)
def fetch_rfc_xml(rfc_number: int | str, force=False) -> None:
    print("[*] fetch_rfc_xml(%s)" % rfc_number)

    if type(rfc_number) is int:
        # RFCのとき
        is_draft = False
        url_xml = RfcFile.get_url_rfc_xml(rfc_number)
        output_file = RfcFile.get_filepath_data_json(rfc_number)
    elif m := re.match(r'draft-(?P<rfc_draft_id>.+)', rfc_number):
        # Draft版RFCのとき
        is_draft = True
        rfc_draft_id = m['rfc_draft_id']
        url_xml = RfcFile.get_url_rfc_xml(rfc_draft_id)
        output_file = RfcFile.get_filepath_data_json(rfc_draft_id)
    else:
        raise RuntimeError(f"fetch_rfc: Unknown format number={rfc_number}")

    # すでに出力ファイルが存在する場合は終了 (--forceオプションが有効なとき以外)
    if not force and os.path.isfile(output_file):
        return

    # RFC (XML) の取得
    page = RfcUtils.fetch_url(url_xml)
    xml: bytes = page.content

    # RFCタイトル取得
    root = lxml.etree.fromstring(xml)
    titles = root.xpath(f'/{RfcXmlElem.RFC}/{RfcXmlElem.FRONT}/{RfcXmlElem.TITLE}/text()')
    if len(titles) > 0:
        title = f"RFC {rfc_number} - {titles[0]}"
    else:
        raise Exception("[-] Cannot extract RFC Title!: RFC=%s" % (rfc_number))

    # XML解析
    text_writer = generate_text_writer(xml)
    text_writer.process()

    # デバッグ
    debug = False
    if debug:
        for content in text_writer._contents:
            print(f'[*] indent={content.indent}, section_title={content.section_title}, toc={content.toc}, raw={content.raw}, tag={content.tag}')
            if content.section_title:
                print('')
                print(f'### {content.text}')
                print('')
            else:
                content_text = textwrap.dedent(content.text)
                content_text = re.sub(re.compile(r'^\n', re.MULTILINE), '', content_text)
                content_text = re.sub(re.compile(r'\n$', re.MULTILINE), '', content_text)
                if not content.raw:
                    content_text = content_text.lstrip()
                print(textwrap.indent(content_text, prefix=(" " * content.indent)))
                print('')

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

    for content in text_writer._contents:
        if re.match(r'^\s*$', content.text):
            continue

        obj[RfcJsonElem.CONTENTS].append({
            RfcJsonElem.Contents.INDENT: content.indent,
            RfcJsonElem.Contents.TEXT: content.text,
        })
        if content.title:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.TITLE] = True
        if content.section_title:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.SECTION_TITLE] = True
        if content.raw:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.RAW] = True
        if content.toc:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.TOC] = True

    # JSONの保存
    RfcFile.write_json_file(output_file, obj)


if __name__ == '__main__':
    fetch_rfc_xml(9000)

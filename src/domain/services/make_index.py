# ------------------------------------------------------------------------------
# トップページを作成するためのプログラム
# ------------------------------------------------------------------------------

import os
import re
import glob
from pprint import pprint
from ..models.rfc.rfc_const import RfcFile
from mako.lookup import TemplateLookup

def make_index() -> None:
    """トップページ作成"""
    print(f'[*] make_index()')
    files = []
    for filepath in glob.glob(RfcFile.GLOB_HTML_FILE):
        html = RfcFile.read_html_file(filepath)
        m = re.search(r'<title>([^<]*)</title>', html)
        if not m:
            print("[-] not found title: %s" % filepath)
            continue
        title = m[1].replace('日本語訳', '').strip()
        rfcfile = os.path.basename(filepath)
        m = re.match(r'rfc(\d+).html', rfcfile)
        if m:
            filenum = int(m[1])
            if filenum < 2220:  # RFC 2220 以降を対象とする
                continue
            files.append((filenum, rfcfile, title))

    # RFC番号降順でソート
    files.sort(reverse=True)

    mylookup = TemplateLookup(directories=["./"], input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template(RfcFile.TEMPLATE_HTML_INDEX)
    output = mytemplate.render_unicode(ctx={'files': files})

    # HTMLファイル出力
    RfcFile.write_html_file(RfcFile.OUTPUT_HTML_INDEX_FILE, output)


def make_index_draft() -> None:
    """Draft版のトップページ作成"""
    print(f'[*] make_index_draft()')
    is_draft = True
    files = []
    for filepath in glob.glob(RfcFile.GLOB_HTML_DRAFT_FILE):
        html = RfcFile.read_html_file(filepath)
        m = re.search(r'<title>([^<]*)</title>', html)
        if not m:
            print("[-] not found title: %s" % filepath)
            continue
        title = m[1].replace('日本語訳', '').strip()

        rfcfile = os.path.basename(filepath)
        m = re.match(r'draft-[^-]+-(?P<draftname>.*).html', rfcfile)
        if m:
            filenum = m['draftname']
            files.append((filenum, rfcfile, title))

    # RFCドラフト名でソート
    files.sort()

    mylookup = TemplateLookup(directories=["./"], input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template(RfcFile.TEMPLATE_HTML_INDEX)
    output = mytemplate.render_unicode(ctx={'files': files}, is_draft=is_draft)

    # HTMLファイル出力
    RfcFile.write_html_file(RfcFile.OUTPUT_HTML_DRAFT_INDEX_FILE, output)

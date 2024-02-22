# ------------------------------------------------------------------------------
# トップページを作成するためのプログラム
# ------------------------------------------------------------------------------

import os
import re
import glob
from mako.lookup import TemplateLookup
from .rfc_const import RfcFile

# トップページ作成
def make_index() -> None:
    output_file = RfcFile.OUTPUT_HTML_INDEX_FILE

    files = []
    for filename in glob.glob('html/rfc*.html'):
        html = RfcFile.read_html_file(filename)
        m = re.search(r'<title>([^<]*)</title>', html)
        if not m:
            print("[-] not found title: %s" % filename)
            continue
        title = m[1].replace('日本語訳', '').strip()
        rfcfile = re.sub(r'^html[/\\]', '', filename)
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
    RfcFile.write_html_file(output_file, output)


# Draft版のトップページ作成
def make_index_draft() -> None:
    output_file = RfcFile.OUTPUT_HTML_DRAFT_INDEX_FILE
    is_draft = True

    files = []
    for filename in glob.glob('html/draft/draft-*.html'):
        html = RfcFile.read_html_file(filename)
        m = re.search(r'<title>([^<]*)</title>', html)
        if not m:
            print("[-] not found title: %s" % filename)
            continue
        title = m[1].replace('日本語訳', '').strip()

        rfcfile = re.sub(r'^html[/\\]draft[/\\]', '', filename)
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
    RfcFile.write_html_file(output_file, output)


if __name__ == '__main__':
    make_index()

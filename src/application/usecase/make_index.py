# ------------------------------------------------------------------------------
# トップページを作成するためのプログラム
# ------------------------------------------------------------------------------

import os
from pprint import pprint
from mako.lookup import TemplateLookup
from ...domain.services.rfcfile import RfcFile
from ...infrastructure.repository.rfchtmlrepository import IRfcHtmlRepository
from ...infrastructure.repository.indexhtmlrepository import IIndexHtmlRepository
from ...infrastructure.repository.indexdrafthtmlrepository import IIndexDraftHtmlRepository


# 一覧に表示するRFCステータスの略称（html/index.js と master.css でも同じ略称を使う）
RFC_STATUS_CODES = {
    'Internet Standard': 'IS',
    'Draft Standard': 'DS',
    'Proposed Standard': 'PS',
    'Best Current Practice': 'BCP',
    'Informational': 'INF',
    'Experimental': 'EXP',
    'Historic': 'HIS',
}


def make_index(index_html_repo: IIndexHtmlRepository,
               rfc_html_repo: IRfcHtmlRepository) -> None:
    """トップページ作成"""

    assert isinstance(index_html_repo, IIndexHtmlRepository)
    assert isinstance(rfc_html_repo, IRfcHtmlRepository)

    print(f'[*] make_index()')

    files = rfc_html_repo.findall()

    # 一覧でステータスの表示・絞り込みと、廃止されたRFCの区別をするための情報
    statuses = {}
    if os.path.isfile(RfcFile.OUTPUT_HTML_RFC_LIST_JSON_FILE):
        statuses = RfcFile.read_json_file(RfcFile.OUTPUT_HTML_RFC_LIST_JSON_FILE)

    mylookup = TemplateLookup(directories=["./"], input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template(RfcFile.TEMPLATE_HTML_INDEX)
    output = mytemplate.render_unicode(ctx={'files': files}, statuses=statuses,
                                       status_codes=RFC_STATUS_CODES)

    # HTMLファイル出力
    index_html_repo.save(output)


def make_index_draft(index_draft_html_repo: IIndexDraftHtmlRepository,
                     rfc_html_repo: IRfcHtmlRepository) -> None:
    """Draft版のトップページ作成"""

    assert isinstance(index_draft_html_repo, IIndexDraftHtmlRepository)
    assert isinstance(rfc_html_repo, IRfcHtmlRepository)

    print(f'[*] make_index_draft()')

    files = rfc_html_repo.findalldraft()

    mylookup = TemplateLookup(directories=["./"], input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template(RfcFile.TEMPLATE_HTML_INDEX)
    output = mytemplate.render_unicode(ctx={'files': files}, is_draft=True,
                                       statuses={}, status_codes=RFC_STATUS_CODES)

    # HTMLファイル出力
    index_draft_html_repo.save(output)

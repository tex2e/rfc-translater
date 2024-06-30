# ------------------------------------------------------------------------------
# トップページを作成するためのプログラム
# ------------------------------------------------------------------------------

from pprint import pprint
from mako.lookup import TemplateLookup
from ..models.rfc import RfcFile
from ..repository.irfchtmlrepository import IRfcHtmlRepository
from ..repository.iindexhtmlrepository import IIndexHtmlRepository
from ..repository.iindexdrafthtmlrepository import IIndexDraftHtmlRepository


def make_index(index_html_repo: IIndexHtmlRepository,
               rfc_html_repo: IRfcHtmlRepository) -> None:
    """トップページ作成"""

    assert isinstance(index_html_repo, IIndexHtmlRepository)
    assert isinstance(rfc_html_repo, IRfcHtmlRepository)

    print(f'[*] make_index()')

    files = rfc_html_repo.findall()

    mylookup = TemplateLookup(directories=["./"], input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template(RfcFile.TEMPLATE_HTML_INDEX)
    output = mytemplate.render_unicode(ctx={'files': files})

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
    output = mytemplate.render_unicode(ctx={'files': files}, is_draft=True)

    # HTMLファイル出力
    index_draft_html_repo.save(output)

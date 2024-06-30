# ------------------------------------------------------------------------------
# IETFのWebサイトからRFC一覧を取得するプログラム
# ------------------------------------------------------------------------------

import re
from pprint import pprint
from lxml import etree  # pip install lxml
from ...domain.services.rfcutils import RfcUtils
from ...domain.valueobject.rfc import RfcIndexXmlElem
from ...infrastructure.repository.rfchtmlrepository import IRfcHtmlRepository
from ...infrastructure.apiclient.rfcindexapiclient import IRfcIndexApiClient


def fetch_remote_index(rfc_index_api_client: IRfcIndexApiClient) -> list[int]:
    """発行されているRFCの番号の一覧をページから取得する"""

    assert isinstance(rfc_index_api_client, IRfcIndexApiClient)

    page = rfc_index_api_client.fetch_index_xml()
    page_content = RfcUtils.remove_namespace_from_xml(page.content)
    tree = etree.XML(page_content)

    rfc_numbers = []
    for item in tree.xpath(f'/{RfcIndexXmlElem.RFC_INDEX}/{RfcIndexXmlElem.RFC_ENTRY}'):
        subtree = etree.XML(etree.tostring(item))

        rfc_ids = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_ids) == 0:
            continue
        rfc_id = rfc_ids[0]

        if m := re.match(r'^RFC(\d+)$', rfc_id):
            rfc_number = m.group(1)
            rfc_numbers.append(int(rfc_number))

    return rfc_numbers

def fetch_local_index(rfc_html_repo: IRfcHtmlRepository) -> list[int]:
    """作成したRFCに対応するHTMLの番号の一覧をローカルから取得する"""

    assert isinstance(rfc_html_repo, IRfcHtmlRepository)

    files = rfc_html_repo.findall()
    rfc_numbers = []
    for file in files:
        rfc_numbers.append(int(file.filenum))

    return rfc_numbers

def diff_remote_and_local_index(rfc_index_api_client: IRfcIndexApiClient,
                                rfc_html_repo: IRfcHtmlRepository) -> list[int]:
    """RFC IndexとローカルのhtmlディレクトリのRFCの差分を作成する。返り値はRFC番号の一覧"""

    assert isinstance(rfc_index_api_client, IRfcIndexApiClient)
    assert isinstance(rfc_html_repo, IRfcHtmlRepository)

    remote_index = fetch_remote_index(rfc_index_api_client)
    local_index = fetch_local_index(rfc_html_repo)
    diff_index = set(remote_index) - set(local_index)
    return diff_index

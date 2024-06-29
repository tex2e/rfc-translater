# ------------------------------------------------------------------------------
# IETFのWebサイトからRFC一覧を取得するプログラム
# ------------------------------------------------------------------------------

import os
import re
import glob
from pprint import pprint
from lxml import etree
from .rfc_utils import RfcUtils
from ..models.rfc import RfcIndexXmlElem, RfcFile

def fetch_remote_index() -> list[int]:
    """発行されているRFCの番号の一覧をページから取得する"""
    page = RfcUtils.fetch_url(RfcFile.get_url_rfc_index_xml())
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

def fetch_local_index() -> list[int]:
    """作成したRFCに対応するHTMLの番号の一覧をローカルから取得する"""
    local_filepath = os.path.join(RfcFile.OUTPUT_HTML_DIR, 'rfc*.html')
    rfc_numbers = []
    for filepath in glob.glob(local_filepath):
        filename = re.sub(rf'^{RfcFile.OUTPUT_HTML_DIR}[/\\]', '', filepath)
        if m := re.match(r'^rfc(\d+)', filename):
            rfc_numbers.append(int(m[1]))

    return rfc_numbers

def diff_remote_and_local_index() -> list[int]:
    """RFC Indexとローカルのhtml/のRFCの差分を作成する。返り値はRFC番号の一覧"""
    remote_index = fetch_remote_index()
    local_index  = fetch_local_index()
    diff_index = set(remote_index) - set(local_index)
    return diff_index

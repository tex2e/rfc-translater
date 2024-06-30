# ------------------------------------------------------------------------------
# IETFのWebサイトからRFCステータスとWGの一覧を取得するプログラム
# ------------------------------------------------------------------------------

import re
from pprint import pprint
from lxml import etree  # pip install lxml
from ...domain.services.rfcutils import RfcUtils
from ...domain.valueobject.rfc import RfcIndexXmlElem, RfcIndexJsonElem
from ...infrastructure.repository.rfcstatusjsonrepository import IRfcStatusRepository
from ...infrastructure.apiclient.rfcindexapiclient import IRfcIndexApiClient


def fetch_status(rfc_status_repo: IRfcStatusRepository,
                 rfc_api: IRfcIndexApiClient) -> None:
    """RFC IndexのXML版を取得してRFCリストを作成する"""

    assert isinstance(rfc_status_repo, IRfcStatusRepository)
    assert isinstance(rfc_api, IRfcIndexApiClient)

    print(f'[*] fetch_status()')

    page = rfc_api.fetch_index_xml()
    page_content = RfcUtils.remove_namespace_from_xml(page.content)
    tree = etree.XML(page_content)

    obj = {}

    for item in tree.xpath(f'/{RfcIndexXmlElem.RFC_INDEX}/{RfcIndexXmlElem.RFC_ENTRY}'):
        subtree = etree.XML(etree.tostring(item))

        rfc_ids = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_ids) == 0:
            continue
        rfc_id = rfc_ids[0]

        m = re.match(r'^RFC([0-9]+)$', rfc_id)
        if not m:
            continue
        rfc_number_str = m.group(1)

        obj[rfc_number_str] = {}

        # obsoletes
        rfc_obsoletes = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.OBSOLETES}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_obsoletes) > 0:
            rfc_obsoletes = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_obsoletes]
            obj[rfc_number_str][RfcIndexJsonElem.OBSOLETES] = rfc_obsoletes

        # obsoleted-by
        rfc_obsoleted_by = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.OBSOLETED_BY}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_obsoleted_by) > 0:
            rfc_obsoleted_by = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_obsoleted_by]
            obj[rfc_number_str][RfcIndexJsonElem.OBSOLETED_BY] = rfc_obsoleted_by

        # updates
        rfc_updates = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.UPDATES}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_updates) > 0:
            rfc_updates = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_updates]
            obj[rfc_number_str][RfcIndexJsonElem.UPDATES] = rfc_updates

        # updated-by
        rfc_updated_by = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.UPDATED_BY}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_updated_by) > 0:
            rfc_updated_by = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_updated_by]
            obj[rfc_number_str][RfcIndexJsonElem.UPDATED_BY] = rfc_updated_by

        # current-status
        rfc_current_status = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.CURRENT_STATUS}/text()')
        if len(rfc_current_status) > 0:
            rfc_current_status = RfcUtils.replace_upper_to_camel(rfc_current_status[0])
            obj[rfc_number_str][RfcIndexJsonElem.CURRENT_STATUS] = rfc_current_status

        # wg (working-group)
        rfc_wgs = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.WG_ACRONYM}/text()')
        if len(rfc_wgs) > 0:
            rfc_wg = rfc_wgs[0]
            if re.match(r'^[^ ]+$', rfc_wg):
                obj[rfc_number_str][RfcIndexJsonElem.WG] = str(rfc_wg)

    # Save file
    rfc_status_repo.save(obj)

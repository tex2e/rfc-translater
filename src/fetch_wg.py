# ------------------------------------------------------------------------------
# IETFのWebサイトからWGの一覧を取得するプログラム
# ------------------------------------------------------------------------------

import os
import re
import json
# from pprint import pprint
from lxml import etree
from rfc_utils import RfcUtils
from rfc_const import RfcXmlElem, RfcJsonElem, RfcFolder

def write_rfc_wg_list():
    # WorkingGroupのRFCの一覧の保存先
    OUTPUT_PATH = os.path.join(RfcFolder.OUTPUT_HTML_DIR, "group-rfcs.json")

    page = RfcUtils.fetch_url("https://www.rfc-editor.org/rfc-index.xml")
    page_content = RfcUtils.remove_namespace_from_xml(page.content)
    tree = etree.XML(page_content)

    obj = {}

    for item in tree.xpath(f'/{RfcXmlElem.RFC_INDEX}/{RfcXmlElem.RFC_ENTRY}'):
        subtree = etree.XML(etree.tostring(item))

        rfc_ids = subtree.xpath(f'/{RfcXmlElem.RFC_ENTRY}/{RfcXmlElem.DOC_ID}/text()')
        if len(rfc_ids) == 0:
            continue
        rfc_id = rfc_ids[0]

        rfc_wgs = subtree.xpath(f'/{RfcXmlElem.RFC_ENTRY}/{RfcXmlElem.WG_ACRONYM}/text()')
        if len(rfc_wgs) == 0:
            continue
        rfc_wg = rfc_wgs[0]

        if not re.match(r'^[^ ]+$', rfc_wg):
            continue
        if m := re.match(r'^RFC([0-9]+)$', rfc_id):
            rfc_number = m.group(1)
            obj[rfc_number] = "wg/%s" % rfc_wg

    RfcUtils.write_json_file(OUTPUT_PATH, obj)


def write_rfc_obsoletes():
    # RFCステータスの一覧の保存先
    OUTPUT_PATH = os.path.join(RfcFolder.OUTPUT_HTML_DIR, "obsoletes.json")

    page = RfcUtils.fetch_url("https://www.rfc-editor.org/rfc-index.xml")
    page_content = RfcUtils.remove_namespace_from_xml(page.content)
    tree = etree.XML(page_content)

    obj = {}

    for item in tree.xpath(f'/{RfcXmlElem.RFC_INDEX}/{RfcXmlElem.RFC_ENTRY}'):
        subtree = etree.XML(etree.tostring(item))

        rfc_ids = subtree.xpath(f'/{RfcXmlElem.RFC_ENTRY}/{RfcXmlElem.DOC_ID}/text()')
        if len(rfc_ids) == 0:
            continue
        rfc_id = rfc_ids[0]
        if m := re.match(r'^RFC([0-9]+)$', rfc_id):
            rfc_number = m.group(1)

        obj[rfc_number] = {}

        # obsoletes
        rfc_obsoletes = subtree.xpath(f'/{RfcXmlElem.RFC_ENTRY}/{RfcXmlElem.OBSOLETES}/{RfcXmlElem.DOC_ID}/text()')
        if len(rfc_obsoletes) > 0:
            rfc_obsoletes = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_obsoletes]
            obj[rfc_number][RfcJsonElem.OBSOLETES] = rfc_obsoletes

        # obsoleted-by
        rfc_obsoleted_by = subtree.xpath(f'/{RfcXmlElem.RFC_ENTRY}/{RfcXmlElem.OBSOLETED_BY}/{RfcXmlElem.DOC_ID}/text()')
        if len(rfc_obsoleted_by) > 0:
            rfc_obsoleted_by = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_obsoleted_by]
            obj[rfc_number][RfcJsonElem.OBSOLETED_BY] = rfc_obsoleted_by

        # updates
        rfc_updates = subtree.xpath(f'/{RfcXmlElem.RFC_ENTRY}/{RfcXmlElem.UPDATES}/{RfcXmlElem.DOC_ID}/text()')
        if len(rfc_updates) > 0:
            rfc_updates = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_updates]
            obj[rfc_number][RfcJsonElem.UPDATES] = rfc_updates

        # updated-by
        rfc_updated_by = subtree.xpath(f'/{RfcXmlElem.RFC_ENTRY}/{RfcXmlElem.UPDATED_BY}/{RfcXmlElem.DOC_ID}/text()')
        if len(rfc_updated_by) > 0:
            rfc_updated_by = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_updated_by]
            obj[rfc_number][RfcJsonElem.UPDATED_BY] = rfc_updated_by

        # current-status
        rfc_current_status = subtree.xpath(f'/{RfcXmlElem.RFC_ENTRY}/{RfcXmlElem.CURRENT_STATUS}/text()')
        if len(rfc_current_status) > 0:
            rfc_current_status = RfcUtils.replace_upper_to_camel(rfc_current_status[0])
            obj[rfc_number][RfcJsonElem.CURRENT_STATUS] = rfc_current_status

    RfcUtils.write_json_file(OUTPUT_PATH, obj)


if __name__ == '__main__':
    # write_rfc_wg_list()
    write_rfc_obsoletes()

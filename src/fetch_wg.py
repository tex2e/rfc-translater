# ------------------------------------------------------------------------------
# IETFのWebサイトからWGの一覧を取得するプログラム
# ------------------------------------------------------------------------------

import os
import re
import json
import requests
from lxml import etree
from pprint import pprint

# WorkingGroupのRFCの一覧の保存先
OUTPUT_PATH = os.path.join("html", "group-rfcs.json")


class RfcIndexXmlHandler:
    rfcs = []

    def start(self, tag: str, attrib):
        # print("start %s" % tag)
        if tag.endswith('rfc-entry'):
            self.rfc = {}
            return

        self.current_tag = tag

    def end(self, tag: str):
        # print("end %s" % tag)
        if tag.endswith('rfc-entry'):
            RfcIndexXmlHandler.rfcs.append(self.rfc)
            self.rfc = {}
            return

    def data(self, data: str):
        # print("data %r" % data.strip())
        text = data.strip()
        if len(text) == 0:
            return
        if self.current_tag.endswith('doc-id'):
            if hasattr(self, 'rfc'):
                self.rfc['rfc'] = text
        if self.current_tag.endswith('wg_acronym'):
            if hasattr(self, 'rfc'):
                self.rfc['wg'] = text

    def comment(self, text: str):
        print("comment %s" % text)

    def close(self):
        print("Finished!")
        return True


def fetch_url(url: str):
    headers = {'User-agent': '', 'referer': url}
    page = requests.get(url, headers, timeout=(36.2, 180))
    return page

def write_rfc_wg_list():
    page = fetch_url("https://www.rfc-editor.org/rfc-index.xml")
    # parser = etree.XMLParser(target=RfcIndexXmlHandler())
    # etree.XML(page.content, parser)

    # XMLの名前空間名を除去
    page_content = re.sub(rb' xmlns(:xsi)?="[^"]+"', rb'', page.content, count=1)

    tree = etree.XML(page_content)
    # pprint(tree)
    # pprint(tree.xpath('/rfc-index/rfc-entry'))

    obj = {}

    for item in tree.xpath('/rfc-index/rfc-entry'):
        # item_content = etree.tostring(item)
        # item_content = re.sub(rb' xmlns(:xsi)?="[^"]+"', rb'', item_content, count=1)
        # print('-' * 80)
        # pprint(item_content)
        subtree = etree.XML(etree.tostring(item))

        rfc_ids = subtree.xpath('/rfc-entry/doc-id/text()')
        if len(rfc_ids) == 0:
            continue
        rfc_id = rfc_ids[0]

        rfc_wgs = subtree.xpath('/rfc-entry/wg_acronym/text()')
        if len(rfc_wgs) == 0:
            continue
        rfc_wg = rfc_wgs[0]

        if not re.match(r'^[^ ]+$', rfc_wg):
            continue
        if m := re.match(r'^RFC([0-9]+)$', rfc_id):
            rfc_number = m.group(1)
            obj[rfc_number] = "wg/%s" % rfc_wg


    # RfcIndexXmlHandler.rfcs.sort(key=lambda x: x['rfc'])

    # pprint(RfcIndexXmlHandler.rfcs)

    # obj = {}

    # for rfc in RfcIndexXmlHandler.rfcs:
    #     rfc_id = rfc.get('rfc', '')
    #     rfc_wg = rfc.get('wg', '')
    #     if not re.match(r'^[^ ]+$', rfc_wg):
    #         continue
    #     if m := re.match(r'^RFC([0-9]+)$', rfc_id):
    #         rfc_number = m.group(1)
    #         obj[rfc_number] = "wg/%s" % rfc_wg

    with open(OUTPUT_PATH, 'w', encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    write_rfc_wg_list()

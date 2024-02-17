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

def fetch_url(url: str):
    headers = {'User-agent': '', 'referer': url}
    page = requests.get(url, headers, timeout=(36.2, 180))
    return page

def write_rfc_wg_list():
    page = fetch_url("https://www.rfc-editor.org/rfc-index.xml")

    # XMLの名前空間名を除去
    page_content = re.sub(rb' xmlns(:xsi)?="[^"]+"', rb'', page.content, count=1)

    tree = etree.XML(page_content)

    obj = {}

    for item in tree.xpath('/rfc-index/rfc-entry'):
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

    with open(OUTPUT_PATH, 'w', encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    write_rfc_wg_list()

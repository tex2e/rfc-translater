# ------------------------------------------------------------------------------
# IETFのWebサイトからRFC一覧を取得するプログラム
# ------------------------------------------------------------------------------

import re
import glob
# from pprint import pprint
from lxml import etree
from rfc_utils import RfcUtils

def fetch_remote_index() -> list[int]:
    # 発行されているRFCの番号の一覧をページから取得する

    page = RfcUtils.fetch_url("https://www.rfc-editor.org/rfc-index.xml")
    page_content = RfcUtils.remove_namespace_from_xml(page.content)
    tree = etree.XML(page_content)

    rfc_numbers = []

    for item in tree.xpath('/rfc-index/rfc-entry'):
        subtree = etree.XML(etree.tostring(item))

        rfc_ids = subtree.xpath('/rfc-entry/doc-id/text()')
        if len(rfc_ids) == 0:
            continue
        rfc_id = rfc_ids[0]

        if m := re.match(r'^RFC(\d+)$', rfc_id):
            rfc_number = m.group(1)
            rfc_numbers.append(int(rfc_number))

    return rfc_numbers

def fetch_local_index() -> list[int]:
    # 作成したRFCに対応するHTMLの番号の一覧をローカルから取得する。
    LOCAL_FILEPATH = 'html/rfc*.html'
    rfc_numbers = []
    for filename in glob.glob(LOCAL_FILEPATH):
        m = re.match(r'^html[/\\]rfc(\d+)', filename)
        if m:
            rfc_numbers.append(int(m[1]))

    return rfc_numbers

def diff_remote_and_local_index() -> list[int]:
    # RFC Indexとローカルのhtml/のRFCの差分を作成する。
    # 返り値は、RFC番号の一覧
    remote_index = fetch_remote_index()
    local_index  = fetch_local_index()
    diff_index = set(remote_index) - set(local_index)
    return diff_index

def get_rfc_number(string: str) -> str:
    return string.strip().replace("RFC", "")


if __name__ == '__main__':
    print(fetch_remote_index())

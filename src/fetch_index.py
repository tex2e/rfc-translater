
from lxml import html  # pip install lxml
import requests

import os
import re
import glob
import json

OUTPUT_DIR  = "html"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "obsoletes.json")

def fetch_remote_index():
    # 発行されているRFCの番号の一覧をページから取得する

    url = 'https://tools.ietf.org/rfc/index'
    headers = { 'User-agent': '', 'referer': url }
    page = requests.get(url, headers, timeout=(36.2, 180))
    tree = html.fromstring(page.content)

    # RFC INDEX の内容を抽出
    rfc_index = tree.xpath('//div[@class="content"]/pre//text()')
    rfc_index = ''.join(rfc_index)
    tmp = rfc_index.split(
        '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')[2]
    # RFCの一覧のみを抽出
    contents = re.compile(r'\n\n+').split(tmp)[2:] # 空行区切り、先頭の余分な文字を除去
    rfcs = []
    for content in contents:
        content = re.sub(r'\n +', ' ', content)
        if re.search(r'Not Issued', content):
            continue
        rfcs.append(content)

    rfc_numbers = [] # rfcの番号一覧
    data = {} # 廃止・更新情報一覧
    for rfc in rfcs:
        #m = re.match(r'^RFC(\d+)', rfc)
        m = re.match(r'^RFC(?P<rfc>\d+) (?P<content>.+)$', rfc)
        if m:
            rfc_number = m["rfc"]
            rfc_numbers.append(int(rfc_number))
            content = m["content"]

            obj = {}
            m = re.search(r'\(Obsoletes (?P<obsoletes>[^)]+)\)', content)
            if m:
                obsoletes = list(map(get_rfc_number, m["obsoletes"].split(", ")))
                obj["obsoletes"] = obsoletes
            m = re.search(r'\(Obsoleted by (?P<obsoleted_by>[^)]+)\)', content)
            if m:
                obsoleted_by = list(map(get_rfc_number, m["obsoleted_by"].split(", ")))
                obj["obsoleted_by"] = obsoleted_by
            m = re.search(r'\(Updates (?P<updates>[^)]+)\)', content)
            if m:
                updates = list(map(get_rfc_number, m["updates"].split(", ")))
                obj["updates"] = updates
            m = re.search(r'\(Updated by (?P<updated_by>[^)]+)\)', content)
            if m:
                updated_by = list(map(get_rfc_number, m["updated_by"].split(", ")))
                obj["updated_by"] = updated_by

            # print(obj)
            data[rfc_number] = obj

    if os.path.isdir(OUTPUT_DIR):
        with open(OUTPUT_PATH, 'w', encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return rfc_numbers

def fetch_local_index():
    # 作成したRFCに対応するHTMLの番号の一覧をローカルディスクから取得する。

    pathname = 'html/rfc*.html'
    rfc_numbers = []
    for filename in glob.glob(pathname):
        m = re.match(r'^html[/\\]rfc(\d+)', filename)
        if m:
            rfc_numbers.append(int(m[1]))

    return rfc_numbers

def diff_remote_and_local_index():
    # RFC Indexとローカルのhtml/のRFCの差分を作成する。
    # 返り値は、RFC番号の一覧
    remote_index = fetch_remote_index()
    local_index  = fetch_local_index()
    diff_index = set(remote_index) - set(local_index)
    return diff_index

def get_rfc_number(string):
    return string.strip().replace("RFC", "")


if __name__ == '__main__':
    print(fetch_remote_index())

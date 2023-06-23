# ------------------------------------------------------------------------------
# IETFのWebサイトからRFC一覧を取得するプログラム
# ------------------------------------------------------------------------------

import requests
import os
import re
import glob
import json
# from pprint import pprint

OUTPUT_DIR  = "html"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "obsoletes.json")

def fetch_remote_index() -> list[int]:
    # 発行されているRFCの番号の一覧をページから取得する

    url = 'https://www.ietf.org/download/rfc-index.txt'
    headers = {'User-agent': '', 'referer': url}
    page = requests.get(url, headers, timeout=(36.2, 180))

    # RFC INDEX の内容を抽出
    rfc_index_page = page.content.decode('utf-8')
    # RFCの一覧のみを抽出
    rfc_index_list = rfc_index_page.split(
        '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')[1]
    # 空行区切りでリスト化
    rfc_text = rfc_index_list.split('\n\n')
    rfcs = []
    for rfc_content in rfc_text:
        # 各行の前後空白を削除
        tmp = ' '.join(map(lambda l: l.strip(), rfc_content.split('\n')))
        # 発行されていないRFCは無視
        if re.search(r'Not Issued', tmp):
            continue
        rfcs.append(tmp)

    # pprint(rfcs)

    rfc_numbers = []  # rfcの番号一覧
    data = {}  # 廃止・更新情報一覧
    for rfc in rfcs:
        m = re.match(r'^(?P<rfc>\d+) (?P<content>.+)$', rfc)
        if m:
            rfc_number = m["rfc"]
            rfc_numbers.append(int(rfc_number))
            content = m["content"]

            obj = {}
            if m := re.search(r'\(Obsoletes (?P<obsoletes>[^)]+)\)', content):
                obsoletes = list(map(get_rfc_number, m["obsoletes"].split(", ")))
                obj["obsoletes"] = obsoletes
            if m := re.search(r'\(Obsoleted by (?P<obsoleted_by>[^)]+)\)', content):
                obsoleted_by = list(map(get_rfc_number, m["obsoleted_by"].split(", ")))
                obj["obsoleted_by"] = obsoleted_by
            if m := re.search(r'\(Updates (?P<updates>[^)]+)\)', content):
                updates = list(map(get_rfc_number, m["updates"].split(", ")))
                obj["updates"] = updates
            if m := re.search(r'\(Updated by (?P<updated_by>[^)]+)\)', content):
                updated_by = list(map(get_rfc_number, m["updated_by"].split(", ")))
                obj["updated_by"] = updated_by
            if m := re.search(re.compile(r'\(Status: (?P<status>[^)]+)\)'), content):
                status = m['status']
                status = re.sub(r'\s+', ' ', status)
                if status == 'UNKNOWN':
                    obj["status"] = 'Unknown'
                if status == 'DRAFT':
                    obj["status"] = 'Draft'
                if status == 'INFORMATIONAL':
                    obj["status"] = 'Informational'
                if status == 'EXPERIMENTAL':
                    obj["status"] = 'Experimental'
                if status == 'BEST CURRENT PRACTICE':
                    obj["status"] = 'Best Common Practice'
                if status == 'PROPOSED STANDARD':
                    obj["status"] = 'Proposed Standard'
                if status == 'DRAFT STANDARD':
                    obj["status"] = 'Draft Standard'
                if status == 'INTERNET STANDARD':
                    obj["status"] = 'Internet Standard'
                if status == 'HISTORIC':
                    obj["status"] = 'Historic'
                if status == 'OBSOLETE':
                    obj["status"] = 'Obsolete'

            # print(obj)
            data[rfc_number] = obj

    if os.path.isdir(OUTPUT_DIR):
        with open(OUTPUT_PATH, 'w', encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    # pprint(data)

    return rfc_numbers

def fetch_local_index() -> list[int]:
    # 作成したRFCに対応するHTMLの番号の一覧をローカルディスクから取得する。

    pathname = 'html/rfc*.html'
    rfc_numbers = []
    for filename in glob.glob(pathname):
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

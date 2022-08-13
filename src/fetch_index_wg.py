
from lxml import etree  # pip install lxml
import requests
import os
import re
import glob
import json
from pprint import pprint

OUTPUT_DIR  = "data/draft"
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "working-group.json")

def fetch_index_wg() -> None:
    # 収集結果はdata/draft/working-group.jsonに保存する

    data = {}

    # Working Groupの一覧を取得
    url = 'https://datatracker.ietf.org/wg/'
    headers = {'User-agent': ''}
    page = requests.get(url, headers, timeout=(36.2, 180))
    ietf_wg = page.content.decode('utf-8')
    working_groups = re.findall(r'<a href="/wg/([^/]+)/">', ietf_wg)
    # pprint(working_groups)

    for working_group in working_groups:
        draft_pathes, rfcs = get_draft_documents(working_group)

        data[working_group] = {}
        data[working_group]['rfcs'] = rfcs
        data[working_group]['drafts'] = []

        for draft in draft_pathes:
            detail = get_draft_detail(draft)
            data[working_group]['drafts'].append(detail)

    # pprint(data)

    if os.path.isdir(OUTPUT_DIR):
        with open(OUTPUT_PATH, 'w', encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return


# WorkingGroupのDraftの一覧とRFCの一覧を取得
# ex. https://datatracker.ietf.org/wg/tls/documents/
def get_draft_documents(wg_name: str) -> (list[str], list[str]):
    url = f'https://datatracker.ietf.org/wg/{wg_name}/documents/'
    print('[+] WorkingGroup:', wg_name)
    print('[+] url:', url)
    headers = {'User-agent': ''}
    page = requests.get(url, headers, timeout=(36.2, 180))
    content = page.content.decode('utf-8')
    drafts = re.findall(r'<a href="(/doc/draft-[^/]+/)">', content)
    drafts = sorted(set(drafts))
    # pprint(drafts)
    rfcs = re.findall(r'<a href="/doc/rfc(\d+)/">', content)
    # pprint(rfcs)
    return drafts, rfcs

# Draftの詳細を取得
# ex. https://datatracker.ietf.org/doc/draft-ietf-tls-subcerts/15
def get_draft_detail(path: str) -> dict:
    url = f'https://datatracker.ietf.org{path}'
    print('[+] +-- url:', url)
    headers = {'User-agent': ''}
    page = requests.get(url, headers, timeout=(36.2, 180))
    content = page.content.decode('utf-8')
    # pprint(content)

    # Last updated
    regex = re.compile(r'<th scope="row">Last updated</th>\s+<td class="edit"></td>\s+<td>\s+(?P<date>\d+-\d+-\d+)', re.MULTILINE)
    last_updated = ''
    if m := re.search(regex, content):
        last_updated = m['date']

    # Type (Expired / Active)
    regex = re.compile(r'<span class="text-danger">Expired Internet-Draft')
    is_expired = False
    if re.search(regex, content):
        is_expired = True

    # Versions
    regex = re.compile(r'href="/doc/draft-[^/]+/(\d+)/"')
    versions = re.findall(regex, content)

    res = {
        'path': path,
        'last_updated': last_updated,
        'is_expired': is_expired,
        'versions': versions
    }
    # print(res)
    return res


def fetch_local_draft_index() -> list[str]:
    # 作成したRFC Draftに対応するHTMLの番号の一覧をローカルディスクから取得する。

    pathname = 'html/draft/draft*.html'
    rfc_drafts = []
    for filename in glob.glob(pathname):
        m = re.match(r'^html[/\\]draft[/\\](?P<draftname>draft-.*)\.html', filename)
        if m:
            rfc_drafts.append(m['draftname'])

    return rfc_drafts

def fetch_remote_draft_index() -> list[str]:

    pathname = 'data/draft/working-group.json'

    with open(pathname, 'r') as f:
        data = json.load(f)

    rfc_drafts = []

    for working_group in data:
        for draft in data[working_group]['drafts']:
            draft_name = draft['path']
            draft_name = re.sub(r'^/doc/|/$', '', draft_name)
            draft_latest_version = draft['versions'][-1]
            if draft_latest_version is None:
                continue
            rfc_drafts.append(f'{draft_name}-{draft_latest_version}')

    return rfc_drafts

def diff_remote_and_local_index() -> list[int]:
    # RFC Indexとローカルのhtml/のRFCの差分を作成する。
    # 返り値は、RFC番号の一覧
    remote_index = fetch_remote_index()
    local_index  = fetch_local_index()
    diff_index = set(remote_index) - set(local_index)
    return diff_index


if __name__ == '__main__':
    # print(fetch_index_wg())

    # https://datatracker.ietf.org/doc/draft-ietf-tls-hybrid-design/
    res = get_draft_detail('/doc/draft-ietf-tls-hybrid-design/')
    exp = {
        'path': '/doc/draft-ietf-tls-hybrid-design/',
        'last_updated': '2022-07-25',
        'is_expired': True,
        'versions': ['00', '01', '02', '03', '04']
    }
    pprint(res)
    assert res == exp

    # https://datatracker.ietf.org/wg/tls/documents/
    drafts, rfcs = get_draft_documents('tls')
    pprint(drafts)
    pprint(rfcs)
    assert '/doc/draft-ietf-tls-56-bit-ciphersuites/' in drafts
    assert '2246' in rfcs

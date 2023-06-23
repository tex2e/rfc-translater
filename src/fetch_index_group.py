# ------------------------------------------------------------------------------
# IETFのWebサイトからWGの一覧を取得するプログラム
# ------------------------------------------------------------------------------

import requests
import os
import re
import glob
import json
# from pprint import pprint

# # ドラフトの一覧の保存先
# OUTPUT_DIR1  = "data/draft"
# OUTPUT_PATH1 = os.path.join(OUTPUT_DIR1, "drafts.json")

# WorkingGroupのRFCの一覧の保存先
OUTPUT_DIR2  = "html"
OUTPUT_PATH2 = os.path.join(OUTPUT_DIR2, "group-rfcs.json")

def fetch_index_group() -> None:

    # data_drafts = {}
    data_wg_rfcs = {}

    # Working Groupの一覧を取得
    working_group_list = []
    working_group_list.append(('wg', get_working_groups(group='wg')))  # Working Groups
    working_group_list.append(('rg', get_working_groups(group='rg')))  # Research Groups
    print(working_group_list)

    for group_name, working_groups in working_group_list:
        for working_group in working_groups:
            draft_pathes, rfcs = get_draft_documents(working_group, group=group_name)

            # # data/draft/drafts.json
            # data_drafts[working_group] = {}
            # data_drafts[working_group]['drafts'] = []
            # for draft in draft_pathes:
            #     detail = get_draft_detail(draft)
            #     data_drafts[working_group]['drafts'].append(detail)

            # html/group-rfcs.json
            for rfc in rfcs:
                data_wg_rfcs[rfc] = f'{group_name}/{working_group}'

    # pprint(data_drafts)

    # with open(OUTPUT_PATH1, 'w', encoding="utf-8", newline="\n") as f:
    #     json.dump(data_drafts, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_PATH2, 'w', encoding="utf-8", newline="\n") as f:
        json.dump(data_wg_rfcs, f, ensure_ascii=False, indent=2)

    return


# Working Groupの一覧を取得
def get_working_groups(group='wg') -> list[str]:
    url = f'https://datatracker.ietf.org/{group}/'
    headers = {'User-agent': ''}
    page = requests.get(url, headers, timeout=(36.2, 180))
    content = page.content.decode('utf-8')
    working_groups = re.findall(rf'<a href="/{group}/([^/]+)/">', content)
    return working_groups

# WorkingGroupのDraftの一覧とRFCの一覧を取得
# ex. https://datatracker.ietf.org/wg/tls/documents/
# ex. https://datatracker.ietf.org/rg/cfrg/documents/
def get_draft_documents(wg_name: str, group='wg') -> (list[str], list[str]):
    url = f'https://datatracker.ietf.org/{group}/{wg_name}/documents/'
    print('[+] WorkingGroup:', wg_name)
    print('[+] url:', url)
    headers = {'User-agent': ''}
    page = requests.get(url, headers, timeout=(36.2, 180))
    content = page.content.decode('utf-8')
    drafts = re.findall(r'<a href="/doc/(draft-[^/]+)/">', content)
    # drafts = sorted(set(drafts))
    # pprint(drafts)
    rfcs = re.findall(r'<a href="/doc/rfc(\d+)/">', content)
    # pprint(rfcs)
    return drafts, rfcs

# Draftの詳細を取得
# ex. https://datatracker.ietf.org/doc/draft-ietf-tls-subcerts/
def get_draft_detail(draft_name: str) -> dict:
    url = f'https://datatracker.ietf.org/doc/{draft_name}/'
    print('[+]   url:', url)
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
    latest_version = versions[-1]

    res = {
        'name': draft_name,
        # 'path': f'/doc/{draft_name}/',
        'last_updated': last_updated,
        'is_expired': is_expired,
        'latest_version': latest_version
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
            draft_latest_version = draft['latest_version']
            if draft_latest_version is None:
                continue
            rfc_drafts.append(f'{draft_name}-{draft_latest_version}')

    return rfc_drafts

def diff_remote_and_local_index() -> list[int]:
    # RFC Indexとローカルのhtml/のRFCの差分を作成する。
    # 返り値は、RFC番号の一覧
    remote_index = fetch_remote_draft_index()
    local_index  = fetch_local_draft_index()
    diff_index = set(remote_index) - set(local_index)
    return diff_index


if __name__ == '__main__':
    # print(fetch_index_group())

    # https://datatracker.ietf.org/rg/
    res = get_working_groups(group='rg')
    print(res)
    assert 'cfrg' in res

    # https://datatracker.ietf.org/doc/draft-ietf-tls-hybrid-design/
    res = get_draft_detail('draft-ietf-tls-hybrid-design')
    exp = {
        'name': 'draft-ietf-tls-hybrid-design',
        # 'path': '/doc/draft-ietf-tls-hybrid-design/',
        'last_updated': '2022-07-25',
        'is_expired': True,
        'latest_version': '04'
    }
    print(res)
    assert res == exp

    # https://datatracker.ietf.org/wg/tls/documents/
    drafts, rfcs = get_draft_documents('tls')
    print(drafts)
    print(rfcs)
    assert 'draft-ietf-tls-56-bit-ciphersuites' in drafts
    assert '2246' in rfcs

    # https://datatracker.ietf.org/rg/cfrg/documents/
    drafts, rfcs = get_draft_documents('cfrg', group='rg')
    print(drafts)
    print(rfcs)
    assert 'draft-irtf-cfrg-rsa-blind-signatures' in drafts
    assert '7539' in rfcs

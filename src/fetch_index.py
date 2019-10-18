
from lxml import html
import requests

import re
import glob

def fetch_remote_index():

    url = 'https://tools.ietf.org/rfc/index'
    headers = { 'User-agent': '', 'referer': url }
    page = requests.get(url, headers)
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

    rfc_numbers = []
    for rfc in rfcs:
        m = re.match(r'^RFC(\d+)', rfc)
        if m:
            rfc_numbers.append(int(m[1]))

    return rfc_numbers

def fetch_local_index():

    pathname = 'html/rfc*.html'
    rfc_numbers = []
    for filename in glob.glob(pathname):
        m = re.match(r'^html/rfc(\d+)', filename)
        if m:
            rfc_numbers.append(int(m[1]))

    return rfc_numbers

def diff_remote_and_local_index():
    remote_index = fetch_remote_index()
    local_index  = fetch_local_index()
    diff_index = set(remote_index) - set(local_index)
    return diff_index

def show_progress():
    local_index  = fetch_local_index()
    remote_index = fetch_remote_index()
    current = len(local_index)
    total   = len(remote_index)
    print('current/total: %d/%d' % (current, total))
    print('progress:      %.2f%%' % (current * 100 / total))

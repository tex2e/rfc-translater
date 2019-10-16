
from lxml import html
import requests

import re
import glob

def fetch_remote_index():

    url = 'https://tools.ietf.org/rfc/index'
    headers = { 'User-agent': '', 'referer': url }
    page = requests.get(url, headers)
    tree = html.fromstring(page.content)

    rfc_urls = tree.xpath('//div[@class="content"]/pre/a/@href')
    rfc_numbers = []
    for rfc_url in rfc_urls:
        m = re.search(r'(\d+)$', rfc_url)
        if m:
            rfc_numbers.append(int(m[1]))

    return rfc_numbers

def fetch_local_index():

    pathname = 'html/rfc*.html'
    rfc_numbers = []
    for filename in glob.glob(pathname):
        m = re.search(r'(\d+).html$', filename)
        if m:
            rfc_numbers.append(int(m[1]))

    return rfc_numbers

def diff_remote_and_local_index():
    remote_index = fetch_remote_index()
    local_index  = fetch_local_index()
    diff_index = set(remote_index) - set(local_index)
    return diff_index

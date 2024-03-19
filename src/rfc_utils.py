
import re
import textwrap
import requests
from datetime import datetime, timedelta, timezone

class RfcUtils:

    # Webページ取得
    @staticmethod
    def fetch_url(url: str):
        headers = {'User-agent': '', 'referer': url}
        page = requests.get(url, headers, timeout=(36.2, 180))
        return page

    # XMLの名前空間名を除去
    @staticmethod
    def remove_namespace_from_xml(xml: bytes) -> bytes:
        removed_xml = re.sub(rb' xmlns(:[^=]+)?="[^"]+"', rb'', xml, count=1)
        return removed_xml

    # RFC番号の取得 (文字列)
    @staticmethod
    def get_rfc_number_str(text: str) -> str:
        if m := re.match(re.compile(r'RFC ?(\d+)', re.IGNORECASE), text):
            return m[1]
        return None

    # RFC番号の取得 (文字列)
    @staticmethod
    def get_rfc_number_int(text: str) -> int:
        if m := re.match(re.compile(r'RFC ?(\d+)', re.IGNORECASE), text):
            return int(m[1])
        return None

    # 文字列の先頭から「RFC」を除去
    @staticmethod
    def replace_rfcXXXX_to_XXXX(text: str) -> str:
        return re.sub(r'^RFC *', '', text)

    # 文字列を大文字からキャメルケースに変換
    @staticmethod
    def replace_upper_to_camel(text: str) -> str:
        def _upper_to_camel(matchobj) -> str:
            return matchobj.group(1) + matchobj.group(2).lower()
        return re.sub(r'\b([A-Z])([A-Z0-9]+)\b', _upper_to_camel, text)

    # 単一行の2つの文字列のインデントの差を求める関数
    @staticmethod
    def get_indent(text: str) -> int:
        return len(text) - len(text.lstrip())

    # 複数行の2つの文字列のインデントの差を求める関数
    @staticmethod
    def get_indent_multiline(text: str) -> int:
        str_before = text
        str_after = textwrap.dedent(text)
        return len(str_before.split('\n')[0]) - len(str_after.split('\n')[0])

    # 複数行の2つの文字列の長さの差を求める関数
    @staticmethod
    def get_line_len_diff(text1: str, text2: str) -> int:
        first_line1 = text1.split('\n')[0]
        first_line2 = text2.split('\n')[0]
        return abs(len(first_line1) - len(first_line2))

    # 本文中にあるaタグ（RFCへのリンクなど）を削除する
    @staticmethod
    def html_rm_link_tag(raw_html: bytes) -> bytes:
        cleaner = re.compile(rb'<a href="./rfc\d+[^"]*"[^>]*>')
        cleantext = re.sub(cleaner, b'', raw_html)
        return cleantext

    # 現在時刻の取得
    @staticmethod
    def get_now():
        JST = timezone(timedelta(hours=+9), 'JST')
        return datetime.now(JST)

    # 実行前にユーザに確認を求めるメッセージを表示する。yで継続、nで中断
    @staticmethod
    def yes_no_input(question: str):
        while True:
            choice = input(question + " [y/N]: ").lower()
            if choice in ['y', 'ye', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False

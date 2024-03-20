
import re
import textwrap
import requests
from datetime import datetime, timedelta, timezone

class RfcUtils:
    """RFC処理汎用クラス"""

    @staticmethod
    def fetch_url(url: str) -> object:
        """Webページ取得"""
        headers = {'User-agent': '', 'referer': url}
        page = requests.get(url, headers, timeout=(36.2, 180))
        return page

    @staticmethod
    def remove_namespace_from_xml(xml: bytes) -> bytes:
        """XMLの名前空間名を除去"""
        removed_xml = re.sub(rb' xmlns(:[^=]+)?="[^"]+"', rb'', xml, count=1)
        return removed_xml

    @staticmethod
    def get_rfc_number_str(text: str) -> str:
        """RFC番号の取得 (文字列)"""
        if m := re.match(re.compile(r'RFC ?(\d+)', re.IGNORECASE), text):
            return m[1]
        return None

    @staticmethod
    def get_rfc_number_int(text: str) -> int:
        """RFC番号の取得 (文字列)"""
        if m := re.match(re.compile(r'RFC ?(\d+)', re.IGNORECASE), text):
            return int(m[1])
        return None

    @staticmethod
    def replace_rfcXXXX_to_XXXX(text: str) -> str:
        """文字列の先頭から「RFC」を除去"""
        return re.sub(r'^RFC *', '', text)

    @staticmethod
    def replace_upper_to_camel(text: str) -> str:
        """文字列を大文字からキャメルケースに変換"""
        def _upper_to_camel(matchobj) -> str:
            return matchobj.group(1) + matchobj.group(2).lower()
        return re.sub(r'\b([A-Z])([A-Z0-9]+)\b', _upper_to_camel, text)

    @staticmethod
    def get_indent(text: str) -> int:
        """単一行の2つの文字列のインデントの差を求める関数"""
        return len(text) - len(text.lstrip())

    @staticmethod
    def get_indent_multiline(text: str) -> int:
        """複数行の2つの文字列のインデントの差を求める関数"""
        str_before = text
        str_after = textwrap.dedent(text)
        return len(str_before.split('\n')[0]) - len(str_after.split('\n')[0])

    @staticmethod
    def get_line_len_diff(text1: str, text2: str) -> int:
        """複数行の2つの文字列の長さの差を求める関数"""
        first_line1 = text1.split('\n')[0]
        first_line2 = text2.split('\n')[0]
        return abs(len(first_line1) - len(first_line2))

    @staticmethod
    def html_rm_link_tag(raw_html: bytes) -> bytes:
        """本文中にあるaタグ（RFCへのリンクなど）を削除する"""
        cleaner = re.compile(rb'<a href="./rfc\d+[^"]*"[^>]*>')
        cleantext = re.sub(cleaner, b'', raw_html)
        return cleantext

    @staticmethod
    def get_now():
        """現在時刻の取得"""
        JST = timezone(timedelta(hours=+9), 'JST')
        return datetime.now(JST)

    @staticmethod
    def yes_no_input(question: str):
        """実行前にユーザに確認を求めるメッセージを表示する。yで継続、nで中断"""
        while True:
            choice = input(question + " [y/N]: ").lower()
            if choice in ['y', 'ye', 'yes']:
                return True
            elif choice in ['n', 'no']:
                return False

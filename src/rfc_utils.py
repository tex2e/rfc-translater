
import re
import json
import requests

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

    # 文字列の先頭から「RFC」を除去
    @staticmethod
    def replace_rfcXXXX_to_XXXX(text: str) -> str:
        return re.sub(r'^RFC *', '', text)

    # 文字列を大文字からキャメルケースに変換
    @staticmethod
    def replace_upper_to_camel(text: str) -> str:
        return re.sub(r'\b([A-Z])([A-Z0-9]+)\b', RfcUtils._upper_to_camel, text)

    @staticmethod
    def _upper_to_camel(matchobj):
        return matchobj.group(1) + matchobj.group(2).lower()

    # JSONファイルの書き込み
    @staticmethod
    def write_json_file(filepath: str, obj: object):
        FILEMODE = 'w'
        ENCODING = 'utf-8'
        NEWLINE = "\n"
        JSON_INDENT = 2
        with open(filepath, FILEMODE, encoding=ENCODING, newline=NEWLINE) as f:
            json.dump(obj, f, ensure_ascii=False, indent=JSON_INDENT)

    # JSONファイルの読み込み
    @staticmethod
    def read_json_file(filepath: str) -> object:
        FILEMODE = 'r'
        ENCODING = 'utf-8'
        with open(filepath, FILEMODE, encoding=ENCODING) as f:
            obj = json.load(f)
            return obj


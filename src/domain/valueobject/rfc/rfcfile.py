
import os
import json
from . import IRfc, Rfc, RfcDraft

class RfcFile:
    """RFCファイル関連クラス"""

    OUTPUT_HTML_DIR = 'html'
    OUTPUT_DATA_DIR = 'data'
    OUTPUT_DRAFT = 'draft'

    OUTPUT_HTML_INDEX_FILE = 'html/index.html'
    OUTPUT_HTML_DRAFT_INDEX_FILE = 'html/draft/index.html'
    OUTPUT_HTML_RFC_LIST_JSON_FILE = 'html/data-rfc-list.json'
    GLOB_HTML_FILE = 'html/rfc*.html'
    GLOB_HTML_DRAFT_FILE = 'html/draft/draft-*.html'

    TEMPLATE_HTML_INDEX = 'templates/index.html'
    TEMPLATE_HTML_RFC = 'templates/rfc.html'

    @staticmethod
    def get_dir_data(rfc: IRfc) -> str:
        """RFCのJSONなどの中間ファイル格納先ディレクトリ"""
        assert isinstance(rfc, IRfc)
        if isinstance(rfc, Rfc):
            return os.path.join(RfcFile.OUTPUT_DATA_DIR, '%04d' % (int(rfc.get_id()) // 1000 % 10 * 1000))
        elif isinstance(rfc, RfcDraft):
            return os.path.join(RfcFile.OUTPUT_DATA_DIR, RfcFile.OUTPUT_DRAFT)

    @staticmethod
    def get_dir_html(rfc: IRfc) -> str:
        """RFCのHTMLファイル格納先ディレクトリ"""
        assert isinstance(rfc, IRfc)
        if isinstance(rfc, Rfc):
            return os.path.join(RfcFile.OUTPUT_HTML_DIR)
        elif isinstance(rfc, RfcDraft):
            return os.path.join(RfcFile.OUTPUT_HTML_DIR, RfcFile.OUTPUT_DRAFT)

    @staticmethod
    def get_filepath_data_json(rfc: IRfc) -> str:
        """RFCの本文取得・解析結果ファイルパス"""
        assert isinstance(rfc, IRfc)
        dir_data = RfcFile.get_dir_data(rfc)
        if isinstance(rfc, Rfc):
            return os.path.join(dir_data, f'rfc{rfc.get_id()}.json')
        elif isinstance(rfc, RfcDraft):
            return os.path.join(dir_data, f'{rfc.get_id()}.json')

    @staticmethod
    def get_filepath_data_trans_json(rfc: IRfc) -> str:
        """RFCの翻訳結果ファイルパス"""
        assert isinstance(rfc, IRfc)
        dir_data = RfcFile.get_dir_data(rfc)
        if isinstance(rfc, Rfc):
            return os.path.join(dir_data, f'rfc{rfc.get_id()}-trans.json')
        elif isinstance(rfc, RfcDraft):
            return os.path.join(dir_data, f'{rfc.get_id()}-trans.json')

    @staticmethod
    def get_filepath_data_midway_json(rfc: IRfc) -> str:
        """RFCの翻訳作業途中結果ファイルパス"""
        assert isinstance(rfc, IRfc)
        dir_data = RfcFile.get_dir_data(rfc)
        if isinstance(rfc, Rfc):
            return os.path.join(dir_data, f'rfc{rfc.get_id()}-midway.json')
        elif isinstance(rfc, RfcDraft):
            return os.path.join(dir_data, f'{rfc.get_id()}-midway.json')

    @staticmethod
    def get_filepath_data_summary_json(rfc: IRfc) -> str:
        """RFCの要約JSONファイルパス"""
        assert isinstance(rfc, IRfc)
        dir_data = RfcFile.get_dir_data(rfc)
        if isinstance(rfc, Rfc):
            return os.path.join(dir_data, f'rfc{rfc.get_id()}-summary.json')
        elif isinstance(rfc, RfcDraft):
            return os.path.join(dir_data, f'{rfc.get_id()}-summary.json')

    @staticmethod
    def get_filepath_html_rfc(rfc: IRfc) -> str:
        """RFCのHTMLファイルパス"""
        assert isinstance(rfc, IRfc)
        dir_html = RfcFile.get_dir_html(rfc)
        if isinstance(rfc, Rfc):
            return os.path.join(dir_html, f'rfc{rfc.get_id()}.html')
        elif isinstance(rfc, RfcDraft):
            return os.path.join(dir_html, f'{rfc.get_id()}.html')

    @staticmethod
    def get_url_rfc_xml(rfc: IRfc) -> str:
        """RFCの取得先URL (XML)"""
        assert isinstance(rfc, IRfc)
        if isinstance(rfc, Rfc):
            return f'https://www.rfc-editor.org/rfc/rfc{rfc.get_id()}.xml'
        elif isinstance(rfc, RfcDraft):
            return f'https://www.ietf.org/archive/id/{rfc.get_id()}.xml'

    @staticmethod
    def get_url_rfc_html(rfc: IRfc) -> str:
        """RFCの取得先URL (HTML)"""
        assert isinstance(rfc, IRfc)
        if isinstance(rfc, Rfc):
            return f'https://datatracker.ietf.org/doc/html/rfc{rfc.get_id()}'
        elif isinstance(rfc, RfcDraft):
            return f'https://datatracker.ietf.org/doc/html/{rfc.get_id()}'

    @staticmethod
    def get_url_rfc_txt(rfc: IRfc) -> str:
        """RFCの取得先URL (TXT)"""
        assert isinstance(rfc, IRfc)
        if isinstance(rfc, Rfc):
            return f'https://www.rfc-editor.org/rfc/rfc{rfc.get_id()}.txt'
        elif isinstance(rfc, RfcDraft):
            return f'https://www.ietf.org/archive/id/{rfc.get_id()}.txt'

    @staticmethod
    def get_url_rfc_index_xml():
        """RFC Indexの取得先URL (XML)"""
        return 'https://www.rfc-editor.org/rfc-index.xml'

    @staticmethod
    def write_json_file(filepath: str, obj: object):
        """JSONファイルの書き込み"""
        with open(filepath, 'w', encoding='utf-8', newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)

    @staticmethod
    def read_json_file(filepath: str) -> object:
        """JSONファイルの読み込み"""
        with open(filepath, 'r', encoding='utf-8') as f:
            obj = json.load(f)
            return obj

    @staticmethod
    def write_html_file(filepath: str, obj: object):
        """HTMLファイルの書き込み"""
        with open(filepath, 'w', encoding='utf-8', newline="\n") as f:
            f.write(obj)

    @staticmethod
    def read_html_file(filepath: str) -> str:
        """HTMLファイルの読み込み"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return content

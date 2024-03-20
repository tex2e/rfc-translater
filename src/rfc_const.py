
import os
import json

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
    def get_dir_data(rfc_number: int | str) -> str:
        """RFCのJSONなどの中間ファイル格納先ディレクトリ"""
        if type(rfc_number) is int:
            return os.path.join(RfcFile.OUTPUT_DATA_DIR, '%04d' % (rfc_number // 1000 % 10 * 1000))
        elif type(rfc_number) is str:
            return os.path.join(RfcFile.OUTPUT_DATA_DIR, RfcFile.OUTPUT_DRAFT)

    @staticmethod
    def get_dir_html(rfc_number: int | str) -> str:
        """RFCのHTMLファイル格納先ディレクトリ"""
        if type(rfc_number) is int:
            return os.path.join(RfcFile.OUTPUT_HTML_DIR)
        elif type(rfc_number) is str:
            return os.path.join(RfcFile.OUTPUT_HTML_DIR, RfcFile.OUTPUT_DRAFT)

    @staticmethod
    def get_filepath_data_json(rfc_number: int | str) -> str:
        """RFCの本文取得・解析結果ファイルパス"""
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}.json')

    @staticmethod
    def get_filepath_data_trans_json(rfc_number: int | str) -> str:
        """RFCの翻訳結果ファイルパス"""
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}-trans.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}-trans.json')

    @staticmethod
    def get_filepath_data_midway_json(rfc_number: int | str) -> str:
        """RFCの翻訳作業途中結果ファイルパス"""
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}-midway.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}-midway.json')

    @staticmethod
    def get_filepath_data_summary_json(rfc_number: int | str) -> str:
        """RFCの要約JSONファイルパス"""
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}-summary.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}-summary.json')

    @staticmethod
    def get_filepath_html_rfc(rfc_number: int | str) -> str:
        """RFCのHTMLファイルパス"""
        dir_html = RfcFile.get_dir_html(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_html, f'rfc{rfc_number}.html')
        elif type(rfc_number) is str:
            return os.path.join(dir_html, f'draft-{rfc_number}.html')

    @staticmethod
    def get_url_rfc_xml(rfc_number: int | str) -> str:
        """RFCの取得先URL (XML)"""
        if type(rfc_number) is int:
            return f'https://www.rfc-editor.org/rfc/rfc{rfc_number}.xml'

    @staticmethod
    def get_url_rfc_html(rfc_number: int | str) -> str:
        """RFCの取得先URL (HTML)"""
        if type(rfc_number) is int:
            return f'https://datatracker.ietf.org/doc/html/rfc{rfc_number}'
        elif type(rfc_number) is str:
            return f'https://datatracker.ietf.org/doc/html/draft-{rfc_number}'

    @staticmethod
    def get_url_rfc_txt(rfc_number: int | str) -> str:
        """RFCの取得先URL (TXT)"""
        if type(rfc_number) is int:
            return f'https://www.rfc-editor.org/rfc/rfc{rfc_number}.txt'
        elif type(rfc_number) is str:
            return f'https://www.ietf.org/archive/id/draft-{rfc_number}.txt'

    def get_url_rfc_xml(rfc_number: int) -> str:
        """RFCの取得先URL (XML)"""
        return f'https://www.rfc-editor.org/rfc/rfc{rfc_number}.xml'

    @staticmethod
    def get_url_rfc_index_xml():
        """RFC Indexの取得先URL (XML)"""
        return 'https://www.rfc-editor.org/rfc-index.xml'

    @staticmethod
    def write_json_file(filepath: str, obj: object):
        """JSONファイルの書き込み"""
        FILEMODE = 'w'
        ENCODING = 'utf-8'
        NEWLINE = "\n"
        JSON_INDENT = 2
        with open(filepath, FILEMODE, encoding=ENCODING, newline=NEWLINE) as f:
            json.dump(obj, f, ensure_ascii=False, indent=JSON_INDENT)

    @staticmethod
    def read_json_file(filepath: str) -> object:
        """JSONファイルの読み込み"""
        FILEMODE = 'r'
        ENCODING = 'utf-8'
        with open(filepath, FILEMODE, encoding=ENCODING) as f:
            obj = json.load(f)
            return obj

    @staticmethod
    def write_html_file(filepath: str, obj: object):
        """HTMLファイルの書き込み"""
        FILEMODE = 'w'
        ENCODING = 'utf-8'
        NEWLINE = "\n"
        with open(filepath, FILEMODE, encoding=ENCODING, newline=NEWLINE) as f:
            f.write(obj)

    @staticmethod
    def read_html_file(filepath: str) -> str:
        """HTMLファイルの読み込み"""
        FILEMODE = 'r'
        ENCODING = 'utf-8'
        with open(filepath, FILEMODE, encoding=ENCODING) as f:
            content = f.read()
            return content


# ------------------------------------------------------------------------------
# https://www.rfc-editor.org/rfc-index.xml

class RfcIndexXmlElem:
    """RFC IndexファイルのXML構造"""
    # level1
    RFC_INDEX = 'rfc-index'
    # level2
    RFC_ENTRY = 'rfc-entry'
    # level3
    DOC_ID = 'doc-id'
    ABSTRACT = 'abstract'
    OBSOLETES = 'obsoletes'
    OBSOLETED_BY = 'obsoleted-by'
    UPDATES = 'updates'
    UPDATED_BY = 'updated-by'
    CURRENT_STATUS = 'current-status'
    WG_ACRONYM = 'wg_acronym'

class RfcIndexJsonElem:
    """RFC IndexファイルのJSON構造"""
    OBSOLETES = 'obs'
    OBSOLETED_BY = 'obs_by'
    UPDATES = 'upd'
    UPDATED_BY = 'upd_by'
    CURRENT_STATUS = 'st'
    WG = 'wg'


# ------------------------------------------------------------------------------
# https://www.rfc-editor.org/rfc/rfcXXXX.xml

class RfcXmlElem:
    """RFCファイルのXML構造"""
    # level1
    RFC = 'rfc'
    # level2
    FRONT = 'front'
    # level3
    TITLE = 'title'
    ABSTRACT = 'abstract'
    DATE = 'date'

class RfcJsonElem:
    """RFCファイルのJSON構造"""
    TITLE = 'title'
    class Title:
        TEXT = 'text'
        JA = 'ja'
    NUMBER = 'number'
    CREATED_AT = 'created_at'
    UPDATED_BY = 'updated_by'
    CONTENTS = 'contents'
    class Contents:
        INDENT = 'indent'
        TEXT = 'text'
        JA = 'ja'
        TITLE = 'title'
        SECTION_TITLE = 'section_title'
        RAW = 'raw'
        TOC = 'toc'
    IS_DRAFT = 'is_draft'


# ------------------------------------------------------------------------------

class RfcSummaryJsonElem:
    """RFC要約ファイルのJSON構造"""
    NUMBER = 'number'
    MODEL = 'model'
    CREATED_AT = 'created_at'
    SUMMARY = 'summary'

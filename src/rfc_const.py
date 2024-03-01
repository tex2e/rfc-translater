
import os
import json

class RfcFile:
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

    # RFCのJSONなどの中間ファイル格納先ディレクトリ
    @staticmethod
    def get_dir_data(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return os.path.join(RfcFile.OUTPUT_DATA_DIR, '%04d' % (rfc_number // 1000 % 10 * 1000))
        elif type(rfc_number) is str:
            return os.path.join(RfcFile.OUTPUT_DATA_DIR, RfcFile.OUTPUT_DRAFT)

    # RFCのHTMLファイル格納先ディレクトリ
    @staticmethod
    def get_dir_html(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return os.path.join(RfcFile.OUTPUT_HTML_DIR)
        elif type(rfc_number) is str:
            return os.path.join(RfcFile.OUTPUT_HTML_DIR, RfcFile.OUTPUT_DRAFT)

    # RFCの本文取得・解析結果ファイルパス
    @staticmethod
    def get_filepath_data_json(rfc_number: int | str) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}.json')

    # RFCの翻訳結果ファイルパス
    @staticmethod
    def get_filepath_data_trans_json(rfc_number: int | str) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}-trans.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}-trans.json')

    # RFCの翻訳作業途中結果ファイルパス
    @staticmethod
    def get_filepath_data_midway_json(rfc_number: int | str) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}-midway.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}-midway.json')

    # RFCの要約JSONファイルパス
    @staticmethod
    def get_filepath_data_summary_json(rfc_number: int | str) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}-summary.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}-summary.json')

    # RFCのHTMLファイルパス
    @staticmethod
    def get_filepath_html_rfc(rfc_number: int | str) -> str:
        dir_html = RfcFile.get_dir_html(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_html, f'rfc{rfc_number}.html')
        elif type(rfc_number) is str:
            return os.path.join(dir_html, f'draft-{rfc_number}.html')

    # RFCの取得先URL (XML)
    @staticmethod
    def get_url_rfc_xml(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return f'https://www.rfc-editor.org/rfc/rfc{rfc_number}.xml'

    # RFCの取得先URL (HTML)
    @staticmethod
    def get_url_rfc_html(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return f'https://datatracker.ietf.org/doc/html/rfc{rfc_number}'
        elif type(rfc_number) is str:
            return f'https://datatracker.ietf.org/doc/html/draft-{rfc_number}'

    # RFCの取得先URL (TXT)
    @staticmethod
    def get_url_rfc_txt(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return f'https://www.rfc-editor.org/rfc/rfc{rfc_number}.txt'
        elif type(rfc_number) is str:
            return f'https://www.ietf.org/archive/id/draft-{rfc_number}.txt'

    # RFCの取得先URL (XML)
    def get_url_rfc_xml(rfc_number: int) -> str:
        return f'https://www.rfc-editor.org/rfc/rfc{rfc_number}.xml'

    # RFC Indexの取得先URL (XML)
    @staticmethod
    def get_url_rfc_index_xml():
        return 'https://www.rfc-editor.org/rfc-index.xml'

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

    # HTMLファイルの書き込み
    @staticmethod
    def write_html_file(filepath: str, obj: object):
        FILEMODE = 'w'
        ENCODING = 'utf-8'
        NEWLINE = "\n"
        with open(filepath, FILEMODE, encoding=ENCODING, newline=NEWLINE) as f:
            f.write(obj)

    # HTMLファイルの読み込み
    @staticmethod
    def read_html_file(filepath: str) -> str:
        FILEMODE = 'r'
        ENCODING = 'utf-8'
        with open(filepath, FILEMODE, encoding=ENCODING) as f:
            content = f.read()
            return content



# ------------------------------------------------------------------------------
# https://www.rfc-editor.org/rfc-index.xml

class RfcIndexXmlElem:
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
    OBSOLETES = 'obs'
    OBSOLETED_BY = 'obs_by'
    UPDATES = 'upd'
    UPDATED_BY = 'upd_by'
    CURRENT_STATUS = 'st'
    WG = 'wg'

# ------------------------------------------------------------------------------
# https://www.rfc-editor.org/rfc/rfcXXXX.xml

class RfcXmlElem:
    # level1
    RFC = 'rfc'
    # level2
    FRONT = 'front'
    # level3
    TITLE = 'title'
    ABSTRACT = 'abstract'

class RfcJsonElem:
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

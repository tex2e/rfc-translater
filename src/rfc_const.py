
import os

class RfcFile:
    OUTPUT_HTML_DIR = 'html'
    OUTPUT_DATA_DIR = 'data'
    OUTPUT_DRAFT = 'draft'

    OUTPUT_HTML_INDEX_FILE = os.path.join('html', 'index.html')

    TEMPLATE_HTML_INDEX = os.path.join('templates', 'index.html')
    TEMPLATE_HTML_RFC = os.path.join('templates', 'rfc.html')

    @staticmethod
    def get_dir_data(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return os.path.join(RfcFile.OUTPUT_DATA_DIR, '%04d' % (rfc_number // 1000 % 10 * 1000))
        elif type(rfc_number) is str:
            return os.path.join(RfcFile.OUTPUT_DATA_DIR, RfcFile.OUTPUT_DRAFT)

    @staticmethod
    def get_dir_html(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return os.path.join(RfcFile.OUTPUT_HTML_DIR)
        elif type(rfc_number) is str:
            return os.path.join(RfcFile.OUTPUT_HTML_DIR, RfcFile.OUTPUT_DRAFT)

    @staticmethod
    def get_filepath_json(rfc_number: int | str) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}.json')

    @staticmethod
    def get_filepath_trans_json(rfc_number: int | str) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}-trans.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}-trans.json')

    @staticmethod
    def get_filepath_midway_json(rfc_number: int | str) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}-midway.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}-midway.json')

    @staticmethod
    def get_filepath_summary_json(rfc_number: int | str) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_data, f'rfc{rfc_number}-summary.json')
        elif type(rfc_number) is str:
            return os.path.join(dir_data, f'draft-{rfc_number}-summary.json')

    @staticmethod
    def get_filepath_rfc_html(rfc_number: int | str) -> str:
        dir_html = RfcFile.get_dir_html(rfc_number)
        if type(rfc_number) is int:
            return os.path.join(dir_html, f'rfc{rfc_number}.html')
        elif type(rfc_number) is str:
            return os.path.join(dir_html, f'draft-{rfc_number}.html')

    @staticmethod
    def get_url_rfc_xml(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return f'https://www.rfc-editor.org/rfc/rfc{rfc_number}.xml'

    @staticmethod
    def get_url_rfc_index_xml():
        return 'https://www.rfc-editor.org/rfc-index.xml'

    @staticmethod
    def get_url_rfc_html(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return f'https://datatracker.ietf.org/doc/html/rfc{rfc_number}'
        elif type(rfc_number) is str:
            return f'https://datatracker.ietf.org/doc/html/draft-{rfc_number}'

    @staticmethod
    def get_url_rfc_txt(rfc_number: int | str) -> str:
        if type(rfc_number) is int:
            return f'https://www.rfc-editor.org/rfc/rfc{rfc_number}.txt'
        elif type(rfc_number) is str:
            return f'https://www.ietf.org/archive/id/draft-{rfc_number}.txt'



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
    ABSTRACT = 'abstract'


import os

class RfcFile:
    OUTPUT_HTML_DIR = 'html'
    OUTPUT_DATA_DIR = 'data'

    TEMPLATE_HTML_RFC = 'templates/rfc.html'

    @staticmethod
    def get_dir_data(rfc_number: int) -> str:
        return os.path.join(RfcFile.OUTPUT_DATA_DIR, '%04d' % (rfc_number // 1000 % 10 * 1000))

    @staticmethod
    def get_filepath_json(rfc_number: int) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        return f'{dir_data}/rfc{rfc_number}.json'

    @staticmethod
    def get_filepath_trans_json(rfc_number: int) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        return f'{dir_data}/rfc{rfc_number}-trans.json'

    @staticmethod
    def get_filepath_midway_json(rfc_number: int) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        return f'{dir_data}/rfc{rfc_number}-trans.json'

    @staticmethod
    def get_filepath_summary_json(rfc_number: int) -> str:
        dir_data = RfcFile.get_dir_data(rfc_number)
        return f'{dir_data}/rfc{rfc_number}-summary.json'

    @staticmethod
    def get_filepath_rfc_html(rfc_number: int) -> str:
        return f'{RfcFile.OUTPUT_HTML_DIR}/rfc{rfc_number}.html'

    @staticmethod
    def get_url_rfc_xml(rfc_number: int) -> str:
        return f"https://www.rfc-editor.org/rfc/rfc{rfc_number}.xml"

    @staticmethod
    def get_url_rfc_index_xml():
        return "https://www.rfc-editor.org/rfc-index.xml"


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

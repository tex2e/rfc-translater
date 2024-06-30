
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

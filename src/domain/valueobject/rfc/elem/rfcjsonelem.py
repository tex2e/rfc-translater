
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

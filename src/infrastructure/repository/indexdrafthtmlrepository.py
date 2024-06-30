
from ...domain.models.rfc import RfcFile
from ...domain.repository.iindexdrafthtmlrepository import IIndexDraftHtmlRepository


class IndexDraftHtmlFileRepository(IIndexDraftHtmlRepository):

    def findpath(self) -> str:
        return RfcFile.OUTPUT_HTML_DRAFT_INDEX_FILE

    def save(self, output_string: object) -> None:
        filepath = self.findpath()
        RfcFile.write_html_file(filepath, output_string)  # HTML出力

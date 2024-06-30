
import abc
from ...domain.valueobject.rfc import IRfc
from ...domain.valueobject.rfc import RfcFile


class IIndexHtmlRepository(metaclass=abc.ABCMeta):
    """IndexのHTMLを管理するレポジトリ"""

    @abc.abstractmethod
    def findpath(self, rfc: IRfc) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, rfc: IRfc, obj: object) -> None:
        raise NotImplementedError()


class IndexHtmlFileRepository(IIndexHtmlRepository):

    def findpath(self) -> str:
        return RfcFile.OUTPUT_HTML_INDEX_FILE

    def save(self, output_string: object) -> None:
        filepath = self.findpath()
        RfcFile.write_html_file(filepath, output_string)  # HTML出力

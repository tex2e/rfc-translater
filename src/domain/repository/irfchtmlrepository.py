
import abc
from ..models.rfc import IRfc
from ..models.html import HtmlFile


class IRfcHtmlRepository(metaclass=abc.ABCMeta):
    """RFC翻訳済みHTMLを管理するレポジトリ"""

    @abc.abstractmethod
    def findpath(self, rfc: IRfc) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def find(self, rfc: IRfc) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, rfc: IRfc, obj: object) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(self, rfc: IRfc) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def findall(self) -> list[HtmlFile]:
        raise NotImplementedError()

    @abc.abstractmethod
    def findalldraft(self) -> list[HtmlFile]:
        raise NotImplementedError()

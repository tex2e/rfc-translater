
import abc
from ..models.rfc import IRfc


class IIndexDraftHtmlRepository(metaclass=abc.ABCMeta):
    """Draft版IndexのHTMLを管理するレポジトリ"""

    @abc.abstractmethod
    def findpath(self, rfc: IRfc) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, rfc: IRfc, obj: object) -> None:
        raise NotImplementedError()

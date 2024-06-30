
import abc
from ..models.rfc import IRfc


class IIndexHtmlRepository(metaclass=abc.ABCMeta):
    """IndexのHTMLを管理するレポジトリ"""

    @abc.abstractmethod
    def findpath(self, rfc: IRfc) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, rfc: IRfc, obj: object) -> None:
        raise NotImplementedError()

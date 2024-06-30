
import abc
from ..models.rfc import IRfc


class IRfcStatusRepository(metaclass=abc.ABCMeta):
    """全RFCの状態を格納するJSONを管理するレポジトリ"""

    @abc.abstractmethod
    def findpath(self, rfc: IRfc) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, obj: object) -> None:
        raise NotImplementedError()

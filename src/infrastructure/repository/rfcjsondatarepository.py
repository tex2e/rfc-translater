
import os
import abc
from ...domain.valueobject.rfc import IRfc
from ...domain.services.rfcfile import RfcFile


class IRfcJsonDataRepository(metaclass=abc.ABCMeta):
    """RFC取得データJSONを管理するレポジトリ"""

    @abc.abstractmethod
    def findpath(self, rfc: IRfc) -> str:
        """JSONファイルのパスを取得する"""
        raise NotImplementedError()

    @abc.abstractmethod
    def find(self, rfc: IRfc) -> object:
        """JSONファイルが存在するとき、その内容を取得する"""
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, rfc: IRfc, obj: object) -> None:
        """JSONファイルを保存する"""
        raise NotImplementedError()

    @abc.abstractmethod
    def delete(self, rfc: IRfc) -> bool:
        """JSONファイルを削除する"""
        raise NotImplementedError()


class RfcJsonDataFileRepository(IRfcJsonDataRepository):

    def findpath(self, rfc: IRfc) -> str:
        return RfcFile.get_filepath_data_json(rfc)

    def find(self, rfc: IRfc) -> object:
        filepath = self.findpath(rfc)
        if not os.path.isfile(filepath):
            return None
        obj = RfcFile.read_json_file(filepath)
        return obj

    def save(self, rfc: IRfc, obj: object) -> None:
        filepath = self.findpath(rfc)
        RfcFile.write_json_file(filepath, obj)

    def delete(self, rfc: IRfc) -> bool:
        filepath = self.findpath(rfc)
        if os.path.isfile(filepath):
            os.remove(filepath)
            return True
        return False

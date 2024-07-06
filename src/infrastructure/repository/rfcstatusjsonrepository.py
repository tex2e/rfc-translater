
import abc
from ...domain.valueobject.rfc import IRfc
from ...domain.services.rfcfile import RfcFile


class IRfcStatusRepository(metaclass=abc.ABCMeta):
    """全RFCの状態を格納するJSONを管理するレポジトリ"""

    @abc.abstractmethod
    def findpath(self, rfc: IRfc) -> str:
        """JSONファイルのパスを取得する"""
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, obj: object) -> None:
        """JSONファイルに保存する"""
        raise NotImplementedError()


class RfcStatusJsonFileRepository(IRfcStatusRepository):

    def findpath(self) -> str:
        return RfcFile.OUTPUT_HTML_RFC_LIST_JSON_FILE

    def save(self, output_string: object) -> None:
        filepath = self.findpath()
        RfcFile.write_json_file(filepath, output_string)  # JSON出力

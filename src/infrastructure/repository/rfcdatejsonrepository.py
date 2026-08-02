
import abc
from ...domain.services.rfcfile import RfcFile


class IRfcDateRepository(metaclass=abc.ABCMeta):
    """全RFCの発行年月を格納するJSONを管理するレポジトリ"""

    @abc.abstractmethod
    def findpath(self) -> str:
        """JSONファイルのパスを取得する"""
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, obj: object) -> None:
        """JSONファイルに保存する"""
        raise NotImplementedError()


class RfcDateJsonFileRepository(IRfcDateRepository):

    def findpath(self) -> str:
        return RfcFile.OUTPUT_HTML_RFC_DATE_JSON_FILE

    def save(self, output_string: object) -> None:
        filepath = self.findpath()
        RfcFile.write_json_file(filepath, output_string)  # JSON出力

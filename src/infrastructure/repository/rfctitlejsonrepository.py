
import abc
from ...domain.services.rfcfile import RfcFile


class IRfcTitleRepository(metaclass=abc.ABCMeta):
    """全RFCの日本語タイトルを格納するJSONを管理するレポジトリ"""

    @abc.abstractmethod
    def findpath(self) -> str:
        """JSONファイルのパスを取得する"""
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, obj: object) -> None:
        """JSONファイルに保存する"""
        raise NotImplementedError()


class RfcTitleJsonFileRepository(IRfcTitleRepository):

    def findpath(self) -> str:
        return RfcFile.OUTPUT_HTML_RFC_TITLE_JSON_FILE

    def save(self, output_string: object) -> None:
        filepath = self.findpath()
        RfcFile.write_json_file(filepath, output_string)  # JSON出力

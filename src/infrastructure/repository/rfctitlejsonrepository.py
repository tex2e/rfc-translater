
import abc
import os
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
        self.save_shards(output_string)

    @staticmethod
    def save_shards(obj: dict) -> None:
        """RFCリンクのツールチップで全件（約800KB）を取得しなくて済むように、RFC番号の千の位ごとに分割して出力する。
        （例: RFC 8446 → html/data-rfc-title/8.json）"""
        shards = {}
        for rfc_number, title in obj.items():
            shards.setdefault(int(rfc_number) // 1000, {})[rfc_number] = title
        for shard_number, shard in shards.items():
            filepath = os.path.join(RfcFile.OUTPUT_HTML_RFC_TITLE_SHARD_DIR, f'{shard_number}.json')
            RfcFile.write_json_file(filepath, shard)


import abc
import glob
import json
import os
from ...domain.valueobject.rfc import IRfc, Rfc
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

    @abc.abstractmethod
    def save_errata(self, errata_by_rfc: dict) -> None:
        """RFCごとのErrataの一覧をJSONファイルに保存する"""
        raise NotImplementedError()

    @abc.abstractmethod
    def save_errata_details(self, details_by_rfc: dict) -> None:
        """RFCごとのErrataの原文・修正文・補足をJSONファイルに保存する"""
        raise NotImplementedError()


class RfcStatusJsonFileRepository(IRfcStatusRepository):

    def findpath(self) -> str:
        return RfcFile.OUTPUT_HTML_RFC_LIST_JSON_FILE

    def save(self, output_string: object) -> None:
        filepath = self.findpath()
        RfcFile.write_json_file(filepath, output_string)  # JSON出力
        self.save_shards(output_string)

    @staticmethod
    def save_shards(obj: dict) -> None:
        """RFCのページ表示時に全件（約1MB）を取得しなくて済むように、RFC番号の千の位ごとに分割して出力する。
        （例: RFC 8446 → html/data-rfc-list/8.json）"""
        shards = {}
        for rfc_number, datum in obj.items():
            shards.setdefault(int(rfc_number) // 1000, {})[rfc_number] = datum
        for shard_number, shard in shards.items():
            filepath = os.path.join(RfcFile.OUTPUT_HTML_RFC_LIST_SHARD_DIR, f'{shard_number}.json')
            RfcFile.write_json_file(filepath, shard)

    def save_errata(self, errata_by_rfc: dict) -> None:
        """RFCごとのErrataの一覧を、RFC番号の千の位ごとに分割して出力する。
        （例: RFC 8446 → html/data-rfc-errata/8.json）
        1件ごとに改行するとファイルが大きくなるため、1つのRFCを1行に収める。"""
        shards = {}
        for rfc_number, entries in errata_by_rfc.items():
            shards.setdefault(int(rfc_number) // 1000, {})[rfc_number] = entries
        os.makedirs(RfcFile.OUTPUT_HTML_RFC_ERRATA_SHARD_DIR, exist_ok=True)
        for shard_number, shard in shards.items():
            filepath = os.path.join(RfcFile.OUTPUT_HTML_RFC_ERRATA_SHARD_DIR, f'{shard_number}.json')
            lines = [f'{json.dumps(k)}:{json.dumps(v, ensure_ascii=False, separators=(",", ":"))}'
                     for k, v in shard.items()]
            with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
                f.write('{\n' + ',\n'.join(lines) + '\n}\n')

    def save_errata_details(self, details_by_rfc: dict) -> None:
        """翻訳済みのRFCについて、Errataの原文・修正文・補足を data/N000/rfcNXXX-errata.json に保存する。
        Errataがなくなった（すべて却下された）RFCのファイルは削除する。"""
        written = set()
        for rfc_number, entries in details_by_rfc.items():
            rfc = Rfc(rfc_number)
            if not os.path.exists(RfcFile.get_filepath_html_rfc(rfc)):
                continue  # 翻訳していないRFCのページはないため、ファイルも作らない
            filepath = RfcFile.get_filepath_data_errata_json(rfc)
            RfcFile.write_json_file(filepath, {'number': int(rfc_number), 'errata': entries})
            written.add(os.path.normpath(filepath))
        for filepath in glob.glob(RfcFile.GLOB_DATA_ERRATA_JSON_FILE):
            if os.path.normpath(filepath) not in written:
                os.remove(filepath)

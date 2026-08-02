
import os
import re
import abc
import glob
from ...domain.valueobject.rfc import IRfc, RfcJsonElem
from ...domain.services.rfcfile import RfcFile


class IRfcJsonTransRepository(metaclass=abc.ABCMeta):
    """RFC翻訳データJSONを管理するレポジトリ"""

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

    @abc.abstractmethod
    def get_title(self, rfc: IRfc) -> str:
        """JSONの内容からRFCのタイトルを取得する"""
        raise NotImplementedError()

    @abc.abstractmethod
    def findall_titles_ja(self) -> dict[str, str]:
        """全RFCの日本語タイトルを取得する"""
        raise NotImplementedError()


class RfcJsonTransFileRepository(IRfcJsonTransRepository):

    def findpath(self, rfc: IRfc) -> str:
        return RfcFile.get_filepath_data_trans_json(rfc)

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

    def get_title(self, rfc: IRfc) -> str:
        """対象RFCのタイトルを取得"""
        obj = self.find(rfc)
        # 翻訳済みRFC (json) の読み込み
        rfc_title = None
        if obj and obj['title'] and obj['title']['text']:
            rfc_title = obj['title']['text']
        return rfc_title

    def findall_titles_ja(self) -> dict[str, str]:
        """全RFCの日本語タイトルを {RFC番号: タイトル} で取得"""
        titles = {}
        for filepath in glob.glob(RfcFile.GLOB_DATA_TRANS_JSON_FILE):
            m = re.match(r'rfc(\d+)-trans\.json$', os.path.basename(filepath))
            if not m:
                continue
            rfc_number = int(m[1])
            if rfc_number < 2220:  # 著作権の関係から RFC 2220 以降のみを対象とする
                continue
            obj = RfcFile.read_json_file(filepath)
            title_ja = obj.get(RfcJsonElem.TITLE, {}).get(RfcJsonElem.Title.JA)
            if not title_ja:
                continue
            titles[str(rfc_number)] = title_ja
        return titles

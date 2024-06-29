
import os
from ...domain.models.rfc.rfc_const import RfcFile
from ...domain.models.rfc import IRfc
from ...domain.repository.irfcjsontransrepository import IRfcJsonTransRepository


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
        rfc_title = obj['title']['text']
        return rfc_title

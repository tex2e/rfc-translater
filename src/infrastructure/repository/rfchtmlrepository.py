
import os
from ...domain.models.rfc import RfcFile, IRfc
from ...domain.repository.irfchtmlrepository import IRfcHtmlRepository


class RfcHtmlFileRepository(IRfcHtmlRepository):

    def findpath(self, rfc: IRfc) -> str:
        return RfcFile.get_filepath_html_rfc(rfc)

    def find(self, rfc: IRfc) -> str:
        filepath = self.findpath(rfc)
        if not os.path.isfile(filepath):
            return None
        obj = RfcFile.read_html_file(filepath)  # HTML入力
        return obj

    def save(self, rfc: IRfc, output_string: object) -> None:
        filepath = self.findpath(rfc)
        RfcFile.write_html_file(filepath, output_string)  # HTML出力

    def delete(self, rfc: IRfc) -> bool:
        filepath = self.findpath(rfc)
        if os.path.isfile(filepath):
            os.remove(filepath)
            return True
        return False

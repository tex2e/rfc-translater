
import os
from ...domain.models.rfc import RfcFile, IRfc
from ...domain.repository.irfcjsondatasummaryrepository import IRfcJsonDataSummaryRepository


class RfcJsonDataSummaryFileRepository(IRfcJsonDataSummaryRepository):

    def findpath(self, rfc: IRfc) -> str:
        return RfcFile.get_filepath_data_summary_json(rfc)

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

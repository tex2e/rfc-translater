
import os
from ...rfc_const import RfcFile
from ...domain.models.rfc import IRfc
from ...domain.repository.irfcjsonplainrepository import IRfcJsonPlainRepository


class RfcJsonPlainFileRepository(IRfcJsonPlainRepository):

    def find(self, rfc: IRfc):
        filepath = RfcFile.get_filepath_data_json(rfc)
        if not os.path.isfile(filepath):
            return None
        obj = RfcFile.read_json_file(filepath)
        return obj

    def save(self, rfc: IRfc, obj):
        output_file = RfcFile.get_filepath_data_json(rfc)
        RfcFile.write_json_file(output_file, obj)

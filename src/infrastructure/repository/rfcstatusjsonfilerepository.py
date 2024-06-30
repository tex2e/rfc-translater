
from ...domain.models.rfc import RfcFile
from ...domain.repository.irfcstatusjsonrepository import IRfcStatusRepository


class RfcStatusJsonRepository(IRfcStatusRepository):

    def findpath(self) -> str:
        return RfcFile.OUTPUT_HTML_RFC_LIST_JSON_FILE

    def save(self, output_string: object) -> None:
        filepath = self.findpath()
        RfcFile.write_json_file(filepath, output_string)  # JSON出力

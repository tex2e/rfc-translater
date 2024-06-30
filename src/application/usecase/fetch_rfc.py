
from ...domain.valueobject.rfc import IRfc, Rfc, RfcDraft
from ...infrastructure.repository.rfcjsondatarepository import IRfcJsonDataRepository
from .fetch_rfc_txt import fetch_rfc_txt
from .fetch_rfc_xml import fetch_rfc_xml


def fetch_rfc(rfc: IRfc,
              rfc_json_plain_file_repo: IRfcJsonDataRepository,
              args):
    """RFCの取得処理"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_plain_file_repo, IRfcJsonDataRepository)

    if isinstance(rfc, RfcDraft):
        fetch_rfc_txt(rfc, rfc_json_plain_file_repo, args)
    elif isinstance(rfc, Rfc):
        if (int(rfc.get_id()) >= 8650) and (not args.txt):
            fetch_rfc_xml(rfc, rfc_json_plain_file_repo, args)
        else:
            fetch_rfc_txt(rfc, rfc_json_plain_file_repo, args)

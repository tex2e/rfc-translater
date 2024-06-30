
from ...domain.valueobject.rfc import IRfc, Rfc, RfcDraft
from ...infrastructure.repository.rfcjsondatarepository import IRfcJsonDataRepository
from ...infrastructure.apiclient.rfcapiclient import IRfcApiClient
from ...application.usecase.fetch_rfc_txt import fetch_rfc_txt
from ...application.usecase.fetch_rfc_xml import fetch_rfc_xml


def fetch_rfc(rfc: IRfc,
              rfc_json_plain_file_repo: IRfcJsonDataRepository,
              rfc_api: IRfcApiClient,
              args):
    """RFCの取得処理"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_plain_file_repo, IRfcJsonDataRepository)
    assert isinstance(rfc_api, IRfcApiClient)

    if isinstance(rfc, RfcDraft):
        fetch_rfc_txt(rfc, rfc_json_plain_file_repo, rfc_api, args)
    elif isinstance(rfc, Rfc):
        if (int(rfc.get_id()) >= 8650) and (not args.txt):
            fetch_rfc_xml(rfc, rfc_json_plain_file_repo, rfc_api, args)
        else:
            fetch_rfc_txt(rfc, rfc_json_plain_file_repo, rfc_api, args)

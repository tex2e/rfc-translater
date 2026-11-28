
import abc
from ...domain.services.rfcutils import RfcUtils
from ...domain.services.rfcfile import RfcFile


class IRfcIndexApiClient(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def fetch_index_xml(self):
        """RFCのIndexページを取得するAPI"""
        raise NotImplementedError()

    @abc.abstractmethod
    def fetch_errata_json(self) -> list:
        """全RFCのErrata一覧を取得するAPI"""
        raise NotImplementedError()


class RfcIndexHttpApiClient(IRfcIndexApiClient):

    def fetch_index_xml(self):
        url = RfcFile.get_url_rfc_index_xml()
        page = RfcUtils.fetch_url(url)
        return page

    def fetch_errata_json(self) -> list:
        url = RfcFile.get_url_errata_json()
        page = RfcUtils.fetch_url(url)
        page.raise_for_status()
        return page.json()

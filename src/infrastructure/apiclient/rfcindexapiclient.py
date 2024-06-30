
import abc
from ...domain.valueobject.rfc import RfcFile
from ...domain.services.rfc_utils import RfcUtils


class IRfcIndexApiClient(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def fetch_index_xml(self):
        """RFCのIndexページを取得するAPI"""
        raise NotImplementedError()


class RfcIndexHttpApiClient(IRfcIndexApiClient):

    def fetch_index_xml(self):
        url = RfcFile.get_url_rfc_index_xml()
        page = RfcUtils.fetch_url(url)
        return page

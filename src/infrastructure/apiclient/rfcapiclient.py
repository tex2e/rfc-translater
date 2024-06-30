
import abc
from ...domain.valueobject.rfc import IRfc
from ...domain.services.rfcutils import RfcUtils
from ...domain.services.rfcfile import RfcFile


class IRfcApiClient(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def fetch_html(self, rfc: IRfc) -> object:
        """RFC (HTML版) を取得するAPI"""
        raise NotImplementedError()

    @abc.abstractmethod
    def fetch_txt(self, rfc: IRfc) -> object:
        """RFC (TXT版) を取得するAPI"""
        raise NotImplementedError()

    @abc.abstractmethod
    def fetch_xml(self, rfc: IRfc) -> object:
        """RFC (XML版) を取得するAPI"""
        raise NotImplementedError()


class RfcHttpApiClient(IRfcApiClient):

    def fetch_html(self, rfc: IRfc):
        assert isinstance(rfc, IRfc)

        url = RfcFile.get_url_rfc_html(rfc)
        page = RfcUtils.fetch_url(url)
        return page

    def fetch_txt(self, rfc: IRfc):
        assert isinstance(rfc, IRfc)

        url = RfcFile.get_url_rfc_txt(rfc)
        page = RfcUtils.fetch_url(url)
        return page

    def fetch_xml(self, rfc: IRfc):
        assert isinstance(rfc, IRfc)

        url = RfcFile.get_url_rfc_xml(rfc)
        page = RfcUtils.fetch_url(url)
        return page

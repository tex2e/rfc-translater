
import abc
from ..models.rfc import IRfc


class IRfcJsonPlainRepository(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def find(self, rfc: IRfc):
        raise NotImplementedError()

    @abc.abstractmethod
    def save(self, rfc: IRfc, obj):
        raise NotImplementedError()


import abc


class IRfc(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def get_id(self) -> str:
        raise NotImplementedError()

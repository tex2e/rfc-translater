
from .irfc import IRfc


class Rfc(IRfc):

    def __init__(self, number: str) -> None:
        assert isinstance(number, str)
        self.number = number

    def get_id(self) -> str:
        return self.number

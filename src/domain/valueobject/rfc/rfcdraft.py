
from .irfc import IRfc


class RfcDraft(IRfc):

    def __init__(self, draftname: str) -> None:
        assert isinstance(draftname, str)
        self.draftname = draftname

    def get_id(self) -> str:
        return self.draftname

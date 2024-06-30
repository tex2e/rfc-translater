
class HtmlFile:
    """HTMLファイルの情報を格納するDTO"""

    def __init__(self, filenum, filepath, title) -> None:
        self.filenum = filenum
        self.filepath = filepath
        self.title = title

    def get_id(self):
        return self.filenum

    def get_filepath(self):
        return self.filepath

    def get_title(self):
        return self.title


# RFC取得先リンクにデータが存在しないときは、RFCNotFoundエラーを投げること。
# このエラーを投げると、html/rfcXXXX-not-found.html が作成される。
class RFCNotFoundException(Exception):
    pass

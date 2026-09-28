import sys
import unittest

sys.path.insert(0, "tools")
from fix_translation import fix_necessity_translation, to_beki, to_nakereba  # noqa: E402
from lint_translation import check_necessity_translation  # noqa: E402


class TestNecessityTranslation(unittest.TestCase):
    def test_lint_detects_necessity_for_must_and_should(self):
        self.assertEqual(check_necessity_translation("It MUST send X.", "Xを送信する必要があります。")[0], "W012")
        self.assertEqual(check_necessity_translation("It SHOULD send X.", "Xを送信する必要があります。")[0], "W012")
        # 正しい訳語があれば対象外。MAY 等の強度も対象外
        self.assertIsNone(check_necessity_translation("It MUST send X.", "Xを送信しなければなりません。"))
        self.assertIsNone(check_necessity_translation("It MAY send X.", "Xを送信する必要がある場合があります。"))

    def test_to_nakereba(self):
        cases = {
            "送信する": "送信しなければなりません",
            "含める": "含めなければなりません",       # 一段
            "できる": "できなければなりません",
            "含んでいる": "含んでいなければなりません",
            "使う": "使わなければなりません",         # 五段
            "示す": "示さなければなりません",
            "なる": "ならなければなりません",
            "ゼロである": "ゼロでなければなりません",
        }
        for pre, expected in cases.items():
            self.assertEqual(to_nakereba(pre), expected, pre)
        # 漢字 + る (送る/着る) は五段か一段か決まらない。否定・ある は対象外
        for pre in ("送る", "着る", "送信しない", "ある"):
            self.assertIsNone(to_nakereba(pre), pre)

    def test_to_beki(self):
        self.assertEqual(to_beki("送信する"), "送信すべきです")
        self.assertEqual(to_beki("送る"), "送るべきです")
        self.assertIsNone(to_beki("送信しない"))

    def test_fix_rewrites_and_annotates(self):
        self.assertEqual(
            fix_necessity_translation("The client MUST send X.", "クライアントはXを送信する必要があります。"),
            "クライアントはXを送信しなければなりません (MUST)。")
        self.assertEqual(
            fix_necessity_translation("Servers SHOULD include X.", "サーバーはXを含める必要があります（SHOULD）。"),
            "サーバーはXを含めるべきです (SHOULD)。")

    def test_fix_multi_sentence_aligned(self):
        self.assertEqual(
            fix_necessity_translation(
                "The policyIdentifier MUST be globally unique. Possible types of identifiers include:",
                "policyIdentifierはグローバルに一意である必要があります。可能な識別子のタイプは次のとおりです。"),
            "policyIdentifierはグローバルに一意でなければなりません (MUST)。可能な識別子のタイプは次のとおりです。")
        self.assertEqual(
            fix_necessity_translation(
                "The server sends the Token back. This message MUST be sent from port PT towards port CT.",
                "サーバーはトークンを送り返します。このメッセージは、ポートPTからポートCTに送信する必要があります。"),
            "サーバーはトークンを送り返します。このメッセージは、ポートPTからポートCTに送信しなければなりません (MUST)。")

    def test_fix_multi_sentence_skips_misaligned(self):
        # 文の数が違う
        self.assertIsNone(fix_necessity_translation(
            "A is sent. B MUST be sent. C is fine.",
            "Aが送信され、Bを送信する必要があります。Cは問題ありません。"))
        # キーワードの文と「必要があ」の文の位置が違う
        self.assertIsNone(fix_necessity_translation(
            "B MUST be sent. C is fine.",
            "Bが送信されます。Cを確認する必要があります。"))

    def test_fix_skips_uncertain(self):
        self.assertIsNone(fix_necessity_translation("It MUST send X.", "Xを送る必要があります。"))
        # 文中に既に注釈がある (キーワードの訳は別の節)
        self.assertIsNone(fix_necessity_translation(
            "The router SHALL construct X and return it.",
            "ルーターはXを作成し（SHALL）、それを返す必要があります。"))
        # 小文字の need/should の節が文末にある
        self.assertIsNone(fix_necessity_translation(
            "The header SHOULD be sent, but agents need to be prepared to receive it.",
            "ヘッダーを送信する必要がありますが、エージェントは受信できるように準備する必要があります。"))
        self.assertIsNone(fix_necessity_translation(
            "The service SHOULD be granted, and the request should be deleted.",
            "サービスを許可し、リクエストを削除する必要があります。"))
        # 種類の違う注釈が付いているものは触らない
        self.assertIsNone(fix_necessity_translation("It MUST send X.", "Xを送信する必要があります (SHOULD)。"))


if __name__ == "__main__":
    unittest.main()

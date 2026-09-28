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

    def test_fix_skips_uncertain(self):
        self.assertIsNone(fix_necessity_translation("It MUST send X.", "Xを送る必要があります。"))
        self.assertIsNone(fix_necessity_translation(
            "It MUST send X. Y is fine.", "Xを送信する必要があります。Yは問題ありません。"))
        # 種類の違う注釈が付いているものは触らない
        self.assertIsNone(fix_necessity_translation("It MUST send X.", "Xを送信する必要があります (SHOULD)。"))


if __name__ == "__main__":
    unittest.main()

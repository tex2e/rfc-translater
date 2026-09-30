import sys
import unittest

sys.path.insert(0, "tools")
from fix_translation import fix_rfc2119_annotation  # noqa: E402


class TestFixRfc2119Annotation(unittest.TestCase):
    def test_appends_annotation_to_final_predicate(self):
        self.assertEqual(
            fix_rfc2119_annotation("The client MUST send X.", "クライアントはXを送信しなければなりません。"),
            "クライアントはXを送信しなければなりません (MUST)。")
        self.assertEqual(
            fix_rfc2119_annotation("Servers SHOULD NOT send X.", "サーバーはXを送信すべきではありません。"),
            "サーバーはXを送信すべきではありません (SHOULD NOT)。")

    def test_uses_original_keyword(self):
        self.assertEqual(
            fix_rfc2119_annotation("It SHALL NOT be sent.", "それは送信されないものとします。"),
            "それは送信されないものとします (SHALL NOT)。")

    def test_bullet_without_period(self):
        self.assertEqual(
            fix_rfc2119_annotation("- Senders MAY include X", "- 送信者はXを含めることができます"),
            "- 送信者はXを含めることができます (MAY)")

    def test_skips_ambiguous_predicates(self):
        # 「必要があります」は MUST/SHOULD、「ないでください」は MUST NOT/SHOULD NOT の両方に読める
        self.assertIsNone(fix_rfc2119_annotation("It MUST send X.", "Xを送信する必要があります。"))
        self.assertIsNone(fix_rfc2119_annotation("It MUST NOT send X.", "Xを送信しないでください。"))

    def test_skips_strength_mismatch(self):
        # "MUST be absent" を禁止形で訳した文など、述語の強度がキーワードと合わない
        self.assertIsNone(fix_rfc2119_annotation("X MUST be absent.", "Xは存在してはいけません。"))
        self.assertIsNone(fix_rfc2119_annotation("It MUST be sent.", "それは送信されないものとします。"))

    def test_skips_multiple_sentences_or_keywords(self):
        self.assertIsNone(fix_rfc2119_annotation(
            "A MAY be used. B is fine.", "Aを使用できます。Bは問題ありません。"))
        self.assertIsNone(fix_rfc2119_annotation(
            "It MUST do X and MAY do Y.", "Xを行い、Yを行ってもよい。"))

    def test_skips_lowercase_modal(self):
        # 文末の述語が小文字の must の節の訳である可能性がある
        self.assertIsNone(fix_rfc2119_annotation(
            "Clients MAY cache X, but they must discard it after use.",
            "クライアントはXをキャッシュでき、使用後は破棄しなければなりません。"))

    def test_skips_when_already_annotated(self):
        self.assertIsNone(fix_rfc2119_annotation(
            "It MUST send X.", "Xを送信しなければなりません (MUST)。"))


if __name__ == "__main__":
    unittest.main()

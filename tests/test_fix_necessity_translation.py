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
        # 「推奨されます」「推奨します」は推奨の強度を一意に表すので対象外
        self.assertIsNone(check_necessity_translation(
            "X is RECOMMENDED if Y needs Z.", "YがZを必要とする場合は、Xが推奨されます (RECOMMENDED)。Yは設定する必要があります。"))
        self.assertIsNotNone(check_necessity_translation(
            "It MUST send X.", "Xを推奨しますが、送信する必要があります。"))
        # 「必須です (REQUIRED)」「必須 (REQUIRED)」は必須の強度を一意に表すので対象外
        self.assertIsNone(check_necessity_translation(
            "Support for X is REQUIRED.", "Yを問い合わせる必要があります。Xのサポートは必須です (REQUIRED)。"))
        self.assertIsNone(check_necessity_translation(
            "[REQUIRED as follows]", "[次のとおり必須 (REQUIRED)：送信する必要がある]"))
        self.assertIsNotNone(check_necessity_translation(
            "It MUST send X.", "不必須ですが、送信する必要があります。"))

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
            "送る": "送らなければなりません",         # 漢字 + る (辞書で型が決まるもの)
            "見る": "見なければなりません",
            "互換性がある": "互換性がなければなりません",
            "ディレクトリにある": "ディレクトリになければなりません",
        }
        for pre, expected in cases.items():
            self.assertEqual(to_nakereba(pre), expected, pre)
        # 辞書にない漢字 + る (要る/居る) は型が決まらない。否定・単独の「ある」は対象外
        for pre in ("要る", "居る", "送信しない", "ある"):
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

    def test_fix_multi_sentence_unique(self):
        # 文の数が違っても、原文・訳文とも規範表現が1か所だけで位置も合えば直す
        self.assertEqual(fix_necessity_translation(
            "A is sent. B MUST be sent. C is fine.",
            "Aが送信され、Bを送信する必要があります。Cは問題ありません。"),
            "Aが送信され、Bを送信しなければなりません (MUST)。Cは問題ありません。")

    def test_fix_multi_sentence_skips_misaligned(self):
        # キーワードの文と「必要があ」の文の位置が違う (訳抜けの疑い)
        self.assertIsNone(fix_necessity_translation(
            "B MUST be sent. C is fine.",
            "Bが送信されます。Cを確認する必要があります。"))
        # 文の数が違い、訳文に別の規範表現がある
        self.assertIsNone(fix_necessity_translation(
            "A is sent. B MUST be sent. C is fine.",
            "Aは送信してください。Bを送信する必要があります。"))
        # 原文に「必要があります」と訳されやすい語 (ensure) がある
        self.assertIsNone(fix_necessity_translation(
            "A is sent. B MUST be sent. Ensure C.",
            "Aが送信され、Bが送信されます。Cを確認する必要があります。"))

    def test_fix_renyo(self):
        self.assertEqual(
            fix_necessity_translation(
                "The Reserved field MUST be set to zero, and receivers ignore it on receipt.",
                "予約フィールドはゼロに設定する必要があり、受信者は受信時にそれを無視します。"),
            "予約フィールドはゼロに設定しなければならず (MUST)、受信者は受信時にそれを無視します。")
        self.assertEqual(
            fix_necessity_translation(
                "Implementations SHOULD log the event, and the log is kept for a day.",
                "実装はイベントを記録する必要があり、ログは1日保持されます。"),
            "実装はイベントを記録すべきであり (SHOULD)、ログは1日保持されます。")
        # 後続の節に規範表現があると、どの節がキーワードの訳か決まらない
        self.assertIsNone(fix_necessity_translation(
            "X MUST be set to zero and ignored by receivers.",
            "Xはゼロに設定する必要があり、受信者は無視しなければなりません。"))

    def test_fix_keeps_trailing_notes(self):
        # 述語の後の括弧書き・引用・コロン・「が、」は残して述語だけ直す
        self.assertEqual(fix_necessity_translation(
            "C MUST send X directly (see Section 3).",
            "CはXを直接送信する必要があります（詳細については、セクション3を参照してください）。"),
            "CはXを直接送信しなければなりません (MUST)（詳細については、セクション3を参照してください）。")
        self.assertEqual(fix_necessity_translation("It MUST cut X [RFC1234].", "Xを切る必要があります [RFC1234]。"),
                         "Xを切らなければなりません (MUST) [RFC1234]。")
        self.assertEqual(fix_necessity_translation("A peer SHOULD respond with one of the following:",
                                                   "ピアは次のいずれかで応答する必要があります："),
                         "ピアは次のいずれかで応答すべきです (SHOULD)：")
        self.assertEqual(fix_necessity_translation("It MUST return X, but it has Y.",
                                                   "Xを返す必要がありますが、Yを備えています。"),
                         "Xを返さなければなりません (MUST) が、Yを備えています。")

    def test_fix_skips_uncertain(self):
        self.assertIsNone(fix_necessity_translation("It MUST send X.", "Xを要る必要があります。"))
        # 述語の後の括弧書きに規範表現がある (括弧内が別の規範の訳かもしれない)
        self.assertIsNone(fix_necessity_translation(
            "It MUST get confirmation (or not send MDN).",
            "確認を取得する必要があります（またはMDNを送信しないでください）。"))
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

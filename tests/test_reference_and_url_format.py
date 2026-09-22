import sys
from pathlib import Path
import unittest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from lint_translation import (  # noqa: E402
    check_reference_author_format,
    check_url_format,
    fix_url_format,
    update_reference_section_state,
)


class TestReferenceAndUrlFormat(unittest.TestCase):
    def test_reference_author_punctuation_restore(self):
        en = '[RFC2119] Bradner, S., "Key words for use in RFCs to Indicate Requirement Levels", BCP 14, RFC 2119, March 1997.'
        ja = '[RFC2119] Bradner、S。、「要件レベルを示すためにRFCで使用するためのキーワード」、BCP 14、RFC 2119、1997年3月。'
        res = check_reference_author_format(en, ja, in_reference_section=True)
        self.assertIsNotNone(res)
        en_authors, ja_authors, fixed_ja = res
        self.assertEqual(en_authors, "Bradner, S.")
        self.assertEqual(ja_authors, "Bradner、S。")
        self.assertEqual(fixed_ja, '[RFC2119] Bradner, S.、「要件レベルを示すためにRFCで使用するためのキーワード」、BCP 14、RFC 2119、1997年3月。')

    def test_reference_author_translated_name_restore(self):
        en = '[RFC8446] Rescorla, E., "The Transport Layer Security (TLS) Protocol Version 1.3", RFC 8446, August 2018.'
        ja = '[RFC8446] レスコルラ、E。、「トランスポート層セキュリティ（TLS）プロトコルバージョン1.3」、RFC 8446、2018年8月。'
        res = check_reference_author_format(en, ja, in_reference_section=True)
        self.assertIsNotNone(res)
        en_authors, ja_authors, fixed_ja = res
        self.assertEqual(en_authors, "Rescorla, E.")
        self.assertIn("Rescorla, E.", fixed_ja)

    def test_body_mention_not_detected_as_reference(self):
        en = '[RFC7489] defined an Organizational Domain as "The domain that was registered with a domain name registrar".'
        ja = '[RFC7489] は、組織ドメインを「ドメイン名レジストラに登録されたドメイン」と定義しました。'
        # セクション内であっても、動詞・助詞チェックにより除外される
        res = check_reference_author_format(en, ja, in_reference_section=True)
        self.assertIsNone(res)
        # セクション外なら当然除外される
        res = check_reference_author_format(en, ja, in_reference_section=False)
        self.assertIsNone(res)

    def test_reference_section_state_machine(self):
        state = False
        # 見出し: 1. Introduction
        state = update_reference_section_state(state, "1. Introduction", is_section_title=True)
        self.assertFalse(state)

        # 見出し: 8. References
        state = update_reference_section_state(state, "8. References", is_section_title=True)
        self.assertTrue(state)

        # 本文段落（セクション状態維持）
        state = update_reference_section_state(state, "[RFC2119] Bradner, S.", is_section_title=False)
        self.assertTrue(state)

        # 見出し: 9. Security Considerations（終了）
        state = update_reference_section_state(state, "9. Security Considerations", is_section_title=True)
        self.assertFalse(state)

    def test_url_colon_and_spacing_fix(self):
        cases = [
            ("https：//www.example.com", "https://www.example.com"),
            ("http ：//www.example.com", "http://www.example.com"),
            ("<https://www.example.com/foo.html >", "<https://www.example.com/foo.html>"),
            ("<https ：//www.example.com>", "<https://www.example.com>"),
        ]
        for bad, expected in cases:
            en = f"See <{expected}>."
            ja = f"{bad} を参照してください。"
            self.assertIsNotNone(check_url_format(en, ja))
            fixed = fix_url_format(en, ja)
            self.assertIn(expected, fixed)


if __name__ == "__main__":
    unittest.main()

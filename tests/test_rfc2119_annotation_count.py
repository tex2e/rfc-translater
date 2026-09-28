import sys
import unittest

sys.path.insert(0, "tools")
from lint_translation import (  # noqa: E402
    check_rfc2119_annotation_count,
    count_rfc2119_annotations,
    count_rfc2119_keywords,
)


class TestRfc2119AnnotationCount(unittest.TestCase):
    def test_count_keywords_excludes_quoted_and_referential(self):
        en = 'Use "MUST" here; this violates a SHOULD in Section 3, and it MAY fail.'
        self.assertEqual(count_rfc2119_keywords(en), {"MAY": 1})

    def test_count_keywords_negation_variants(self):
        en = "It MUST also not send X and SHOULD NOT send Y."
        self.assertEqual(count_rfc2119_keywords(en), {"MUST NOT": 1, "SHOULD NOT": 1})

    def test_count_annotations_half_and_full_width(self):
        ja = "送信しなければなりません (MUST)。送信してはなりません（MUST NOT）。"
        self.assertEqual(count_rfc2119_annotations(ja), {"MUST": 1, "MUST NOT": 1})

    def test_matching_counts_is_ok(self):
        en = "It MUST do X and MAY do Y."
        ja = "Xしなければなりません (MUST)。Yしてもよい (MAY)。"
        self.assertEqual(check_rfc2119_annotation_count(en, ja), [])

    def test_missing_all_annotations_is_w011(self):
        [(code, _)] = check_rfc2119_annotation_count("It MUST do X.", "Xしなければなりません。")
        self.assertEqual(code, "W011")

    def test_partially_missing_is_e014(self):
        [(code, detail)] = check_rfc2119_annotation_count(
            "It MUST do X and MAY do Y.", "Xしなければなりません (MUST)。Yしてもよいです。")
        self.assertEqual(code, "E014")
        self.assertIn("不足 MAY", detail)

    def test_surplus_annotation_is_e015(self):
        # 小文字の should は規範キーワードではないため、(SHOULD) の注釈は過剰
        [(code, detail)] = check_rfc2119_annotation_count(
            "The client MUST ignore it. The client should avoid assumptions.",
            "無視しなければなりません (MUST)。仮定を避けるべきです (SHOULD)。")
        self.assertEqual(code, "E015")
        self.assertIn("過剰 SHOULD", detail)

    def test_wrong_keyword_is_both_missing_and_surplus(self):
        codes = [code for code, _ in check_rfc2119_annotation_count(
            "It MUST do X and MUST do Y.", "Xしなければなりません (MUST)。Yすべきです (SHOULD)。")]
        self.assertEqual(codes, ["E014", "E015"])

    def test_single_keyword_mismatch_is_left_to_e002(self):
        # キーワード1個・注釈1個で種類だけ違う場合は E002 (注釈不一致) の担当
        self.assertEqual(check_rfc2119_annotation_count(
            "It MUST do X.", "Xしてはなりません (MUST NOT)。"), [])

    def test_bcp14_boilerplate_is_skipped(self):
        en = ('The key words "MUST", "MUST NOT", "REQUIRED" in this document are to be '
              'interpreted as described in BCP 14 [RFC2119] [RFC8174].')
        self.assertEqual(check_rfc2119_annotation_count(en, "本文書のキーワード…"), [])


if __name__ == "__main__":
    unittest.main()

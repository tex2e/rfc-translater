import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, "tools")
from lint_translation import check_recommendation_style, lint_file


class TestRecommendationStyle(unittest.TestCase):
    def test_recommended_uses_recommendation_wording(self):
        en = "Use of TLS is RECOMMENDED."
        for ja in ["TLSを使うべきです (RECOMMENDED)。",
                   "TLSの使用をお勧めします (RECOMMENDED)。",
                   "TLSの使用を推奨します (RECOMMENDED)。"]:
            with self.subTest(ja=ja):
                self.assertEqual(check_recommendation_style(en, ja)[0][0], "W018")
        self.assertEqual(check_recommendation_style(
            en, "TLSの使用が推奨されます (RECOMMENDED)。"), [])

    def test_not_recommended_uses_negative_recommendation_wording(self):
        en = "Use of X is NOT RECOMMENDED."
        self.assertEqual(check_recommendation_style(
            en, "Xを使うべきではありません (NOT RECOMMENDED)。")[0][0], "W018")
        self.assertEqual(check_recommendation_style(
            en, "Xの使用は推奨されません (NOT RECOMMENDED)。"), [])

    def test_negative_action_keeps_positive_recommended_keyword(self):
        self.assertEqual(check_recommendation_style(
            "It is RECOMMENDED that X not be used.",
            "Xを使用しないことが推奨されます (RECOMMENDED)。"), [])

    def test_should_and_separate_requirements_are_preserved(self):
        self.assertEqual(check_recommendation_style(
            "It SHOULD use X. Use of Y is RECOMMENDED.",
            "Xを使うべきです (SHOULD)。Yの使用が推奨されます (RECOMMENDED)。"), [])

    def test_keyword_definitions_are_excluded(self):
        self.assertEqual(check_recommendation_style(
            'The word "RECOMMENDED" is defined in RFC 2119.',
            "すべきです (RECOMMENDED) と定義されます。"), [])

    def test_file_entry_point_skips_raw_and_headings(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "rfc9999-trans.json"
            paragraph = {"text": "Use of TLS is RECOMMENDED.",
                         "ja": "TLSを使うべきです (RECOMMENDED)。"}
            doc = {"title": {"text": "RFC 9999 - Test", "ja": "RFC 9999 - テスト"},
                   "contents": [
                       {"text": "Keywords follow RFC 2119.", "ja": "RFC 2119に従います。"},
                       paragraph,
                       {**paragraph, "raw": True},
                       {**paragraph, "section_title": True},
                   ]}
            path.write_text(json.dumps(doc), encoding="utf-8")
            self.assertEqual([(f.code, f.index) for f in lint_file(str(path), {"W018"})],
                             [("W018", 1)])

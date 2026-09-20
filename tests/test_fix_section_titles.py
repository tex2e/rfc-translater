import os
import sys
import unittest

sys.path.insert(0, "tools")
from fix_section_titles import (  # noqa: E402
    canonical_heading,
    find_fixes,
    normalize_numeric_heading,
    reviewed_exclusions,
)


class TestFixSectionTitles(unittest.TestCase):
    def test_canonical_heading(self):
        self.assertEqual(canonical_heading("  + 1.2.  Purpose ....... 7"), "1.2 Purpose")

    def test_toc_and_sequence_matches_without_numbered_step(self):
        contents = [
            {
                "indent": 3,
                "text": "1. Introduction ............ 2\nAcknowledgements ........... 4",
                "raw": True,
                "ja": "",
            },
            {"indent": 0, "text": "1. Introduction", "ja": "1. はじめに"},
            {"indent": 0, "text": "11. Appendix C", "section_title": True, "ja": "11. 付録C"},
            {"indent": 0, "text": "12. Appendix D", "ja": "12. 付録D"},
            {"indent": 1, "text": "2. Send the second message", "ja": "2. 2番目のメッセージを送信"},
            {"indent": 0, "text": "13. Authors' Addresses", "section_title": True, "ja": "13. 著者の連絡先"},
            {"indent": 0, "text": "Acknowledgements", "ja": "謝辞"},
        ]

        toc, sequence, residual = find_fixes(contents)

        self.assertEqual(toc, [1, 6])
        self.assertEqual(sequence, [3])
        self.assertEqual(residual, [4])

    def test_normalize_numeric_heading_spacing(self):
        cases = [
            ("2 Conditions of Use", "2利用規約", "2 利用規約"),
            ("1. Introduction", "1はじめに", "1. はじめに"),
            ("4.2.8.1. Parameters", "4.2.8.1。 Parameters", "4.2.8.1. Parameters"),
            ("3.2. Terminology", "3.2.  用語", "3.2. 用語"),
            ("3.2. Terminology", "3.2. 用語", "3.2. 用語"),
        ]
        for en, ja, expected in cases:
            with self.subTest(en=en, ja=ja):
                self.assertEqual(normalize_numeric_heading(en, ja), expected)

    def test_numeric_heading_does_not_guess_reordered_number(self):
        self.assertIsNone(
            normalize_numeric_heading("2 Recommendations", "推奨事項2件")
        )

    def test_reviewed_exclusions_reads_tsv_keys(self):
        import tempfile

        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline="", delete=False
        ) as file:
            file.write("rfc\tindex\treason\n2801\t184\tnumbered-procedure-step\n")
            path = file.name
        try:
            self.assertEqual(reviewed_exclusions(path), {(2801, 184)})
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

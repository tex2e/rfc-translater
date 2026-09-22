import sys
from pathlib import Path
import unittest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from lint_translation import check_diff_indicator  # noqa: E402


class TestDiffIndicator(unittest.TestCase):
    def test_detects_bad_old_translations(self):
        self.assertIsNotNone(check_diff_indicator("OLD:", "年："))
        self.assertIsNotNone(check_diff_indicator("OLD:", "古い："))
        self.assertIsNotNone(check_diff_indicator("OLD:", "年:"))
        self.assertIsNotNone(check_diff_indicator("OLD:", "古い:"))
        self.assertIsNotNone(check_diff_indicator("_OLD:_", "_古い：_"))
        self.assertIsNotNone(check_diff_indicator("o OLD:", "o 古い："))

    def test_detects_bad_new_translations(self):
        self.assertIsNotNone(check_diff_indicator("NEW:", "新着："))
        self.assertIsNotNone(check_diff_indicator("NEW:", "新しい："))
        self.assertIsNotNone(check_diff_indicator("NEW:", "新着:"))
        self.assertIsNotNone(check_diff_indicator("NEW:", "新しい:"))
        self.assertIsNotNone(check_diff_indicator("_NEW:_", "_新しい：_"))
        self.assertIsNotNone(check_diff_indicator("o NEW:", "o 新着："))
        self.assertIsNotNone(check_diff_indicator("PROPOSED/NEW:", "提案/新規："))

    def test_allows_correct_translations(self):
        self.assertIsNone(check_diff_indicator("OLD:", "旧："))
        self.assertIsNone(check_diff_indicator("NEW:", "新："))
        self.assertIsNone(check_diff_indicator("_OLD:_", "_旧：_"))
        self.assertIsNone(check_diff_indicator("_NEW:_", "_新：_"))
        self.assertIsNone(check_diff_indicator("o OLD:", "o 旧："))
        self.assertIsNone(check_diff_indicator("o NEW:", "o 新："))
        self.assertIsNone(check_diff_indicator("PROPOSED/NEW:", "提案/新："))
        self.assertIsNone(check_diff_indicator("OLD:", "OLD:"))
        self.assertIsNone(check_diff_indicator("NEW:", "NEW:"))

    def test_ignores_normal_sentences(self):
        self.assertIsNone(check_diff_indicator("This is an old document.", "これは古いドキュメントです。"))
        self.assertIsNone(check_diff_indicator("A new mechanism is proposed.", "新しいメカニズムが提案されています。"))

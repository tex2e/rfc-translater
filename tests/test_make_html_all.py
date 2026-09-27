import unittest

from src.application.usecase.make_html_all import find_all_targets
from src.domain.valueobject.rfc import Rfc, RfcDraft


class TestMakeHtmlAll(unittest.TestCase):

    def test_find_all_targets(self):
        targets = find_all_targets()
        rfcs = [t for t in targets if isinstance(t, Rfc)]
        drafts = [t for t in targets if isinstance(t, RfcDraft)]
        # 翻訳済みJSONがあるものだけを、RFC（番号順）→ Draft の順に返す
        self.assertIn('8446', [r.get_id() for r in rfcs])
        self.assertEqual([int(r.get_id()) for r in rfcs], sorted(int(r.get_id()) for r in rfcs))
        self.assertTrue(all(d.get_id().startswith('draft-') for d in drafts))
        self.assertEqual(targets, rfcs + drafts)


if __name__ == '__main__':
    unittest.main()

import unittest

from src.application.usecase.make_html_all import find_all_targets
from src.domain.valueobject.rfc import Rfc, RfcDraft


class TestMakeHtmlAll(unittest.TestCase):

    def test_find_all_targets(self):
        targets = find_all_targets()
        rfcs = [t for t in targets if isinstance(t, Rfc)]
        # 翻訳済みJSONがあるRFCだけを番号順に返し、Draftは公開しない
        self.assertIn('8446', [r.get_id() for r in rfcs])
        self.assertEqual([int(r.get_id()) for r in rfcs], sorted(int(r.get_id()) for r in rfcs))
        self.assertFalse(any(isinstance(t, RfcDraft) for t in targets))
        self.assertEqual(targets, rfcs)

    def test_draft_html_cannot_be_published(self):
        from unittest.mock import patch
        from src.infrastructure.repository.rfchtmlrepository import RfcHtmlFileRepository
        with patch('src.domain.services.rfcfile.RfcFile.write_html_file') as write:
            with self.assertRaisesRegex(ValueError, 'Draft'):
                RfcHtmlFileRepository().save(RfcDraft('draft-ietf-tls-esni-14'), '<html></html>')
            write.assert_not_called()


if __name__ == '__main__':
    unittest.main()

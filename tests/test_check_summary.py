import tempfile
import unittest
from src.domain.valueobject.rfc import Rfc
from src.domain.services.rfcfile import RfcFile
from src.application.usecase.check_summary import check_summary, find_unsummarized
from src.infrastructure.repository.rfcjsontransrepository import RfcJsonTransFileRepository
from src.infrastructure.repository.rfcjsondatasummaryrepository import RfcJsonDataSummaryFileRepository


class TestCheckSummary(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_data_dir = RfcFile.OUTPUT_DATA_DIR
        self.original_glob = RfcFile.GLOB_DATA_TRANS_JSON_FILE
        RfcFile.OUTPUT_DATA_DIR = self.tmpdir.name
        RfcFile.GLOB_DATA_TRANS_JSON_FILE = self.tmpdir.name + '/*/rfc*-trans.json'
        self.rfc = Rfc('9999')
        self.trans_repo = RfcJsonTransFileRepository()
        self.summary_repo = RfcJsonDataSummaryFileRepository()
        self.trans_repo.save(self.rfc, {'title': {'text': 'RFC 9999 - Sample', 'ja': 'RFC 9999 - サンプル'},
                                        'number': 9999, 'contents': []})

    def tearDown(self):
        RfcFile.OUTPUT_DATA_DIR = self.original_data_dir
        RfcFile.GLOB_DATA_TRANS_JSON_FILE = self.original_glob
        self.tmpdir.cleanup()

    def check(self, **overrides) -> list[str]:
        obj = {
            'number': 9999,
            'model': 'claude-sonnet-5-5',
            'created_at': '2026-02-15T00:00:00.000000',
            'summary': ['このRFCはサンプルプロトコルを規定します。',
                        '既存の仕様を拡張します（RFC 1234を更新）。'],
        }
        obj.update(overrides)
        self.summary_repo.save(self.rfc, obj)
        return check_summary(self.rfc, self.trans_repo, self.summary_repo)

    def test_valid(self):
        self.assertEqual(self.check(), [])

    def test_missing_file(self):
        self.assertEqual(len(check_summary(self.rfc, self.trans_repo, self.summary_repo)), 1)

    def test_number_must_match_rfc(self):
        self.assertEqual(len(self.check(number=9998)), 1)
        self.assertEqual(len(self.check(number='9999')), 1)

    def test_created_at_format(self):
        self.assertEqual(len(self.check(created_at='2026-02-15 00:00:00')), 1)

    def test_summary_items(self):
        self.assertEqual(len(self.check(summary=[])), 1)
        self.assertEqual(len(self.check(summary=['あ。'] * 4)), 1)
        self.assertEqual(len(self.check(summary=['**強調**を使った文です。'])), 1)
        self.assertEqual(len(self.check(summary=['である調の文である。'])), 1)
        self.assertEqual(len(self.check(summary=['長い' * 100 + '文です。'])), 1)

    def test_find_unsummarized(self):
        self.assertEqual(find_unsummarized(9000), [9999])
        self.check()
        self.assertEqual(find_unsummarized(9000), [])


if __name__ == '__main__':
    unittest.main()

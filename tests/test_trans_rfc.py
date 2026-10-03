import os
import tempfile
import unittest
from src.domain.valueobject.rfc import Rfc
from src.domain.services.rfcfile import RfcFile
from src.application.usecase.trans_rfc import (trans_prepare, trans_export, trans_import, trans_finish,
                                               trans_status, validate_ja, TransError)
from src.infrastructure.repository.rfcjsondatarepository import RfcJsonDataFileRepository
from src.infrastructure.repository.rfcjsontransrepository import RfcJsonTransFileRepository
from src.infrastructure.repository.rfcjsontransmidwayrepository import RfcJsonTransMidwayFileRepository


class TestValidateJa(unittest.TestCase):

    def test_bullet_prefix_must_be_kept(self):
        content = {'text': '* The length MUST be zero.'}
        self.assertIsNone(validate_ja(content, '* 長さはゼロでなければなりません (MUST)。'))
        self.assertIsNotNone(validate_ja(content, '長さはゼロでなければなりません (MUST)。'))

    def test_section_number_must_be_kept(self):
        content = {'text': '3.1. Address Group Sub-TLVs', 'section_title': True}
        self.assertIsNone(validate_ja(content, '3.1. Address Group Sub-TLV'))
        self.assertIsNotNone(validate_ja(content, 'Address Group Sub-TLV'))

    def test_appendix_prefix(self):
        content = {'text': 'Appendix A. Examples', 'section_title': True}
        self.assertIsNone(validate_ja(content, '付録A. 例'))
        self.assertIsNotNone(validate_ja(content, 'Appendix A. 例'))

    def test_reject_empty_raw_invisible_and_untranslated(self):
        self.assertIsNotNone(validate_ja({'text': 'Some text.'}, ''))
        self.assertIsNotNone(validate_ja({'text': '+--+', 'raw': True}, '表'))
        self.assertIsNotNone(validate_ja({'text': 'Some text.'}, '何らかの​文章です。'))
        text = 'This document defines a new registry for profiles.'
        self.assertIsNotNone(validate_ja({'text': text}, text))

    def test_allow_untranslated_names(self):
        # 著者名や識別子だけの段落は原文のまま残す
        self.assertIsNone(validate_ja({'text': 'Extended Unique Identifier'}, 'Extended Unique Identifier'))


class TestTransWorkflow(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.original_data_dir = RfcFile.OUTPUT_DATA_DIR
        RfcFile.OUTPUT_DATA_DIR = self.tmpdir.name
        self.rfc = Rfc('9999')
        self.data_repo = RfcJsonDataFileRepository()
        self.trans_repo = RfcJsonTransFileRepository()
        self.midway_repo = RfcJsonTransMidwayFileRepository()
        self.data_repo.save(self.rfc, {
            'title': {'text': 'RFC 9999 - Sample Protocol'},
            'number': 9999,
            'created_at': '2026-01-01 00:00:00',
            'updated_by': '',
            'contents': [
                {'indent': 0, 'text': 'Header', 'raw': True},
                {'indent': 0, 'text': '1. Introduction', 'section_title': True},
                {'indent': 3, 'text': 'This document defines a sample protocol.'},
                {'indent': 3, 'text': 'n:'},
                {'indent': 3, 'text': '* A sender MUST set the flag.'},
            ],
        })

    def tearDown(self):
        RfcFile.OUTPUT_DATA_DIR = self.original_data_dir
        self.tmpdir.cleanup()

    def test_workflow(self):
        status = trans_prepare(self.rfc, self.data_repo, self.midway_repo)
        # 図表と変数説明は翻訳対象から外れる
        self.assertEqual(status['remaining_idx'], [1, 2, 4])
        self.assertEqual(status['batches'], [{'offset': 1, 'limit': 4, 'items': 3, 'chars': 84}])
        self.assertFalse(status['title_translated'])

        exported = trans_export(self.rfc, self.trans_repo, self.midway_repo, offset=2, limit=3)
        self.assertEqual([item['idx'] for item in exported['items']], [2, 4])
        self.assertEqual(exported['items'][1]['prefix'], '* ')
        self.assertEqual([item['idx'] for item in exported['context_before']], [1])

        # 未翻訳が残っている間は確定できない
        with self.assertRaises(TransError):
            trans_finish(self.rfc, self.data_repo, self.trans_repo, self.midway_repo)

        # 1件でも検証に失敗したら何も適用しない
        with self.assertRaises(TransError):
            trans_import(self.rfc, self.trans_repo, self.midway_repo, {'items': [
                {'idx': 2, 'ja': 'この文書はサンプルプロトコルを定義します。'},
                {'idx': 4, 'ja': '送信者はフラグを設定しなければなりません (MUST)。'},
            ]})
        self.assertEqual(trans_status(self.rfc, self.midway_repo)['remaining'], 3)

        with self.assertRaises(TransError):
            trans_import(self.rfc, self.trans_repo, self.midway_repo, {'title_ja': 'サンプルプロトコル'})

        status = trans_import(self.rfc, self.trans_repo, self.midway_repo, {
            'title_ja': 'RFC 9999 - サンプルプロトコル',
            'items': [
                {'idx': 1, 'ja': '1. はじめに'},
                {'idx': 2, 'ja': 'この文書はサンプルプロトコルを定義します。'},
                {'idx': 4, 'ja': '* 送信者はフラグを設定しなければなりません (MUST)。'},
            ]})
        self.assertEqual(status['remaining'], 0)

        self.assertTrue(trans_finish(self.rfc, self.data_repo, self.trans_repo, self.midway_repo))
        obj = self.trans_repo.find(self.rfc)
        self.assertEqual(obj['title']['ja'], 'RFC 9999 - サンプルプロトコル')
        self.assertEqual([c['ja'] for c in obj['contents']], [
            '', '1. はじめに', 'この文書はサンプルプロトコルを定義します。', 'n:',
            '* 送信者はフラグを設定しなければなりません (MUST)。'])
        self.assertFalse(os.path.exists(self.data_repo.findpath(self.rfc)))
        self.assertFalse(os.path.exists(self.midway_repo.findpath(self.rfc)))

        # 確定後も訳文の修正を適用できる
        trans_import(self.rfc, self.trans_repo, self.midway_repo,
                     {'items': [{'idx': 1, 'ja': '1. 導入'}]})
        self.assertEqual(self.trans_repo.find(self.rfc)['contents'][1]['ja'], '1. 導入')


if __name__ == '__main__':
    unittest.main()

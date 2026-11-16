"""make_html (JSON→HTML) と make_json_from_html (HTML→JSON) の往復で翻訳データが失われないことの検証。

翻訳者は html/rfcXXXX.html を直接編集し、--make-json でJSONに戻す運用のため、
テンプレートに表示用の要素（リンク・アンカー・クラス）を足しても本文が変化してはならない。
"""

import re
import textwrap
import unittest

from src.application.usecase.make_html import RfcHtmlHelper, make_html
from src.application.usecase.make_json_from_html import make_json_from_html
from src.domain.valueobject.rfc import Rfc, RfcJsonElem
from src.infrastructure.repository.rfcjsontransrepository import (
    IRfcJsonTransRepository, RfcJsonTransFileRepository)
from src.infrastructure.repository.rfcjsondatasummaryrepository import (
    RfcJsonDataSummaryFileRepository)
from src.infrastructure.repository.rfchtmlrepository import IRfcHtmlRepository

# 見出し・目次・図表・箇条書き・RFC参照を一通り含むRFC
SAMPLE_RFCS = ['8446', '9110', '5280', '2616', '7540', '9293',
               '2397', '5005', '5707', '6121', '6596', '6787',
               '2557', '4590', '4709', '5090', '7991', '7992', '6749']


class MemoryHtmlRepository(IRfcHtmlRepository):
    def __init__(self):
        self.html = {}

    def findpath(self, rfc):
        return f'memory/rfc{rfc.get_id()}.html'

    def find(self, rfc):
        return self.html[rfc.get_id()]

    def save(self, rfc, obj):
        self.html[rfc.get_id()] = obj

    def delete(self, rfc):
        return self.html.pop(rfc.get_id(), None) is not None

    def findall(self):
        return []

    def findalldraft(self):
        return []


class MemoryJsonTransRepository(IRfcJsonTransRepository):
    def __init__(self):
        self.obj = {}

    def findpath(self, rfc):
        return f'memory/rfc{rfc.get_id()}-trans.json'

    def find(self, rfc):
        return self.obj.get(rfc.get_id())

    def save(self, rfc, obj):
        self.obj[rfc.get_id()] = obj

    def delete(self, rfc):
        return self.obj.pop(rfc.get_id(), None) is not None

    def get_title(self, rfc):
        return self.obj[rfc.get_id()][RfcJsonElem.TITLE][RfcJsonElem.Title.TEXT]

    def findall_titles_ja(self):
        return {}


def normalize(paragraph):
    """往復で比較する項目だけを取り出す。

    既存の仕様で揺れる部分（図表の共通インデント、文章中の連続改行や空白の数）は正規化して比較する。
    """
    raw = bool(paragraph.get(RfcJsonElem.Contents.RAW))
    if raw:
        text = textwrap.dedent(paragraph[RfcJsonElem.Contents.TEXT].strip('\n')).strip('\n')
        ja = ''
    else:
        text = re.sub(r'\s+', ' ', paragraph[RfcJsonElem.Contents.TEXT]).strip()
        ja = re.sub(r'\s+', ' ', paragraph[RfcJsonElem.Contents.JA]).strip()
    section_title = bool(paragraph.get(RfcJsonElem.Contents.SECTION_TITLE))
    return {
        'text': text,
        'ja': ja,
        'indent': paragraph.get(RfcJsonElem.Contents.INDENT, 0) if not raw and not section_title else None,
        'raw': raw,
        'section_title': section_title,
        'toc': bool(paragraph.get(RfcJsonElem.Contents.TOC)),
        'list_continuation': bool(paragraph.get(RfcJsonElem.Contents.LIST_CONTINUATION)),
        'merged_paragraphs': paragraph.get(RfcJsonElem.Contents.MERGED_PARAGRAPHS, 0),
        'preserve_paragraph_numbering': bool(paragraph.get(RfcJsonElem.Contents.PRESERVE_PARAGRAPH_NUMBERING)),
    }


class TestMakeHtmlRoundTrip(unittest.TestCase):

    def test_dot_bullet_keeps_the_marker_and_hanging_indent(self):
        self.assertEqual(RfcHtmlHelper.bullet_class('. 入力形式'), ' bullet')
        self.assertIn('<span class="bullet-mark">.</span> 入力形式', RfcHtmlHelper.render_text('. 入力形式'))

    def test_split_list_preserves_existing_paragraph_ids(self):
        paragraphs = [
            {'text': '1. Introduction', 'section_title': True},
            {'text': 'o client'},
            {'text': 'o datastore', 'list_continuation': True},
            {'text': 'o server', 'list_continuation': True},
            {'text': 'The next paragraph.'},
        ]
        self.assertEqual(RfcHtmlHelper.make_paragraph_ids(paragraphs), [
            None, '1--Introduction-p1', '1--Introduction-p1-item2',
            '1--Introduction-p1-item3', '1--Introduction-p2',
        ])

    def test_merged_paragraph_preserves_existing_links_and_roundtrips(self):
        rfc = Rfc('6337')
        original = RfcJsonTransFileRepository().find(rfc)
        html_repo = MemoryHtmlRepository()
        json_repo = MemoryJsonTransRepository()
        json_repo.save(rfc, original)
        make_html(rfc, json_repo, RfcJsonDataSummaryFileRepository(), html_repo)

        html = html_repo.find(rfc)
        self.assertIn('class="paragraph-anchor" id="5-3--Hold-and-Resume-of-Media-p11"', html)
        self.assertIn('class="row" id="5-3--Hold-and-Resume-of-Media-p10"', html)

        make_json_from_html(rfc, html_repo, json_repo)
        self.assertEqual([normalize(p) for p in json_repo.find(rfc)[RfcJsonElem.CONTENTS]],
                         [normalize(p) for p in original[RfcJsonElem.CONTENTS]])

    def test_merged_paragraph_keeps_following_paragraph_numbers(self):
        heading = {'text': '1. Introduction', 'section_title': True}
        paragraphs = [heading, {'text': 'First and second.', 'merged_paragraphs': 1},
                      {'text': 'Third.'}, {'text': 'Fourth.'}]
        aliases = {}
        self.assertEqual(RfcHtmlHelper.make_paragraph_ids(paragraphs, aliases=aliases), [
            None, '1--Introduction-p1', '1--Introduction-p3', '1--Introduction-p4',
        ])
        self.assertEqual(aliases, {1: ['1--Introduction-p2']})

    def test_raw_rows_preserve_previous_paragraph_anchors_and_roundtrip(self):
        rfc = Rfc('6337')
        data = RfcJsonTransFileRepository().find(rfc)
        paragraphs = [
            {'indent': 0, 'text': '1. Introduction', 'ja': '1. はじめに', 'section_title': True},
            {'indent': 0, 'text': 'First.', 'ja': ''},
            {'indent': 0, 'text': '1) Raw list item.', 'ja': '', 'raw': True, 'list_continuation': True},
            {'indent': 0, 'text': '2. Restored heading', 'ja': '2. 復元した見出し', 'section_title': True,
             'preserve_paragraph_numbering': True},
            {'indent': 0, 'text': 'Code block.', 'ja': '', 'raw': True, 'merged_paragraphs': 1},
        ]
        data[RfcJsonElem.CONTENTS] = paragraphs
        html_repo = MemoryHtmlRepository()
        json_repo = MemoryJsonTransRepository()
        json_repo.save(rfc, data)
        make_html(rfc, json_repo, RfcJsonDataSummaryFileRepository(), html_repo)

        html = html_repo.find(rfc)
        self.assertIn('id="1--Introduction-p1-item2" data-list-continuation="true"', html)
        self.assertIn('id="2--Restored-heading"', html)
        self.assertIn('id="1--Introduction-p2"', html)
        self.assertIn('class="paragraph-anchor" id="1--Introduction-p3"', html)

        make_json_from_html(rfc, html_repo, json_repo)
        self.assertEqual([normalize(p) for p in json_repo.find(rfc)[RfcJsonElem.CONTENTS]],
                         [normalize(p) for p in paragraphs])

    def test_roundtrip_keeps_contents(self):
        file_repo = RfcJsonTransFileRepository()
        for rfc_number in SAMPLE_RFCS:
            with self.subTest(rfc=rfc_number):
                rfc = Rfc(rfc_number)
                original = file_repo.find(rfc)
                html_repo = MemoryHtmlRepository()
                make_html(rfc, file_repo, RfcJsonDataSummaryFileRepository(), html_repo)

                json_repo = MemoryJsonTransRepository()
                make_json_from_html(rfc, html_repo, json_repo)
                restored = json_repo.find(rfc)

                self.assertEqual(restored[RfcJsonElem.TITLE], original[RfcJsonElem.TITLE])
                expected = [normalize(p) for p in original[RfcJsonElem.CONTENTS]]
                actual = [normalize(p) for p in restored[RfcJsonElem.CONTENTS]]
                self.assertEqual(len(actual), len(expected))
                for i, (a, e) in enumerate(zip(actual, expected)):
                    self.assertEqual(a, e, f'paragraph {i}')


if __name__ == '__main__':
    unittest.main()

import copy
import unittest

from bs4 import BeautifulSoup

from src.application.usecase.make_html import RfcHtmlHelper, make_html
from src.application.usecase.make_json_from_html import make_json_from_html
from src.application.usecase.rfc_toc import make_toc_rows
from src.domain.valueobject.rfc import Rfc
from src.infrastructure.repository.rfcjsondatasummaryrepository import RfcJsonDataSummaryFileRepository
from tests.test_make_html_roundtrip import MemoryHtmlRepository, MemoryJsonTransRepository


def heading(text, ja):
    return {'text': text, 'ja': ja, 'indent': 0, 'section_title': True}


def toc(text, indent=3):
    return {'text': text, 'ja': '', 'indent': indent, 'raw': True, 'toc': True}


def rows(contents):
    return make_toc_rows(contents, RfcHtmlHelper.make_paragraph_ids(contents), RfcHtmlHelper.text_to_id)


class TestBilingualToc(unittest.TestCase):
    def test_preserves_indent_number_spelling_and_page_numbers(self):
        contents = [toc('1   Introduction ....................7\n   1.1.  Purpose ...................8'),
                    heading('1. Introduction', '1. はじめに'),
                    heading('1.1 Purpose', '1.1 目的')]
        original = copy.deepcopy(contents)
        result = rows(contents)[0]
        self.assertEqual(result[0]['en'], '   1   Introduction ....................7')
        self.assertTrue(result[0]['ja'].startswith('   1   はじめに '))
        self.assertTrue(result[0]['ja'].endswith('7'))
        self.assertTrue(result[1]['ja'].startswith('      1.1.  目的 '))
        self.assertTrue(result[1]['ja'].endswith('8'))
        self.assertEqual(result[1]['target'], '1-1-Purpose')
        self.assertEqual(contents, original)

    def test_wrapped_entries_blank_lines_and_multiple_blocks(self):
        contents = [toc('1. A long heading\n   continued .................12\n\n2. Next .............13'),
                    toc('Appendix A.  Examples\n  A.1.  More Examples'),
                    heading('1. A long heading continued', '1. 長い見出し'),
                    heading('2. Next', '2. 次'),
                    heading('Appendix A. Examples', '付録A. 例'),
                    heading('A.1. More Examples', 'A.1. 追加の例')]
        result = rows(contents)
        self.assertEqual(len(result[0]), 3)
        self.assertIn('\n      continued', result[0][0]['en'])
        self.assertTrue(result[0][1]['blank'])
        self.assertTrue(result[0][0]['ja'].endswith('12'))
        self.assertEqual(result[1][0]['ja'], '   Appendix A.  例')
        self.assertEqual(result[1][1]['ja'], '     A.1.  追加の例')

    def test_unnumbered_headings_and_safe_fallbacks(self):
        contents = [toc('Acknowledgments\nMissing Heading\n1. Ambiguous\n2. No Translation'),
                    heading('Acknowledgments', '謝辞'),
                    heading('1. First', '1. 最初'), heading('1. Second', '1. 二番目'),
                    heading('2. No Translation', '')]
        result = rows(contents)[0]
        self.assertEqual(result[0]['ja'], '   謝辞')
        for item in result[1:]:
            self.assertFalse(item['translated'])
            self.assertEqual(item['ja'], item['en'])
        self.assertIsNone(result[2]['target'])

    def test_long_japanese_title_is_never_truncated(self):
        title = '長い日本語の見出し' * 20
        result = rows([toc('1. Short ...........7'), heading('1. Short', '1. ' + title)])[0][0]
        self.assertIn(title, result['ja'])
        self.assertTrue(result['ja'].endswith(' ..7'))

    def test_continuation_matching_another_heading_stays_with_its_entry(self):
        contents = [toc('1.  Content-Negotiated\n    Resources\n2.  Next'),
                    heading('1. Content-Negotiated Resources', '1. コンテンツネゴシエーション対象リソース'),
                    heading('2. Next', '2. 次'), heading('3. Resources', '3. リソース')]
        result = rows(contents)[0]
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]['translated'])
        self.assertEqual(result[0]['target'], '1--Content-Negotiated-Resources')

    def test_mismatched_titles_do_not_link_by_number_alone(self):
        result = rows([toc('1. A diagram'), heading('1. Introduction', '1. はじめに')])[0][0]
        self.assertFalse(result['translated'])
        self.assertIsNone(result['target'])

    def test_old_lettered_numbers_and_roman_page_numbers(self):
        result = rows([toc('4a.  First Page Heading . . . . . . vii'),
                       heading('4a. First Page Heading', '4a. 最初のページの見出し')])[0][0]
        self.assertTrue(result['translated'])
        self.assertTrue(result['ja'].startswith('   4a.  最初のページの見出し'))
        self.assertTrue(result['ja'].endswith('vii'))

    def test_single_dot_page_separator_does_not_strip_version_numbers(self):
        result = rows([toc('1. Long title.89\n2. TLS 1.3'),
                       heading('1. Long title', '1. 長い題名'),
                       heading('2. TLS 1.3', '2. TLS 1.3')])[0]
        self.assertTrue(result[0]['translated'])
        self.assertTrue(result[0]['ja'].endswith('89'))
        self.assertEqual(result[1]['ja'], '   2. TLS 1.3')

    def test_html_escapes_titles_and_does_not_nest_links(self):
        rendered = RfcHtmlHelper.render_toc_cell('<script> & RFC 9110', '1-Example')
        soup = BeautifulSoup(rendered, 'html.parser')
        self.assertIsNone(soup.find('script'))
        self.assertEqual(len(soup.find_all('a')), 1)
        self.assertEqual(soup.a.text, '<script> & RFC 9110')

    def test_roundtrip_uses_exact_source_and_ignores_derived_translation(self):
        source = toc('1.  Introduction ...........7\n\n  1.1.  Purpose ...........8\n', 5)
        contents = [source, heading('1. Introduction', '1. はじめに'), heading('1.1. Purpose', '1.1. 目的')]
        rfc = Rfc('99999')
        obj = {'title': {'text': 'RFC 99999 - Test', 'ja': 'RFC 99999 - テスト'},
               'number': 99999, 'created_at': '', 'updated_by': '', 'contents': contents}
        json_repo = MemoryJsonTransRepository()
        json_repo.save(rfc, obj)
        html_repo = MemoryHtmlRepository()
        make_html(rfc, json_repo, RfcJsonDataSummaryFileRepository(), html_repo)
        soup = BeautifulSoup(html_repo.find(rfc), 'html.parser')
        soup.select_one('.toc-cell[lang="ja"]').string = '表示側だけの変更'
        html_repo.save(rfc, str(soup))
        restored = MemoryJsonTransRepository()
        make_json_from_html(rfc, html_repo, restored)
        self.assertEqual(restored.find(rfc)['contents'][0], source)


if __name__ == '__main__':
    unittest.main()

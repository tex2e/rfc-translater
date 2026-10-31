import copy
import json
from pathlib import Path
import unittest

from src.domain.valueobject.rfc.contents.paragraph import Paragraph, BREAK
from tests.test_bilingual_toc import toc, heading, rows
from tools.check_toc import inspect, check_html


class TestTocRepairs(unittest.TestCase):
    def test_rfc3323_indent_and_short_title_regression(self):
        path = Path(__file__).resolve().parents[1] / 'data/3000/rfc3323-trans.json'
        obj = json.loads(path.read_text())
        entries = [e for block in rows(obj['contents']).values() for e in block]
        target = {e['number']: e for e in entries if e['number'] in ('5.1', '5.2', '5.3')}
        leading = lambda value: len(value) - len(value.lstrip(' '))
        self.assertEqual(leading(target['5.1']['en']), leading(target['5.2']['en']))
        self.assertTrue(target['5.3']['translated'])
        self.assertEqual(target['5.3']['target'], '5-3-Applying-User-Level-Privacy-Functions-at-a-Privacy-Service')

    def test_page_breaks_are_dedented_as_logical_lines(self):
        p = Paragraph('   5. Section ...................14' + BREAK +
                      '   5.1 Header ..................16\n   5.2 Session .................17' + BREAK +
                      '   5.3 User ....................18')
        self.assertEqual(p.indent, 3)
        self.assertTrue(p.is_toc)
        self.assertTrue(all(line[0] == '5' for line in p.text.splitlines()))

    def test_code_page_break_preserves_relative_indent(self):
        p = Paragraph('   begin {\n     first;' + BREAK + '     second;\n   }', is_code=True)
        self.assertEqual(p.text, 'begin {\n  first;\n  second;\n}')
        self.assertEqual(p.indent, 3)

    def test_prose_page_break_remains_a_space(self):
        p = Paragraph('   This paragraph continues' + BREAK + '   on the next page.')
        self.assertFalse(p.is_code)
        self.assertEqual(p.text, 'This paragraph continues on the next page.')

    def test_short_titles_link_in_a_confirmed_toc(self):
        contents = [{'text': 'Table of Contents', 'ja': '目次', 'indent': 0},
                    toc('5.3 Applying User-Level Privacy Functions ........18'),
                    heading('5.3 Applying User-Level Privacy Functions at a Privacy Service', '5.3 プライバシーサービスでの適用')]
        entry = rows(contents)[1][0]
        self.assertTrue(entry['translated'])
        self.assertTrue(entry['target'].startswith('5-3-'))
        self.assertEqual(entry['issue'], 'title_mismatch')
        self.assertIn('プライバシーサービスでの適用', entry['ja'])

    def test_matching_multiple_headings_confirms_a_legacy_toc(self):
        contents = [toc('1. First .......1\n2. Second .......2\n3. Short .......3'),
                    heading('1. First', '1. 最初'), heading('2. Second', '2. 二番目'),
                    heading('3. Short with more detail', '3. 詳細')]
        self.assertTrue(rows(contents)[0][2]['translated'])

    def test_source_verified_indent_patch_only_changes_whitespace(self):
        obj = {'number': 3323, 'contents': [
            {'text': 'Table of Contents', 'ja': '目次', 'indent': 0},
            toc('5.1 Header .........16\n   5.2 Session .........17'),
            heading('5.1 Header', '5.1 ヘッダー'), heading('5.2 Session', '5.2 セッション')]}
        original = copy.deepcopy(obj)
        source = 'Request for Comments: 3323\n   5.1 Header .........16\n\f\nRFC 3323 Header\n\n   5.2 Session .........17\n'
        issues, changes = inspect(obj, source, apply=True)
        self.assertEqual(len(changes), 1)
        self.assertEqual(obj['contents'][1]['text'], '5.1 Header .........16\n5.2 Session .........17')
        original['contents'][1]['text'] = obj['contents'][1]['text']
        self.assertEqual(obj, original)
        self.assertFalse(inspect(obj, source, apply=True)[1])

    def test_non_page_break_indent_difference_requires_review(self):
        obj = {'number': 3323, 'contents': [
            {'text': 'Table of Contents', 'ja': '目次', 'indent': 0},
            toc('   5.1 Header .........16'), heading('5.1 Header', '5.1 ヘッダー')]}
        original = copy.deepcopy(obj)
        source = 'Request for Comments: 3323\n   5.1 Header .........16\n'
        issues, changes = inspect(obj, source, apply=True)
        self.assertFalse(changes)
        self.assertTrue(any(i['kind'] == 'source_indent_review' for i in issues))
        self.assertEqual(obj, original)

    def test_no_source_no_speculative_indent_repair(self):
        obj = {'number': 1, 'contents': [toc('1. One\n   2. Two\n3. Three\n4. Four')]}
        original = copy.deepcopy(obj)
        inspect(obj, apply=True)
        self.assertEqual(obj, original)

    def test_broken_or_different_targets_are_errors(self):
        html = '<div class="toc-grid"><pre class="toc-cell"><a href="#a">A</a></pre><pre class="toc-cell"><a href="#b">B</a></pre></div><h5 id="a">A</h5>'
        self.assertEqual({x['kind'] for x in check_html(html)}, {'invalid_target', 'paired_target_mismatch'})


if __name__ == '__main__':
    unittest.main()

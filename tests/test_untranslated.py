import json
from pathlib import Path
import unittest

from tools.check_untranslated import inspect


class TestUntranslated(unittest.TestCase):
    def test_guidance_is_detected_even_with_whitespace_or_case_differences(self):
        obj = {'number': 1, 'contents': [
            {'text': 'With an input of:', 'ja': 'With an Input of:'},
            {'text': 'Content model:', 'ja': ''},
            {'text': 'In any order:', 'ja': '任意の順序：'},
            {'text': 'With an input of:', 'ja': '', 'raw': True}]}
        self.assertEqual([f['kind'] for f in inspect(obj)], ['guidance', 'guidance'])

    def test_references_author_information_and_literals_are_preserved(self):
        obj = {'number': 1, 'contents': [
            {'text': 'o "false" (default)', 'ja': 'o "false" (default)'},
            {'text': '* inline-or-keystore-end-entity-cert-with-key-grouping', 'ja': ''},
            {'text': '* Service-tenant-from-another-org.example.org', 'ja': ''},
            {'text': 'o mdt-softwire-mapping-address-and-port (2011-10-24)', 'ja': ''},
            {'text': "A.3.1. <with-defaults> = 'report-all'", 'ja': '', 'section_title': True},
            {'text': 'https://example.com/', 'ja': 'https://example.com/'},
            {'text': '9. References', 'ja': '9. 参考文献', 'section_title': True},
            {'text': '[EXAMPLE] Smith, A., "The example of a document", 2026.', 'ja': ''},
            {'text': "Author's Address", 'ja': '著者のアドレス', 'section_title': True},
            {'text': 'Someone At The University Of Somewhere', 'ja': ''}]}
        self.assertFalse(inspect(obj))

    def test_untranslated_body_is_a_review_candidate(self):
        obj = {'number': 1, 'contents': [
            {'text': 'This element represents a comment in the document.', 'ja': ''},
            {'text': 'This element represents a comment in the document.', 'ja': 'この要素は文書内のコメントを表します。'}]}
        self.assertEqual(len(inspect(obj)), 1)
        self.assertEqual(inspect(obj)[0]['kind'], 'prose_candidate')

    def test_inline_bibliography_and_contributor_names_are_not_missing_prose(self):
        obj = {'number': 1, 'contents': [
            {'text': '[8] Smith, A. and B. Jones, "The example of a protocol", RFC 1234, October 2000.', 'ja': ''},
            {'text': 'RFC 4015 S: "The Eifel Response Algorithm for TCP" (February 2005)', 'ja': ''},
            {'text': '[11] Telcordia, "GR-506: Signaling for Analog Interfaces, Issue 1, Revision 1", Nov 1996.', 'ja': ''},
            {'text': 'o "IPv6 over Low-Power Wireless Personal Area Networks: Overview" [RFC4919]', 'ja': ''},
            {'text': 'Acknowledgements', 'ja': '謝辞', 'section_title': True},
            {'text': 'Anand Vijayan, Chris Marshall, Jay Lindenauer, and Michael Shannon.', 'ja': ''},
            {'text': 'Brian Campbell (Ping Identity), George Fletcher (AOL), and Justin Richer (MITRE).', 'ja': ''},
            {'text': 'James H. Manger (Telstra), Breno de Medeiros (Google), and Éric Vyncke (as AD).', 'ja': ''},
            {'text': 'o RFC 2616 Hyper Text Transfer Protocol o RFC 1767 EDI Content Type o RFC 3023 XML Media Types', 'ja': ''},
            {'text': "5.1. 'server-error-printer-is-deactivated' (0x050A)", 'ja': "5.1. 'server-error-printer-is-deactivated' (0x050A)", 'section_title': True}]}
        self.assertFalse(inspect(obj))

    def test_xml_vocabulary_rfcs_have_no_remaining_prose_candidates(self):
        root = Path(__file__).resolve().parents[1]
        for number in (7991, 7992):
            with self.subTest(rfc=number):
                obj = json.loads((root / f'data/7000/rfc{number}-trans.json').read_text())
                self.assertFalse(inspect(obj))


if __name__ == '__main__':
    unittest.main()

import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from src.application.usecase.fetch_rfc_txt import fetch_rfc_txt
from src.domain.valueobject.rfc import Rfc
from src.domain.valueobject.rfc.contents.paragraphs import Paragraphs
from src.infrastructure.apiclient.rfcapiclient import IRfcApiClient
from src.infrastructure.repository.rfcjsondatarepository import IRfcJsonDataRepository
from tools.check_html_fragments import inspect


def fetch(text):
    api = MagicMock(spec=IRfcApiClient)
    api.fetch_html.return_value.content = b'<title>RFC 2397 - Test</title>'
    api.fetch_txt.return_value.content = text.encode('ascii')
    repo = MagicMock(spec=IRfcJsonDataRepository)
    fetch_rfc_txt(Rfc('2397'), repo, api, SimpleNamespace(force=True))
    return repo.save.call_args.args[1]['contents']


class TestHtmlFragments(unittest.TestCase):
    def test_image_and_description_do_not_join_across_page(self):
        blocks = fetch('Header\n\n   The HTML fragment:\n'
                       '   <IMG\n   SRC="data:image/gif;base64,AAAA"\n   ALT="Larry">\n\n'
                       'Author [Page 2]\n\f\nRFC 2397\n\n'
                       '   could be used for a small inline image.\n')
        self.assertEqual([p['text'] for p in blocks[1:]], [
            'The HTML fragment:', '<IMG\nSRC="data:image/gif;base64,AAAA"\nALT="Larry">',
            'could be used for a small inline image.'])
        self.assertTrue(blocks[2]['raw'])
        self.assertFalse(blocks[3].get('raw', False))
        self.assertEqual(blocks[3]['indent'], 3)

    def test_complete_xml_and_following_explanation_are_separate(self):
        blocks = fetch('Header\n\n   <message>\n     <body>Hello</body>\n   </message>\n\n'
                       'Author [Page 2]\n\f\nRFC 2397\n\n   For details, see the specification.')
        self.assertTrue(blocks[1]['raw'])
        self.assertNotIn('For details', blocks[1]['text'])
        self.assertFalse(blocks[2].get('raw', False))

    def test_incomplete_tag_still_continues_across_page(self):
        blocks = fetch('Header\n\n   <IMG SRC="image.gif"\n\n'
                       'Author [Page 2]\n\f\nRFC 2397\n\n   ALT="Example">')
        self.assertEqual(blocks[1]['text'], '<IMG SRC="image.gif"\nALT="Example">')
        self.assertTrue(blocks[1]['raw'])

    def test_attribute_values_can_contain_greater_than(self):
        blocks = list(Paragraphs('   Intro:\n   <img alt="x > y" src="x">\n   Description.', ignore_header=False))
        self.assertEqual(len(blocks), 3)
        self.assertTrue(blocks[1].is_code)
        self.assertFalse(blocks[2].is_code)

    def test_inline_tags_and_protocol_variables_remain_prose(self):
        for text in ['The HTML <A> anchor is used here.', '<head> is omitted if head-length is zero.',
                     '<table> An <id> that names a table.', '<P>_b indicates the body of payload <P>.',
                     'See <a href="https://example.com/">the example</a> for details.',
                     'Use <span>.']:
            with self.subTest(text=text):
                blocks = list(Paragraphs(text, ignore_header=False))
                self.assertEqual(len(blocks), 1)
                self.assertFalse(blocks[0].is_code)

    def test_blank_lines_in_complete_html_document_preserved(self):
        document = '<?xml version="1.0"?>\n\n<!DOCTYPE html>\n\n<html>\n\n<head>\n\n<meta charset="utf-8">\n\n</head>\n\n<body>\n\n<p>Hello</p>\n\n</body>\n\n</html>'
        blocks = list(Paragraphs(document + '\n\nExplanation.', ignore_header=False))
        self.assertEqual(len(blocks), 2)
        self.assertTrue(blocks[0].is_code)
        self.assertEqual(blocks[0].text, document)
        self.assertFalse(blocks[1].is_code)

    def test_existing_xml_block_is_not_split_at_html_named_children(self):
        text = '<message from="romeo@example.net">\n  <body>Hello</body>\n</message>'
        blocks = list(Paragraphs(text, ignore_header=False))
        self.assertEqual(len(blocks), 1)
        self.assertTrue(blocks[0].is_code)
        self.assertEqual(blocks[0].text, text)

    def test_http_and_mime_samples_keep_physical_lines(self):
        for text in ['   HTTP/1.1 200 OK\n   ...',
                     '   GET /inbox/ HTTP/1.1\n   Host: www.example.com',
                     '      --boundary-example\n      Content-Location: image.gif',
                     '      R0lGODlhGAGgAPEAAP/////ZRaCgoAAAACH+PUNvcHlyaWdodCAoQykgMTk5\n      etc...']:
            with self.subTest(text=text):
                blocks = list(Paragraphs(text, ignore_header=False))
                self.assertEqual(len(blocks), 1)
                self.assertTrue(blocks[0].is_code)
                self.assertIn('\n', blocks[0].text)

    def test_mib_description_is_literal_across_blank_lines(self):
        text = ('   EXAMPLE-MIB DEFINITIONS ::= BEGIN\n\n'
                '       DESCRIPTION "\n\n'
                '         This text is part of a MIB string.\n\n'
                '       "\n\n   END\n\n'
                '   This is explanatory prose after the module.')
        blocks = list(Paragraphs(text, ignore_header=False))
        self.assertTrue(all(p.is_code for p in blocks[:-1]))
        self.assertFalse(blocks[-1].is_code)

    def test_fenced_yang_description_is_not_translated(self):
        text = ('   <CODE BEGINS> file "example.yang"\n\n'
                '   This is English inside source code.\n\n'
                '   <CODE ENDS>\n\n   This paragraph explains the code.')
        blocks = list(Paragraphs(text, ignore_header=False))
        self.assertTrue(all(p.is_code for p in blocks[:-1]))
        self.assertFalse(blocks[-1].is_code)

    def test_state_table_rows_remain_literal_between_blank_lines(self):
        text = ('   STATE          EVENT                                  NEW STATE\n'
                '   ---------------------------------------------------------------\n'
                '   RESET          Initial event                          WAITING\n\n'
                '                  Transmit Application Connect TLV       CONNECTING\n'
                '                  with A-bit=1\n\n'
                '   This paragraph explains the table.')
        blocks = list(Paragraphs(text, ignore_header=False))
        self.assertTrue(blocks[0].is_code)
        self.assertTrue(blocks[1].is_code)
        self.assertIn('       CONNECTING\n', blocks[1].text)
        self.assertFalse(blocks[2].is_code)

    def test_explicit_xml_input_example_is_not_translated(self):
        example = '   See <relref section="2.3" target="RFC9999"/> for an overview.'
        blocks = list(Paragraphs('   For example, with an input of:\n\n' + example, ignore_header=False))
        self.assertFalse(blocks[0].is_code)
        self.assertTrue(blocks[1].is_code)
        self.assertEqual(blocks[1].text, example.strip())
        inline = list(Paragraphs('   This is ordinary prose.\n\n' + example, ignore_header=False))
        self.assertFalse(inline[1].is_code)

    def test_ldap_schema_description_and_nested_lists_remain_code(self):
        text = ("   ( nisSchema.2.1 NAME 'shadowAccount'\n"
                "     DESC 'Additional attributes (including passwords)'\n"
                "     MUST uid MAY ( userPassword $ description ) )")
        blocks = list(Paragraphs(text, ignore_header=False))
        self.assertEqual(len(blocks), 1)
        self.assertTrue(blocks[0].is_code)
        self.assertIn('\n', blocks[0].text)

    def test_ldap_schema_is_separated_from_following_explanation(self):
        text = ("   ( 1.3.6.1 NAME 'example' DESC 'The example' )\n"
                "   This paragraph explains another attribute.")
        blocks = list(Paragraphs(text, ignore_header=False))
        self.assertEqual(len(blocks), 2)
        self.assertTrue(blocks[0].is_code)
        self.assertFalse(blocks[1].is_code)
        self.assertEqual(blocks[1].indent, 3)

    def test_annotated_cbor_keeps_comments_and_physical_lines(self):
        text = ("   [ 12, / type code /\n"
                "     2, / block number /\n"
                "     1, / flags - block must be replicated /\n"
                "     0, / CRC type /\n"
                "     h'81010201' ]")
        blocks = list(Paragraphs(text, ignore_header=False))
        self.assertEqual(len(blocks), 1)
        self.assertTrue(blocks[0].is_code)
        self.assertIn('\n', blocks[0].text)

    def test_unrelated_xml_and_html_documents_are_not_merged(self):
        text = '<?xml version="1.0"?><feed><entry>Example</entry></feed>'
        blocks = list(Paragraphs(text + '\n\nExplanation.\n\n<html><body>Other example</body></html>', ignore_header=False))
        self.assertEqual(len(blocks), 3)
        self.assertEqual(blocks[0].text, text)
        self.assertFalse(blocks[1].is_code)

    def test_repaired_rfc2397_keeps_code_out_of_translation(self):
        path = Path(__file__).resolve().parents[1] / 'data/2000/rfc2397-trans.json'
        obj = json.loads(path.read_text())
        image = next(p for p in obj['contents'] if p['text'].startswith('<IMG'))
        self.assertTrue(image['raw'])
        self.assertEqual(image['ja'], '')
        self.assertEqual(len(image['text'].splitlines()), 9)
        self.assertNotIn('could be used', image['text'])
        description = next(p for p in obj['contents'] if p['text'].startswith('could be used'))
        self.assertEqual(description['indent'], 3)
        self.assertTrue(description['ja'])
        self.assertFalse([f for f in inspect(obj) if f['kind'] == 'block_candidate'])

    def test_audit_distinguishes_block_and_inline_candidates(self):
        obj = {'number': 1, 'contents': [
            {'text': '<img src="x">'}, {'text': 'The <head> element is optional.'},
            {'text': '<img src="x">', 'raw': True}]}
        self.assertEqual([f['kind'] for f in inspect(obj)], ['block_candidate', 'inline_or_placeholder'])

    def test_html_example_is_escaped_in_rendered_output(self):
        import lxml.html
        from src.application.usecase.make_html import make_html
        from src.infrastructure.repository.rfcjsontransrepository import RfcJsonTransFileRepository
        from src.infrastructure.repository.rfcjsondatasummaryrepository import RfcJsonDataSummaryFileRepository
        from tests.test_make_html_roundtrip import MemoryHtmlRepository
        repo = MemoryHtmlRepository()
        rfc = Rfc('2397')
        make_html(rfc, RfcJsonTransFileRepository(), RfcJsonDataSummaryFileRepository(), repo)
        tree = lxml.html.fromstring(repo.find(rfc))
        self.assertFalse(tree.xpath('//img[@alt="Larry"]'))
        examples = tree.xpath('//pre[contains(., "ALT=")]')
        self.assertEqual(len(examples), 1)
        self.assertIn('<IMG\n', examples[0].text_content())


if __name__ == '__main__':
    unittest.main()

import unittest

from src.domain.valueobject.rfc.contents.paragraph import Paragraph
from tools.check_raw_prose import inspect


class ProseEllipsisTests(unittest.TestCase):
    def test_quoted_definition_is_prose_and_retains_omission(self):
        text = ('A trust anchor store is a set of one or more trust anchors stored\n'
                'in a device.... A device may have more than one trust anchor\n'
                'store, each of which may be used by one or more applications.')
        paragraph = Paragraph('      ' + text.replace('\n', '\n      '))
        self.assertFalse(paragraph.is_code)
        self.assertEqual(paragraph.indent, 6)
        self.assertIn('device.... A device', paragraph.text)
        self.assertNotIn('\n', paragraph.text)

    def test_sentence_ending_omission_is_prose(self):
        paragraph = Paragraph('The LSP_ATTRIBUTES object and the LSP_REQUIRED_ATTRIBUTES object\n'
                              'MAY be carried in a Path message....')
        self.assertFalse(paragraph.is_code)
        self.assertTrue(paragraph.text.endswith('message....'))

    def test_real_dot_leaders_and_code_are_retained(self):
        for text in (
            '1. Introduction .............. 2\n2. Overview .................. 3',
            'First heading .... 3\nSecond heading .... 7',
            'C  A1 A2         A3     LoST server name\n'
            'US NJ Atlantic   *      atlantic.nj.example.org/sos\n'
            'US NJ Bergen     *      bergen.nj.example.org/sos\n'
            'US NJ Monmouth   *      monmouth.nj.example.org/sos\n....',
            '000  10 f1 e7 e4 d1 3b 59 15 50 0f dd 1f a3 20 71 c4  .....;Y.P.... q.',
            '+-------------------------------+\n'
            '| The text is part of a diagram. |\n'
            '| It has many words and ends.... |\n'
            '+-------------------------------+',
        ):
            with self.subTest(text=text):
                self.assertTrue(Paragraph(text).is_code)

    def test_inline_numeric_and_quoted_omissions_are_prose(self):
        for text in (
            'The values for this field can be selected from the ordered sequence of integers 0, 1, 2, ....',
            'From the abstract: "This document describes a method for sending data over links....This is useful."',
            'Following the XML notation, this document uses "&#x...." to represent characters in its examples.',
        ):
            with self.subTest(text=text):
                self.assertFalse(Paragraph(text).is_code)

    def test_audit_only_flags_misclassified_prose(self):
        prose = ('A trust anchor store is a set of one or more trust anchors stored '
                 'in a device.... A device may have more than one store.')
        obj = {'number': 7925, 'contents': [
            {'text': prose, 'raw': True},
            {'text': prose, 'ja': '翻訳済み'},
            {'text': '1. Introduction .............. 2', 'raw': True, 'toc': True},
            {'text': 'Packet data....', 'raw': True},
        ]}
        self.assertEqual([r['paragraph'] for r in inspect(obj)], [0])


if __name__ == '__main__':
    unittest.main()

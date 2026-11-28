
# python3 -m unittest discover -s tests -p "test_*.py"

import unittest
from src.application.usecase.fetch_status import make_errata, parse_errata_sections


class TestParseErrataSections(unittest.TestCase):

    def test_section_numbers(self):
        cases = {
            '4.2.10.': ['4.2.10'],
            '4.3.2, B.3.2': ['4.3.2', 'B.3.2'],
            '2, 5.1, 6.3': ['2', '5.1', '6.3'],
            'Section 3 and 4.1': ['3', '4.1'],
            '8.  Security': ['8'],
            '7.2. grouping prefix': ['7.2'],
            '8.2.11 + .18': ['8.2.11'],
            'In Section 25.1:': ['25.1'],
            '10.3:': ['10.3'],
            'see Appendix B': ['B'],
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_errata_sections(text), expected)

    def test_appendix(self):
        self.assertEqual(parse_errata_sections('Appendix D.6'), ['D.6'])
        self.assertEqual(parse_errata_sections('Appendix J'), ['J'])
        self.assertEqual(parse_errata_sections('2.8 & Appx E'), ['2.8', 'E'])
        self.assertEqual(parse_errata_sections('A.5.'), ['A.5'])
        self.assertEqual(parse_errata_sections('A'), ['A'])

    def test_page_numbers_are_not_sections(self):
        self.assertEqual(parse_errata_sections('12, pg.18'), ['12'])
        self.assertEqual(parse_errata_sections('2., pg. 4'), ['2'])
        self.assertEqual(parse_errata_sections('page 2'), [])

    def test_free_text(self):
        for text in ['GLOBAL', 'IANA Conside', 'A grouping prefix', 'In the header, it says:', '']:
            with self.subTest(text=text):
                self.assertEqual(parse_errata_sections(text), [])


class TestMakeErrata(unittest.TestCase):

    def test_make_errata(self):
        obj = {'8446': {}, '5246': {}}
        errata = make_errata(obj, [
            {'errata_id': '6146', 'doc-id': 'RFC8446', 'errata_status_code': 'Verified',
             'errata_type_code': 'Technical', 'section': '4.2.10.'},
            {'errata_id': '5483', 'doc-id': 'RFC8446', 'errata_status_code': 'Held for Document Update',
             'errata_type_code': 'Editorial', 'section': 'GLOBAL'},
            {'errata_id': '6120', 'doc-id': 'RFC8446', 'errata_status_code': 'Rejected',
             'errata_type_code': 'Editorial', 'section': '1'},
            {'errata_id': '1', 'doc-id': 'FYI0036', 'errata_status_code': 'Verified',
             'errata_type_code': 'Editorial', 'section': '1'},
        ])
        self.assertEqual(errata, {'8446': [
            [5483, 'H', 'E', 'GLOBAL', []],
            [6146, 'V', 'T', '4.2.10.', ['4.2.10']],
        ]})


if __name__ == '__main__':
    unittest.main()

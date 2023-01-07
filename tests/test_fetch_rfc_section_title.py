
# python3 -m unittest discover -s tests -p "test_*.py"

import unittest
import difflib
from src.fetch_rfc import Paragraph


# --- Section Title ------------------------------------------------------------

class TestFetchRfcSectionTitle(unittest.TestCase):

    def test_section_title(self):
        p = Paragraph("1. Introduction")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_not_section_title_endswith_dot(self):
        p = Paragraph("1. Introduction.")
        self.assertNotEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_not_section_title_endswith_semicolon(self):
        p = Paragraph("1. Introduction:")
        self.assertNotEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_A_3(self): # RFC 9271
        p = Paragraph("A.3. Typical UPS Instant Commands")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_Appendix_C_colon(self): # RFC 9271
        p = Paragraph("Appendix C. Technical Terms: Historical Differences")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_hypen(self): # RFC 9240
        p = Paragraph("4.7. Defining Information Resources for Resource-Specific Property Values")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_section_title_2lines(self): # RFC 9313 (3.2.)
        p = Paragraph("3.2.  Network Address Translation among the Different IPv4aaS\n      Technologies")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_not_section_title_2lines(self): # RFC 9313 (3.2.)
        p = Paragraph("3.2.  Network Address Translation among the Different IPv4aaS\n     Technologies")
        self.assertNotEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)
        p = Paragraph("3.2.  Network Address Translation among the Different IPv4aaS\n       Technologies")
        self.assertNotEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_not_section_title_2lines_endswith_dot(self):
        p = Paragraph("3.2.  Network Address Translation among the Different IPv4aaS\n      Technologies.")
        self.assertNotEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_not_section_title_3lines(self):
        p = Paragraph("3.2.  Network Address Translation among the Different\n      IPv4aaS\n      Technologies")
        self.assertNotEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_sharp(self):  # RFC 8018
        p = Paragraph("Appendix D. Revision History of PKCS #5")
        self.assertNotEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)


if __name__ == '__main__':
    unittest.main()

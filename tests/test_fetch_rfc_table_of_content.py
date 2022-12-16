
# python3 -m unittest discover -s tests -p "test_*.py"

import unittest
import difflib
from src.fetch_rfc import Paragraph


# --- Table of Content ---------------------------------------------------------

class TestFetchRfcToc(unittest.TestCase):

    def test_toc(self): # RFC 9271
        p = Paragraph("""
        1.  Introduction
            1.1.  Current Practice
            1.1.1.  NUT Project
            1.1.2.  The Shutdown Story
            1.1.3.  How to Read this Document
            1.2.  Additional Information
            1.3.  Requirements Language
        2.  Terminology
        Appendix E.  Administrative Security
            E.1.  Management of Administrative Users
            E.2.  An Administrative User of a Client Management Daemon
            E.2.1.  An Administrative User Logs into a Short Session
            E.2.2.  An Administrative User Logs into a Long Session
        Acknowledgments
        Author's Address
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_TOC)

    def test_toc_RFC9293(self): # RFC9293
        p = Paragraph("""
           1.  Purpose and Scope
           2.  Introduction
             2.1.  Requirements Language
             2.2.  Key TCP Concepts
           Appendix B.  TCP Requirement Summary
           Acknowledgments
           Author's Address
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_TOC)


if __name__ == '__main__':
    unittest.main()

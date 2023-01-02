
# python3 -m unittest discover -s tests -p "test_*.py"

import unittest
import difflib
from src.fetch_rfc import Paragraph


# --- Sentence -----------------------------------------------------------------

class TestFetchRfcSentence(unittest.TestCase):
    maxDiff = None

    def test_sentence_hello(self):
        p = Paragraph("hello world.")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_sentence_with_newline(self):
        p = Paragraph("hello\nworld.")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_url(self):
        p = Paragraph("""
        Information about the current status of this document, any errata,
        and how to provide feedback on it may be obtained at
        http://www.rfc-editor.org/info/rfc6181.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_colon_end(self):
        p = Paragraph("Response:")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_colon(self): # RFC 9271
        p = Paragraph("Table 7: Typical Readable and Writable UPS Variables")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_semicolon(self): # RFC 9271
        p = Paragraph("""
        The character set used for commands and responses is US-ASCII; see
        [RFC0020].
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_semicolon2(self): # RFC 9298
        p = Paragraph("""
        The lifetime of the socket is tied to the request stream.  The UDP
        proxy MUST keep the socket open while the request stream is open.  If
        a UDP proxy is notified by its operating system that its socket is no
        longer usable, it MUST close the request stream.  For example, this
        can happen when an ICMP Destination Unreachable message is received;
        see Section 3.1 of [ICMP6].  UDP proxies MAY choose to close sockets
        due to a period of inactivity, but they MUST close the request stream
        when closing the socket.  UDP proxies that close sockets after a
        period of inactivity SHOULD NOT use a period lower than two minutes;
        see Section 4.3 of [BEHAVE].
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_square_brackets(self): # RFC 9307
        p = Paragraph("""
        There is a wide range of tools to analyze this data produced by IETF
        participants or researchers interested in the work of the IETF.  Two
        projects that presented their work at the workshop were BigBang
        [BigBang] and Sodestream's IETFdata [ietfdata] library.  The RFC
        Prolog Database was described in a submitted paper; see
        [Prolog-Database].  These projects could provide additional insight
        into existing IETF statistics [ArkkoStats] and datatracker statistics
        [DatatrackerStats], e.g., gender-related information.  Privacy issues
        and the implications of making such data publicly available were
        discussed as well.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_hypens_underscore(self): # RFC 9271
        p = Paragraph("""
        Although "_", "-", "__--" are valid entity domain types, it is
        desirable to add characters, such as alphanumeric ones, for better
        intelligibility.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_hypens_equals(self): # RFC 9271
        p = Paragraph("""
        The reference configuration in Figure 1 shows a single UPS unit that
        has a power supply link (===) and a data link (---) attached to a
        system running an Attachment Daemon.  The UPS provides power supply
        protection to the system running the Attachment Daemon.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_slash_aster(self): # RFC 9239
        p = Paragraph("""
        In order to ensure interoperability and align with widespread
        implementation practices, the charset parameter is optional rather
        than required, despite the recommendation in BCP 13 [RFC6838] for
        text/* types.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_colon_colon_equal(self):
        p = Paragraph("""
        Each entity domain is identified by a unique entity domain name.
        Borrowing the symbol "::=" from the Backus-Naur Form notation
        [RFC5511], the format of an entity domain name is defined as follows:
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_quote_colon_quote_equal(self): # RFC 2622
        p = Paragraph("""
        integers seperated by \":\" to partition the community number space so that a provider can use its AS number as the first two bytes, and assigns a semantics of its choice to the last two bytes.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_copyright(self):
        p = Paragraph("""
        This document is subject to BCP 78 and the IETF Trust's Legal
        Provisions Relating to IETF Documents
        (http://trustee.ietf.org/license-info) in effect on the date of
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_reference(self):
        p = Paragraph("""
        [TA-MGMT]  Reynolds, M. and S. Kent, "Local Trust Anchor Management
                   for the Resource Public Key Infrastructure", Work in
                   Progress, December 2011.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_note_online(self): # RFC 9271
        p = Paragraph("""
        |  Note: Historically, the Primary was known as the "Master".
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)
        self.assertEqual(p.text, """
        Note: Historically, the Primary was known as the "Master".
        """.strip())

    def test_note(self): # RFC 9271
        p = Paragraph("""
        |  Note: Should the Primary fail or go offline, the fate of the
        |  Secondaries depends on the UPS status when the Primary failed.
        |  If the UPS had status OL, the Secondary continues operation,
        |  but if the UPS had status OB, the Secondary may choose to shut
        |  down as a precaution.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_implementation_note(self): # RFC 9271
        p = Paragraph("""
        |  _Implementation note:_ In the current implementation, the names
        |  of commands and subcommands are not case sensitive.  For
        |  example, GET VAR may be written as Get var, but in this
        |  specification, they are always written in uppercase.
        |  Similarly, <upsname> and <varname> are not case sensitive.  For
        |  example, UPS341 ups.id may be written as ups341 Ups.Id, but in
        |  this specification, <varname> is always written in lower case.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)

    def test_ul_li(self): # RFC 9271
        p = Paragraph("""
        *  upsc reports the values of the variables defined for a given UPS;
           see Table 6.
        *  upsrw reports on and changes the values of the readable and
           writable configuration variables defined for a given UPS; see
           Appendix A.2.
        *  upscmd reports on and executes the instant action commands defined
           for a given UPS; see Section 4.2.6.
        *  UPSmon.py is an experimental Python3 rewrite of upsmon and
           upssched that includes support for TLS 1.3 [RFC8446].
        """.strip('\n'))
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)
        self.assertEqual(p.text, """
* upsc reports the values of the variables defined for a given UPS; see Table 6.

* upsrw reports on and changes the values of the readable and writable configuration variables defined for a given UPS; see Appendix A.2.

* upscmd reports on and executes the instant action commands defined for a given UPS; see Section 4.2.6.

* UPSmon.py is an experimental Python3 rewrite of upsmon and upssched that includes support for TLS 1.3 [RFC8446].
        """.strip('\n').rstrip())

    def test_ul_li_with_signs(self): # RFC 9271
        p = Paragraph("""
        *  <ups> is defined by the Attachment Daemon configuration files.
        *  The default <hostname> is localhost.
        *  The <port> is the number of the TCP port on which the Attachment
           Daemon is listening.  The default is 3493.  This is supported by
           all current Management Daemons.
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SENTENCE)
        self.assertEqual(p.text, """
* <ups> is defined by the Attachment Daemon configuration files.

* The default <hostname> is localhost.

* The <port> is the number of the TCP port on which the Attachment Daemon is listening. The default is 3493. This is supported by all current Management Daemons.
        """.strip())


if __name__ == '__main__':
    unittest.main()


import unittest
import difflib
from src.fetch_rfc import Paragraph


class TestFetchRfcSectionTitle(unittest.TestCase):

    def test_A_3(self): # RFC 9271
        p = Paragraph("A.3. Typical UPS Instant Commands")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_Appendix_C_colon(self): # RFC 9271
        p = Paragraph("Appendix C. Technical Terms: Historical Differences")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)

    def test_hypen(self): # RFC 9240
        p = Paragraph("4.7. Defining Information Resources for Resource-Specific Property Values")
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_SECTIOIN_TITLE)


# --- Sentence -----------------------------------------------------------------

class TestFetchRfcSentence(unittest.TestCase):
    maxDiff = None

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


# --- Code ---------------------------------------------------------------------

class TestFetchRfcCode(unittest.TestCase):

    def test_command(self): # RFC 9271
        p = Paragraph("""
        Command: ATTACH <upsname>
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_command_with_dots(self): # RFC 9271
        p = Paragraph("""
        Response: TYPE <upsname> <varname> <type>...
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_command_response(self): # RFC 9271
        p = Paragraph("""
        BEGIN LIST CMD <upsname>
        CMD <upsname> <cmdname>
        ...
        END LIST CMD <upsname>
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_colon_colon_equal(self): # RFC 9240
        p = Paragraph("""
        EntityID ::= EntityDomainName ':' DomainTypeSpecificEntityID
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_definitions(self): # RFC 9239
        p = Paragraph("""
        Additional information:
           Deprecated alias names for this type:  application/javascript,
              application/x-javascript, text/javascript1.0, text/
              javascript1.1, text/javascript1.2, text/javascript1.3, text/
              javascript1.4, text/javascript1.5, text/jscript, text/
              livescript
           Magic number(s):  N/A
           File extension(s):  .js, .mjs
           Macintosh File Type Code(s):  TEXT
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_struct(self): # RFC 9240
        p = Paragraph("""
        object {
          EntityPropertyMapping mappings;
        } PropertyMapCapabilities;
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_http(self): # RFC 9230
        p = Paragraph("""
        :method = POST
        :scheme = https
        :authority = dnsproxy.example
        :path = /dns-query?targethost=dnstarget.example&targetpath=/dns-query
        accept = application/oblivious-dns-message
        content-type = application/oblivious-dns-message
        content-length = 106
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_table(self): # RFC 9271
        p = Paragraph("""
        +========================+============+=========================+
        |        Variable        |  Typical   |   Default Description   |
        |                        |   Value    | Provided as Response to |
        |                        |            |   the Command GET DESC  |
        +========================+============+=========================+
        | battery.charge.low     | 20         | "Remaining battery      |
        |                        |            | level when UPS switches |
        |                        |            | to LB (percent)"        |
        +------------------------+------------+-------------------------+
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)


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


if __name__ == '__main__':
    unittest.main()


# python3 -m unittest discover -s tests -p "test_*.py"

import unittest
import difflib
from src.fetch_rfc import Paragraph


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

    def test_struct2(self): # RFC 9298
        p = Paragraph("""
        UDP Proxying HTTP Datagram Payload {
          Context ID (i),
          UDP Proxying Payload (..),
        }
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

    def test_http2_header(self): # RFC 9298
        p = Paragraph("""
        HEADERS
        :status = 200
        capsule-protocol = ?1
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_http2_long_header(self): # RFC 9298
        p = Paragraph("""
        HEADERS
        :method = CONNECT
        :protocol = connect-udp
        :scheme = https
        :path = /.well-known/masque/udp/192.0.2.6/443/
        :authority = example.org
        capsule-protocol = ?1
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

    def test_table_without_lines(self): # RFC 6495
        p = Paragraph("""
           Name Type      Description
            0              Reserved
            3              SHA-1 Subject Key Identifier (SKI)
            4              SHA-224 Subject Key Identifier (SKI)
            5              SHA-256 Subject Key Identifier (SKI)
            6              SHA-384 Subject Key Identifier (SKI)
            7              SHA-512 Subject Key Identifier (SKI)
            253-254        Experimental
            255            Reserved
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_figure_flow(self):  # RFC 3830
        p = Paragraph("""
        I_MESSAGE =
        HDR, T, RAND, [IDi],[IDr],
             {SP}, KEMAC                --->
                                                    R_MESSAGE =
                                       [<---]       HDR, T, [IDr], V
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_BNF(self): # RFC 9298
        p = Paragraph("""
        target_host = IPv6address / IPv4address / reg-name
        target_port = port
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_BNF_2(self): # RFC 6497
        p = Paragraph("""
        lang      = language                 ; BCP 47, with restrictions
                  ["-" script]
                  ["-" region]
                  *("-" variant)
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_BNF_3(self): # RFC 6203
        p = Paragraph("""
        capability         =/ "SEARCH=FUZZY"
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_BNF_4(self): # RFC 6193
        p = Paragraph("""
        attribute                 =/ psk-fingerprint-attribute
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)

    def test_BNF_5(self): # RFC 6193
        p = Paragraph("""
        psk-fingerprint-attribute = "psk-fingerprint" ":" hash-func SP
                                    psk-fingerprint
        """)
        self.assertEqual(p.get_text_type(), Paragraph.TYPE_CODE)


if __name__ == '__main__':
    unittest.main()

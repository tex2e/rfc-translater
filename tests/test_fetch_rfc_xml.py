
# python3 -m unittest discover -s tests -p "test_*.py"

import unittest
from pprint import pprint
from src.domain.services.fetch_rfc_xml import generate_text_writer
from src.domain.models.rfc.contents.content import Content


class TestFetchXmlRfc(unittest.TestCase):

    def test_rfc_front_abstract_t(self):
        self.maxDiff = None
        xml = b'''
        <rfc xmlns:xi="http://www.w3.org/2001/XInclude" version="3" docName="draft-ietf-add-dnr-16" number="9463" submissionType="IETF" category="std" consensus="true" ipr="trust200902" tocInclude="true" tocDepth="4" symRefs="true" sortRefs="true" updates="" obsoletes="" xml:lang="en" prepTime="2023-11-06T13:16:37" indexInclude="true" scripts="Common,Latin">
        <link href="https://datatracker.ietf.org/doc/draft-ietf-add-dnr-16" rel="prev"/>
        <link href="https://dx.doi.org/10.17487/rfc9463" rel="alternate"/>
        <link href="urn:issn:2070-1721" rel="alternate"/>
        <front>
        <title abbrev="DNR">DHCP and Router Advertisement Options for the Discovery of Network-designated Resolvers (DNR)</title>
        <date month="11" year="2023"/>
        <abstract pn="section-abstract">
            <t indent="0" pn="section-abstract-1">This document specifies new DHCP and IPv6 Router Advertisement options
            to discover encrypted DNS resolvers (e.g., DNS over HTTPS, DNS over TLS,
            and DNS over QUIC).</t>
        </abstract>
        </front>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        self.assertGreaterEqual(len(actual), 2)
        actual = actual[-2:]  # ページトップを除いた末尾2要素のみ取得
        excepted = [
            Content(text='Abstract', section_title=True),
            Content(text='This document specifies new DHCP and IPv6 Router Advertisement options to discover encrypted DNS resolvers (e.g., DNS over HTTPS, DNS over TLS, and DNS over QUIC).', indent=3)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_front_toc(self):
        self.maxDiff = None
        xml = b'''
        <rfc xmlns:xi="http://www.w3.org/2001/XInclude" version="3" docName="draft-ietf-add-dnr-16" number="9463" submissionType="IETF" category="std" consensus="true" ipr="trust200902" tocInclude="true" tocDepth="4" symRefs="true" sortRefs="true" updates="" obsoletes="" xml:lang="en" prepTime="2023-11-06T13:16:37" indexInclude="true" scripts="Common,Latin">
        <link href="https://datatracker.ietf.org/doc/draft-ietf-add-dnr-16" rel="prev"/>
        <link href="https://dx.doi.org/10.17487/rfc9463" rel="alternate"/>
        <link href="urn:issn:2070-1721" rel="alternate"/>
        <front>
        <title abbrev="DNR">DHCP and Router Advertisement Options for the Discovery of Network-designated Resolvers (DNR)</title>
        <date month="11" year="2023"/>
        <toc>
        <section anchor="toc" numbered="false" removeInRFC="false" toc="exclude" pn="section-toc.1">
            <name slugifiedName="name-table-of-contents">Table of Contents</name>
            <ul bare="true" empty="true" indent="2" spacing="compact" pn="section-toc.1-1">
                <li pn="section-toc.1-1.1">
                    <t indent="0" pn="section-toc.1-1.1.1"><xref derivedContent="1" format="counter" sectionFormat="of" target="section-1"/>. <xref derivedContent="" format="title" sectionFormat="of" target="name-overview">Overview</xref></t>
                    <ul bare="true" empty="true" indent="2" spacing="compact" pn="section-toc.1-1.1.2">
                        <li pn="section-toc.1-1.1.2.1">
                            <t indent="0" keepWithNext="true" pn="section-toc.1-1.1.2.1.1"><xref derivedContent="1.1" format="counter" sectionFormat="of" target="section-1.1"/>. <xref derivedContent="" format="title" sectionFormat="of" target="name-document-structure">Document Structure</xref></t>
                        </li>
                        <li pn="section-toc.1-1.1.2.2">
                            <t indent="0" keepWithNext="true" pn="section-toc.1-1.1.2.2.1"><xref derivedContent="1.2" format="counter" sectionFormat="of" target="section-1.2"/>. <xref derivedContent="" format="title" sectionFormat="of" target="name-terms-and-definitions">Terms and Definitions</xref></t>
                        </li>
                    </ul>
                </li>
                <li pn="section-toc.1-1.2">
                    <t indent="0" pn="section-toc.1-1.2.1"><xref derivedContent="2" format="counter" sectionFormat="of" target="section-2"/>. <xref derivedContent="" format="title" sectionFormat="of" target="name-streams">Streams</xref></t>
                </li>
            </ul>
        </section>
        </toc>
        </front>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        self.assertGreaterEqual(len(actual), 2)
        actual = actual[-2:]  # ページトップを除いた末尾2要素のみ取得
        excepted = [
            Content(text='Table of Contents', section_title=True, indent=0),
            Content(text='1.  Overview\n  1.1.  Document Structure\n  1.2.  Terms and Definitions\n2.  Streams', indent=3, raw=True, toc=True)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_name(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section anchor="intro" numbered="true" removeInRFC="false" toc="include" pn="section-2">
            <name slugifiedName="name-introduction">Terminology</name>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='2. Terminology', section_title=True, indent=0)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_t(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <t indent="0" pn="section-1-1">This document focuses on the discovery of encrypted DNS.</t>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='This document focuses on the discovery of encrypted DNS.', indent=3)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_name_and_t(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section anchor="intro" numbered="true" removeInRFC="false" toc="include" pn="section-1">
            <name slugifiedName="name-introduction">Introduction</name>
            <t indent="0" pn="section-1-1">This document focuses on the discovery of encrypted DNS.</t>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='1. Introduction', section_title=True, indent=0),
            Content(text='This document focuses on the discovery of encrypted DNS.', indent=3)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_aside(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <aside pn="section-3-4">
                <t indent="0" pn="section-3-4.1">Note: In some cases, a single event or action can cause a transition through multiple states.</t>
            </aside>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='Note: In some cases, a single event or action can cause a transition through multiple states.', indent=12),
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_figure_arwtork(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <figure anchor="fig-stream-send-states" align="left" suppress-title="false" pn="figure-2">
            <name slugifiedName="name-states-for-sending-parts-of">States for Sending Parts of Streams</name>
            <artwork name="" type="" align="left" alt="" pn="section-3.1-2.1">
    +-------+    +-------+
    | Data  |    | Reset |
    | Recvd |    | Recvd |
    +-------+    +-------+
            </artwork>
            </figure>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text=
                    '+-------+    +-------+\n'+
                    '| Data  |    | Reset |\n'+
                    '| Recvd |    | Recvd |\n'+
                    '+-------+    +-------+', raw=True, indent=7),
            Content(text="Figure 2: States for Sending Parts of Streams", indent=15)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_arwtork(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <artwork name="" type="" align="left" alt="" pn="section-3.1-2.1">
    a*x + b*y = c
            </artwork>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='a*x + b*y = c', raw=True, indent=7),
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_table_t(self):  # RFC 9435
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
        <table anchor="table6" align="center" pn="table-6">
          <name slugifiedName="name-the-phb-mapping-recommended">The PHB Mapping Recommended in the Guidelines Recommended in <xref target="GSMA-IR.34" format="default" sectionFormat="of" derivedContent="GSMA-IR.34"/></name>
          <thead>
            <tr>
              <th align="left" colspan="1" rowspan="1">
                <t indent="0" pn="section-5.3-3.1.1.0.1">QoS Class in <xref target="GSMA-IR.34" format="default" sectionFormat="of" derivedContent="GSMA-IR.34"/></t>
              </th>
              <th align="left" colspan="1" rowspan="1">PHB</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td rowspan="4" align="left" colspan="1">
                <t indent="0" pn="section-5.3-3.2.3.1.1">Interactive</t>
                <t indent="0" pn="section-5.3-3.2.3.1.2">(ordered by priority, AF3 highest)</t>
              </td>
              <td align="left" colspan="1" rowspan="1">AF31</td>
            </tr>
            <tr>
              <td align="left" colspan="1" rowspan="1">AF32</td>
            </tr>
            <tr>
              <td align="left" colspan="1" rowspan="1">AF21</td>
            </tr>
            <tr>
              <td align="left" colspan="1" rowspan="1">AF11</td>
            </tr>
          </tbody>
        </table>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text=
                    '+====================================+======+\n'+
                    '| QoS Class in GSMA-IR.34            | PHB  |\n'+
                    '+====================================+======+\n'+
                    '| Interactive                        | AF31 |\n'+
                    '|                                    +------+\n'+
                    '| (ordered by priority, AF3 highest) | AF32 |\n'+
                    '|                                    +------+\n'+
                    '|                                    | AF21 |\n'+
                    '|                                    +------+\n'+
                    '|                                    | AF11 |\n'+
                    '+------------------------------------+------+', raw=True, indent=15),
            Content(text="Table 6: The PHB Mapping Recommended in the Guidelines Recommended in GSMA-IR.34", indent=18),
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_back_section_figure_artset(self):  # RFC 9389
        self.maxDiff = None
        xml = '''
        <rfc>
        <back>
        <section anchor="capture-math" numbered="true" removeInRFC="false" toc="include" pn="section-appendix.a">
            <figure anchor="peq1" align="left" suppress-title="false" pn="figure-3">
                <artset pn="section-appendix.a-3.1">
                <artwork align="center" type="svg" pn="section-appendix.a-3.1.1"><svg xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://www.w3.org/2000/svg" height="6.176ex" role="img" viewBox="0 -1580.7 7512 2659.1" width="17.447ex">
                    <defs>
                        <path d="M304 -161l-12 -16c-158 90 -244 259 -244 429c0 185 87 329 247 424l9 -16c-139 -119 -170 -212 -170 -405c0 -186 30 -299 170 -416Z" id="E1-STIXWEBMAIN-28-gensym001" stroke-width="1"/>
                    </defs>
                    <g fill="black" stroke="currentColor" stroke-width="0" transform="matrix(1 0 0 -1 0 0)">
                    </g>
                    </svg>
                </artwork>
                <artwork type="ascii-art" align="center" pn="section-appendix.a-3.1.2">⎛a⎞      a!
⎜ ⎟ = ────────
⎝b⎠   (a-b)!b!
</artwork>
                </artset>
            </figure>
        </section>
        </back>
        </rfc>
        '''.encode('utf-8')
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text=
                    '⎛a⎞      a!\n'+
                    '⎜ ⎟ = ────────\n'+
                    '⎝b⎠   (a-b)!b!\n'+
                    '\n'+
                    '    Figure 3', raw=True, indent=27),
        ]
        self.assertEqual(actual, excepted)


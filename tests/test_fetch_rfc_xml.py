
# python3 -m unittest discover -s tests -p "test_*.py"

import unittest
from pprint import pprint
from src.fetch_rfc_xml import generate_text_writer, Content

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

    def test_rfc_middle_section_t_and_ul_li(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <t indent="0" pn="section-5.3-2">When implementing the client role, an application protocol can:</t>
            <ul spacing="normal" bare="false" empty="false" indent="3" pn="section-5.3-3">
                <li pn="section-5.3-3.1">open a connection, which begins the exchange described in <xref target="handshake" format="default" sectionFormat="of" derivedContent="Section 7"/>;</li>
                <li pn="section-5.3-3.2">enable Early Data when available; and</li>
                <li pn="section-5.3-3.3">be informed when Early Data has been accepted or rejected by a server.</li>
            </ul>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='When implementing the client role, an application protocol can:', indent=3),
            Content(text='* open a connection, which begins the exchange described in Section 7;', indent=6),
            Content(text='* enable Early Data when available; and', indent=6),
            Content(text='* be informed when Early Data has been accepted or rejected by a server.', indent=6)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_ul_li_ul_li(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <ul spacing="normal" bare="false" empty="false" indent="3" pn="section-5.3-3">
                <li pn="section-5.3-3.1">Item1</li>
                <li pn="section-5.3-3.2">Item2</li>
                <ul spacing="normal" bare="false" empty="false" indent="3" pn="section-5.3-3.2">
                    <li pn="section-5.3-3.1-1">Item2-1</li>
                    <li pn="section-5.3-3.2-1">Item2-2</li>
                </ul>
                <li pn="section-5.3-3.3">Item3</li>
            </ul>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='* Item1', indent=6),
            Content(text='* Item2', indent=6),
            Content(text='- Item2-1', indent=12),
            Content(text='- Item2-2', indent=12),
            Content(text='* Item3', indent=6)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_ol_li(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <ol spacing="normal" type="1" indent="adaptive" start="1" pn="section-21.1.3.1-8">
                <li pn="section-5.3-3.1" derivedCounter="1.">Item1</li>
                <li pn="section-5.3-3.2" derivedCounter="2.">Item2</li>
                <li pn="section-5.3-3.3" derivedCounter="3.">Item3</li>
            </ol>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='1. Item1', indent=8),
            Content(text='2. Item2', indent=8),
            Content(text='3. Item3', indent=8)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_ol_li_ol_li(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <ol spacing="normal" type="1" indent="adaptive" start="1" pn="section-21.1.3.1-8">
                <li pn="section-5.3-3.1" derivedCounter="1.">Item1</li>
                <li pn="section-5.3-3.2" derivedCounter="2.">Item2</li>
                <ol spacing="normal" type="1" indent="adaptive" start="1" pn="section-21.1.3.1-8">
                    <li pn="section-5.3-3.1-1" derivedCounter="a.">Item2-1</li>
                    <li pn="section-5.3-3.2-1" derivedCounter="b.">Item2-2</li>
                </ol>
                <li pn="section-5.3-3.3" derivedCounter="3.">Item3</li>
            </ol>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='1. Item1', indent=8),
            Content(text='2. Item2', indent=8),
            Content(text='a. Item2-1', indent=16),
            Content(text='b. Item2-2', indent=16),
            Content(text='3. Item3', indent=8)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_dl(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <dl spacing="compact" indent="3" newline="false" pn="section-22.1.1-5">
                <dt pn="section-22.1.1-5.1">Value:</dt>
                <dd pn="section-22.1.1-5.2">
                <t indent="0" pn="section-22.1.1-5.2.1">The assigned codepoint.</t>
                </dd>
            </dl>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='Value:', indent=3),
            Content(text='The assigned codepoint.', indent=12)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_ul_li_dl(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <ul spacing="normal" bare="false" empty="false" indent="3" pn="section-5.3-3">
                <li pn="section-5.3-3.1">Item1</li>
                <li pn="section-5.3-3.2">Item2</li>
                <dl spacing="compact" indent="3" newline="false" pn="section-22.1.1-5">
                    <dt pn="section-22.1.1-5.1">Value:</dt>
                    <dd pn="section-22.1.1-5.2">
                    <t indent="0" pn="section-22.1.1-5.2.1">The assigned codepoint.</t>
                    </dd>
                </dl>
                <li pn="section-5.3-3.3">Item3</li>
            </ul>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='* Item1', indent=6),
            Content(text='* Item2', indent=6),
            Content(text='Value:', indent=6),
            Content(text='The assigned codepoint.', indent=15),
            Content(text='* Item3', indent=6)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_dl_dd_dl_dd(self):  # RFC 9525
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <dl indent="3" newline="false" spacing="normal" pn="section-1.5-2">
                <dt pn="section-1.5-2.9">identifier type:</dt>
                <dd pn="section-1.5-2.10">
                    <t indent="0" pn="section-1.5-2.10.1">A formally defined category of identifier.</t>
                    <dl spacing="normal" indent="3" newline="false" pn="section-1.5-2.10.2">
                        <dt pn="section-1.5-2.10.2.1">DNS-ID:</dt>
                        <dd pn="section-1.5-2.10.2.2"> A subjectAltName entry of type dNSName as defined in <xref target="RFC5280" format="default" sectionFormat="of" derivedContent="PKIX"/>.</dd>
                    </dl>
                </dd>
            </dl>
        </section>
        </middle>
        </rfc>
        '''
        text_writer = generate_text_writer(xml)
        text_writer.process()
        actual = text_writer._contents
        excepted = [
            Content(text='identifier type:', indent=3),
            Content(text='A formally defined category of identifier.', indent=12),
            Content(text='DNS-ID:', indent=6),
            Content(text='A subjectAltName entry of type dNSName as defined in PKIX.', indent=15),
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
            Content(text='+-------+    +-------+\n| Data  |    | Reset |\n| Recvd |    | Recvd |\n+-------+    +-------+', raw=True, indent=7),
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

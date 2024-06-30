
# python3 -m unittest discover -s tests -p "test_*.py"

import unittest
from pprint import pprint
from src.domain.services.fetch_rfc_xml import generate_text_writer
from src.domain.models.rfc.contents.content import Content


class TestFetchXmlRfcUnorderdOrderdDefinitionList(unittest.TestCase):

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

    def test_rfc_middle_section_ul_li_t(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <ul spacing="normal" bare="false" empty="false" indent="3" pn="section-5.3-3">
                <li pn="section-5.3-3.1">
                    <t indent="0" pn="section-6.1-2.1.1">ItemA</t>
                    <t indent="0" pn="section-6.1-2.1.2">ItemB</t>
                </li>
                <li pn="section-5.3-3.2">
                    <t indent="0" pn="section-6.1-2.2.1">ItemC</t>
                    <t indent="0" pn="section-6.1-2.2.2">ItemD</t>
                </li>
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
            Content(text='* ItemA', indent=6),
            Content(text='ItemB', indent=10),
            Content(text='* ItemC', indent=6),
            Content(text='ItemD', indent=10),
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

    def test_rfc_middle_section_ol_li_t(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <ol spacing="normal" type="1" indent="adaptive" start="1" pn="section-21.1.3.1-8">
                <li pn="section-5.3-3.1" derivedCounter="1.">
                    <t indent="0" pn="section-6.1-2.1.1">ItemA</t>
                    <t indent="0" pn="section-6.1-2.1.2">ItemB</t>
                </li>
                <li pn="section-5.3-3.2" derivedCounter="2.">
                    <t indent="0" pn="section-6.1-2.2.1">ItemC</t>
                    <t indent="0" pn="section-6.1-2.2.2">ItemD</t>
                </li>
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
            Content(text='1. ItemA', indent=8),
            Content(text='ItemB', indent=12),
            Content(text='2. ItemC', indent=8),
            Content(text='ItemD', indent=12),
            Content(text='3. Item3', indent=8)
        ]
        self.assertEqual(actual, excepted)

    def test_rfc_middle_section_ol_li_ul_li_t(self):
        self.maxDiff = None
        xml = b'''
        <rfc>
        <middle>
        <section>
            <ol spacing="normal" type="1" indent="adaptive" start="1" pn="section-21.1.3.1-8">
                <li pn="section-5.3-3.1" derivedCounter="1.">
                    <t indent="0" pn="section-6.1-2.1.1">Item1-1</t>
                    <t indent="0" pn="section-6.1-2.1.2">Item1-2</t>
                    <ul spacing="normal" bare="false" empty="false" indent="3" pn="section-6.2-2.5.3">
                        <li pn="section-6.2-2.5.3.1">First</li>
                        <li pn="section-6.2-2.5.3.2">Second</li>
                    </ul>
                </li>
                <li pn="section-5.3-3.2" derivedCounter="2.">
                    <t indent="0" pn="section-6.1-2.2.1">Item2-1</t>
                    <t indent="0" pn="section-6.1-2.2.2">Item2-2</t>
                </li>
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
            Content(text='1. Item1-1', indent=8),
            Content(text='Item1-2', indent=12),
            Content(text='* First', indent=14),
            Content(text='* Second', indent=14),
            Content(text='2. Item2-1', indent=8),
            Content(text='Item2-2', indent=12),
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

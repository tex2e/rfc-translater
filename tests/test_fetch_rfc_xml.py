
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

    def test_rfc_middle_section_name(self):
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

    def test_rfc_middle_section_name_and_t(self):
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


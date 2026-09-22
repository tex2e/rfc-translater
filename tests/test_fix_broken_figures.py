import unittest

from tools.fix_broken_figures import (
    Finding,
    filter_message_flow_neighbors,
    message_flow_reason,
)


def finding(index, text, reason):
    return Finding(index, [reason], text, 0, text, 0, 'translated')


class TestMessageFlowNeighbors(unittest.TestCase):

    def test_reason_is_limited_to_eap_tls_tlv_arrows(self):
        self.assertEqual(
            message_flow_reason('<- EAP-Request/EAP-FAST (S=1, A-ID)'),
            'message-flow')
        self.assertEqual(
            message_flow_reason('Client -> Server (TLS client_hello)'),
            'message-flow')
        self.assertEqual(message_flow_reason('Result TLV (Success) ->'),
                         'message-flow')
        self.assertIsNone(message_flow_reason('FEC1 -> Label A mapping'))
        self.assertIsNone(message_flow_reason('caller() -> result'))

    def test_notes_require_raw_seed_and_protocol_message(self):
        contents = [
            {'text': 'diagram header', 'raw': True},
            {'text': '// identity sent in the clear'},
            {'text': '<- EAP-Request/EAP-FAST'},
            {'text': 'TLS channel established'},
            {'text': 'EAP-Response/EAP-FAST ->'},
            {'text': 'ordinary prose'},
        ]
        findings = [
            finding(1, contents[1]['text'], 'message-flow-note'),
            finding(2, contents[2]['text'], 'message-flow'),
            finding(3, contents[3]['text'], 'message-flow-note'),
            finding(4, contents[4]['text'], 'message-flow'),
        ]

        self.assertEqual(
            [f.index for f in filter_message_flow_neighbors(contents, findings)],
            [1, 2, 3, 4])

    def test_comment_only_component_does_not_propagate_from_raw_code(self):
        contents = [
            {'text': 'code', 'raw': True},
            {'text': '// ordinary code comment'},
        ]
        findings = [finding(1, contents[1]['text'], 'message-flow-note')]

        self.assertEqual(filter_message_flow_neighbors(contents, findings), [])

    def test_section_title_stops_propagation(self):
        contents = [
            {'text': 'diagram header', 'raw': True},
            {'text': '<- EAP-Request'},
            {'text': 'Next Section', 'section_title': True},
            {'text': 'EAP-Response ->'},
        ]
        findings = [
            finding(1, contents[1]['text'], 'message-flow'),
            finding(3, contents[3]['text'], 'message-flow'),
        ]

        self.assertEqual(
            [f.index for f in filter_message_flow_neighbors(contents, findings)],
            [1])

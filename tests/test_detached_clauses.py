import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from check_detached_clauses import inspect, introduced


def body(text, ja, **flags):
    return {"text": text, "ja": ja, "indent": 3, **flags}


def findings(*contents):
    return list(inspect({"contents": contents}))


class TestDetachedClauses(unittest.TestCase):

    def test_iv_examples_preserve_hex_values_and_order(self):
        source = ('The sender sends packets with the following IVs: '
                  '0x0100000000000001, 0x0100000000000002, '
                  'with a final value of 0x01FFFFFFFFFFFFFF.')
        correct = 'IVは0x0100000000000001、0x0100000000000002で、最後は0x01ffffffffffffffです。'
        self.assertEqual(findings(body(source, correct)), [])
        for wrong in (correct.replace('0x0100000000000001', '0x010000000000000001'),
                      correct.replace('0x0100000000000001、', ''),
                      correct.replace('0x0100000000000001、0x0100000000000002',
                                      '0x0100000000000002、0x0100000000000001')):
            row = body(source, wrong)
            self.assertEqual([f.kind for f in findings(row)], ['hex-iv-values'])
            self.assertEqual(findings({**row, 'raw': True}), [])
        self.assertEqual(findings(body('An IV is an initialization vector.', '初期化ベクトルです。')), [])

    def test_hex_default_preserves_digits_and_byte_order(self):
        source = 'The default value is 0x55AA55AA55AA55BB.'
        good = body(source, 'デフォルト値は0x55aa55aa55aa55bbです。')
        bad = body(source, 'デフォルト値は0x555AA555555555BBです。')
        self.assertEqual(findings(good), [])
        self.assertEqual([(f.kind, f.fragment) for f in findings(bad)],
                         [('hex-default-value', '0x55AA55AA55AA55BB')])
        self.assertEqual(findings({**bad, 'raw': True}), [])
        sequence = 'The default value is 0x63 0x69 0x73.'
        self.assertEqual(findings(body(sequence, '値は0x63、0x69、0x73です。')), [])
        self.assertEqual([f.kind for f in findings(body(sequence, '値は0x69 0x63 0x73です。'))],
                         ['hex-default-value'])
        self.assertEqual(findings(body(source.replace('default value', 'example value'), '例です。')), [])

    def test_compressed_port_restoration_preserves_addition(self):
        for direction in ('source', 'destination'):
            source = f'The actual 16-bit {direction} port is obtained by calculating: P + short_port value.'
            for translation in ('P + short_portを計算します。', 'Pとshort_portの値の和です。',
                                'Pにshort_portを加えて求めます。'):
                self.assertEqual(findings(body(source, translation)), [])
            for translation in ('PSHORT_PORT値を使います。', 'P - short_portを計算します。'):
                wrong = body(source, translation)
                self.assertEqual([(f.kind, f.fragment) for f in findings(wrong)],
                                 [('short-port-formula', 'P + short_port')])
                self.assertEqual(findings({**wrong, 'raw': True}), [])
            self.assertEqual(findings(body(source.replace('P + short_port', 'Q + short_port'),
                                           '別の式を使用します。')), [])

    def test_link_layer_option_length_preserves_each_addend(self):
        source = ('option-len 12 + link-layer-len field value + length of LLaddr-options field. '
                  'With no extra options and an address length of 6, the option-len is 18.')
        for translation in (
            'option-len：12 + link-layer-lenフィールドの値 + LLaddr-optionsフィールドの長さです。',
            'option-lenは12にlink-layer-lenの値とLLaddr-optionsの長さを加えた値です。',
        ):
            self.assertEqual(findings(body(source, translation)), [])
        for translation in (
            'option-len：12 + link-layer-lenフィールドの値です。',
            'option-len：12 - link-layer-lenフィールドの値 + LLaddr-optionsフィールドの長さです。',
            'option-len：112 + link-layer-lenの値 + LLaddr-optionsの長さです。',
        ):
            wrong = body(source, translation)
            self.assertEqual([f.kind for f in findings(wrong)], ['lladdr-option-length'])
            self.assertEqual(findings({**wrong, 'raw': True}), [])

    def test_ipp_language_length_checks_both_field_lengths(self):
        source = 'The length of a textWithLanguage value MUST be 4 + the value of field a + the value of field c.'
        symbolic = body(source, '長さは4 + フィールドaの値 + フィールドcの値でなければなりません (MUST)。')
        prose = body(source, '長さは4にフィールドaとフィールドcの値を加えた値でなければなりません (MUST)。')
        wrong = body(source, '長さは4でなければなりません (MUST)。フィールドaとフィールドcの値。')
        self.assertEqual(findings(symbolic, prose), [])
        self.assertEqual([f.kind for f in findings(wrong)], ['ipp-language-length'])
        self.assertEqual(findings({**wrong, 'raw': True}), [])

    def test_dns_query_example_checks_missing_class_and_final_dot(self):
        source = 'QNAME=host1.example., QTYPE=MX, QCLASS=IN because host1.example. exists.'
        correct = body(source, 'QNAME=host1.example.、QTYPE=MX、QCLASS=IN の問い合わせです。')
        wrong = {**correct, 'ja': 'QNAME=host1.example、QTYPE=MX の問い合わせです。'}
        self.assertEqual(findings(correct), [])
        self.assertEqual([(f.kind, f.fragment) for f in findings(wrong)],
                         [('dns-query-fields', 'QCLASS=IN, QNAME=host1.example.')])
        self.assertEqual(findings({**wrong, 'raw': True}), [])

    def test_octet_formula_preserves_operators_and_constants(self):
        formula = 'OCT_EXP[OCT_LOG[u] - OCT_LOG[v] + 255]'
        correct = body(formula + ' otherwise.', 'それ以外は OCT_EXP [ OCT_LOG[u] − OCT_LOG[v] +255 ] です。')
        self.assertEqual(findings(correct), [])
        for wrong in (formula.replace('+', ''), formula.replace('255', '256'), formula.replace('OCT_LOG[v]', 'OCT_LOG[u]')):
            row = {**correct, 'ja': wrong}
            self.assertEqual([(f.kind, f.fragment) for f in findings(row)], [('octet-formula', formula)])

    def test_type_assignment_checks_name_and_number_in_field_context(self):
        before = body('Type', 'タイプ')
        after = body('Length', '長さ')
        correct = body('24 for State.', 'State のタイプは24です。')
        wrong = {**correct, 'ja': '州の場合は24。'}
        wrong_number = {**correct, 'ja': 'State のタイプは124です。'}
        self.assertEqual(findings(before, correct, after), [])
        self.assertEqual([f.kind for f in findings(before, wrong, after)], ['type-assignment'])
        self.assertEqual([f.kind for f in findings(before, wrong_number, after)], ['type-assignment'])
        self.assertEqual(findings(wrong), [])
        self.assertEqual([f.kind for f in findings({**wrong, 'text': 'Type: 24 for State.'})], ['type-assignment'])

    def test_ipp_status_warning_checks_omission_of_not(self):
        code = 'client-error-attributes-or-values-not-supported'
        wrong = code.replace('-not-supported', '-supported')
        source = f"The server returns '{code}' otherwise."
        row = body(source, f"それ以外の場合は '{wrong}' を返します。")
        self.assertEqual([(f.kind, f.ending, f.fragment) for f in findings(row)],
                         [('ipp-status-negation', code, wrong)])
        self.assertEqual(findings({**row, 'ja': row['ja'].replace(wrong, code)}), [])
        self.assertEqual(findings({**row, 'text': f"{source} See '{wrong}'."}), [])
        self.assertEqual(findings({**row, 'raw': True}), [])

    def test_json_integer_range_checks_signs_and_inclusive_bounds(self):
        source = 'Int means an integer in the range -2^53+1 <= value <= 2^53-1.'
        correct = body(source, '整数の範囲は −2 ^ 53 + 1 ≤ 値 ≤ 2^53−1 です。')
        self.assertEqual(findings(correct), [])
        for error in ('−2^53 1 ≤ 値 ≤ 2^53−1', '−2^53+1 < 値 ≤ 2^53−1', '−2^53+1 ≤ 値 ≤ 2^53−10'):
            self.assertEqual([f.kind for f in findings({**correct, 'ja': error})], ['json-integer-range'])
        self.assertEqual(findings({**correct, 'raw': True, 'ja': ''}), [])

    def test_standalone_noun_warns_only_when_source_sentences_have_predicates(self):
        source = 'The receiver uses the field. It contains the identifier value.'
        wrong = body(source, '受信側はフィールドを読み取ります。識別子が入っています。 値。')
        correct = body(source, '受信側はフィールドを読み取ります。フィールドには識別子の値が入っています。')
        self.assertEqual([(f.kind, f.fragment) for f in findings(wrong)],
                         [('standalone-nominal', '値。')])
        self.assertEqual(list(inspect({'contents': [wrong]}, include_nominal=True)), findings(wrong))
        self.assertEqual(findings(correct), [])
        self.assertEqual(findings({**wrong, 'text': 'The receiver uses the field. Value.'}), [])
        self.assertEqual(findings({**wrong, 'text': 'o ' + source}), [])
        for flag in ('raw', 'section_title', 'toc', 'list_continuation'):
            self.assertEqual(findings({**wrong, flag: True}), [])

    def test_cardinality_warning_checks_explicit_counts_with_field_context(self):
        source = 'Contact Zero or more. The contact information for the incident.'
        wrong = body(source, 'Contact は0件または1件で、型は STRING です。連絡先を格納します。')
        correct = body(source, 'Contact は0件以上です。連絡先を格納します。')
        ambiguous = body(source, '連絡先を格納します。')
        self.assertEqual([(f.kind, f.ending, f.fragment) for f in findings(wrong)],
                         [('cardinality-mismatch', '0+', '0–1')])
        self.assertEqual(findings(correct, ambiguous, {**wrong, 'toc': True}), [])

        field = body('Analyzer', 'アナライザー')
        child = body('Exactly one. Identification information for the analyzer.', '1件以上です。識別情報を格納します。',
                     indent=6)
        self.assertEqual([f.kind for f in findings(field, child)], ['cardinality-mismatch'])
        self.assertEqual(findings(child, field, {**child, 'indent': 3}), [])

    def test_source_sentence_tail_follows_an_unfinished_determiner(self):
        start = body('The object is carried according to the aforementioned', 'オブジェクトを運びます。')
        tail = body('specification. This means that the object is validated.', '仕様。オブジェクトを検証します。')
        self.assertEqual([f.kind for f in findings(start, tail)], ['source-sentence-split'])
        self.assertEqual(findings(start, {**tail, 'raw': True}), [])
        self.assertEqual(findings(start, {**tail, 'indent': 6}), [])
        self.assertEqual(findings({**start, 'text': start['text'] + ' specification.'}, tail), [])

    def test_source_sentence_tail_can_complete_an_object_after_a_comparative(self):
        start = body("The method can involve more complex", "このメソッドにはより複雑なものが含まれます。")
        tail = body("processing. It is useful for complex requests.", "処理。複雑な要求に役立ちます。")
        self.assertEqual([f.kind for f in findings(start, tail)], ["source-sentence-split"])
        self.assertEqual(findings({**start, "text": "The method can be more complex"}, tail), [])
        self.assertEqual(findings(start, {**tail, "indent": 6}), [])

    def test_source_sentence_tail_can_complete_a_named_phrase(self):
        start = body("The application must ensure, when applied below the", "以下に適用する場合に確認します。")
        tail = body("FEC Framework, that both streams are valid.", "FEC フレームワーク。両方とも有効です。")
        self.assertEqual([f.kind for f in findings(start, tail)], ["source-sentence-split"])
        self.assertEqual(findings({**start, "text": start["text"] + " transport layer."}, tail), [])
        self.assertEqual(findings(start, {**tail, "section_title": True}), [])

    def test_source_sentence_tail_can_complete_a_reference_clause(self):
        first = body('A handover is possible. [RFC9999] defines', '引き渡しが可能です。[RFC9999] は定めています。')
        tail = body('the specific requirements for an ownership handover procedure. It also gives examples.',
                    '所有権の引き渡し手順の具体的な要件。例も示します。')
        self.assertEqual([f.kind for f in findings(first, tail)], ['source-sentence-split'])
        self.assertEqual(findings({**first, 'text': first['text'] + ' a procedure.'}, tail), [])
        self.assertEqual(findings(first, {**tail, 'text': tail['text'].capitalize()}), [])

    def test_source_sentence_split_can_continue_a_quoted_list(self):
        first = body('This document uses the terms "access token", "endpoint",', 'この文書では次の用語を使います。')
        tail = body('"client", "authorization server", and "redirect".', 'クライアント、認可サーバー、リダイレクト。')
        self.assertEqual([f.kind for f in findings(first, tail)], ["source-sentence-split"])
        self.assertEqual(findings({**first, "text": first["text"].rstrip(",") + "."}, tail), [])
        self.assertEqual(findings(first, {**tail, "indent": 6}), [])
        dictionary = body('"ABLE", "ACID",', '"ABLE", "ACID",')
        self.assertEqual(findings(dictionary, tail), [])

    def test_source_sentence_split_can_continue_an_enumeration_with_ensuring(self):
        first = body("This section covers protecting documents, ensuring", "この節では文書の保護を扱います。")
        tail = body("proper authentication, data integrity, and transport security.", "適切な認証、完全性、安全性。")
        self.assertEqual([f.kind for f in findings(first, tail)], ["source-sentence-split"])
        self.assertEqual(findings({**first, "text": first["text"] + " security."}, tail), [])
        self.assertEqual(findings(first, {**tail, "list_continuation": True}), [])

    def test_source_sentence_split_can_continue_an_indented_numeric_range(self):
        first = body("It may be set to any value from 1", "1 からの任意の値に設定できます。")
        tail = body("to 7 to indicate a non-default priority.", "7 からデフォルト以外の優先度を示します。", indent=6)
        self.assertEqual([f.kind for f in findings(first, tail)], ["source-sentence-split"])
        self.assertEqual(findings({**first, "text": first["text"] + " to 7."}, tail), [])
        self.assertEqual(findings(first, {**tail, "raw": True}), [])

    def test_source_sentence_split_across_an_indented_url(self):
        first = body('The interface is maintained separately. See', '別のグループが管理しています。')
        url = body('https://example.org/interface', 'https://example.org/interface', indent=6)
        tail = body('for additional information on the current state of the interface.', 'インターフェースの追加情報。')
        self.assertEqual([(f.kind, f.index) for f in findings(first, url, tail)], [('source-sentence-split', 2)])
        self.assertEqual(findings({**first, 'text': 'See the site.'}, url, tail), [])
        self.assertEqual(findings(first, {**url, 'indent': 3}, tail), [])

    def test_source_sentence_split_in_an_indented_list_item(self):
        first = body('o Two-way: The packets contain all the required', 'o 双方向：パケットにはすべて含まれます。')
        tail = body('information to measure packet loss from the sender.', '送信側のパケット損失測定情報。', indent=6)
        self.assertEqual([(f.kind, f.index) for f in findings(first, tail)], [('source-sentence-split', 1)])
        self.assertEqual(findings(first, {**tail, 'list_continuation': True}), [])
        self.assertEqual(findings({**first, 'text': first['text'] + ' fields.'}, tail), [])

    def test_flattened_grammar_between_raw_rules_is_detected_in_grammar_section(self):
        heading = body("Appendix A. ABNF Syntax", "付録 A. ABNF 構文", section_title=True)
        first = body("component = begin-array", "", raw=True)
        flattened = body("; A property has a name ; and a value. property = name value", "プロパティの説明。")
        last = body("name = string", "", raw=True)
        self.assertEqual([f.kind for f in findings(heading, first, flattened, last)], ["grammar-as-prose"])
        self.assertEqual(findings(heading, first, {**flattened, "raw": True}, last), [])
        self.assertEqual(findings(heading, first, flattened), [])
        self.assertEqual(findings({**heading, "text": "Appendix A. Examples"}, first, flattened, last), [])
        comment_only = {**flattened, "text": "; A property has a name ; and a value."}
        self.assertEqual(findings(heading, first, comment_only, last), [])

    def test_indented_der_example_is_detected_when_joined_with_its_caption(self):
        caption = body("Example of an algorithm identifier:", "アルゴリズム識別子の例です。", indent=6)
        vector = "30 15 06 06 2B 81 04 01 0B 02 30 0B 06 09 60 86 48 01 65 03 04 01 05"
        flattened = {**caption, "text": f"{caption['text']} {vector}"}
        self.assertEqual([f.kind for f in findings(flattened)], ["der-example-as-prose"])
        self.assertEqual(findings(caption, body(vector, "", raw=True, indent=9)), [])
        self.assertEqual(findings({**flattened, "indent": 3}), [])
        self.assertEqual(findings({**flattened, "text": caption["text"] + " 30 15 06 06 2B"}), [])

    def test_sip_example_requires_request_or_status_line_followed_by_via_header(self):
        for start in ("OPTIONS sip:example.com SIP/2.0", "SIP/2.0 200 OK"):
            flattened = body(f"{start} Via: SIP/2.0/TCP example.com", "SIP メッセージの例。")
            self.assertEqual([f.kind for f in findings(flattened)], ["sip-message-as-prose"])
            self.assertEqual(findings({**flattened, "raw": True}), [])
            self.assertEqual(findings({**flattened, "text": "For example: " + flattened["text"]}), [])
            self.assertEqual(findings({**flattened, "text": start}), [])

    def test_soa_example_requires_a_complete_record(self):
        record = body("example. 900 IN SOA ns.example. admin.example. ( 1 1800 900 604800 86400 )", "例。")
        self.assertEqual([f.kind for f in findings(record)], ["soa-record-as-prose"])
        self.assertEqual(findings({**record, "raw": True}), [])
        self.assertEqual(findings({**record, "text": record["text"].replace("604800 ", "")}), [])
        self.assertEqual(findings({**record, "text": "The following record is an example: " + record["text"]}), [])

    def test_commented_assignment_is_detected_in_pseudocode_section(self):
        heading = body("Appendix A. Load Rate Adjustment Pseudocode", "付録 A. 擬似コード", section_title=True)
        code = body("step = 3 # initial step # for this example", "初期値。")
        example = body("Initialize step = 3 before comparing values.", "比較の前に step を 3 にします。")
        self.assertEqual([f.kind for f in findings(heading, example, code)], ["pseudocode-as-prose"])
        self.assertEqual(findings(heading, {**code, "raw": True}), [])
        self.assertEqual(findings({**heading, "text": "Appendix A. Examples"}, code), [])
        self.assertEqual(findings(heading, {**heading, "text": "Appendix B. References"}, code), [])

    def test_merged_claim_registration_detects_joined_fields(self):
        fields = [
            'Claim Name: scope',
            'Claim Description: The scope of an access token.',
            'JWT Claim Name: scope',
            'Claim Key: 9',
            'Change Controller: IETF',
            'Reference: Section 4.2.',
        ]
        joined = body(' '.join(fields), '')
        self.assertEqual([f.kind for f in findings(joined)], ['merged-claim-registration'])
        fields[-1] = 'Specification Document(s): Section 4.2.'
        self.assertEqual([f.kind for f in findings(body(' '.join(fields), ''))], ['merged-claim-registration'])
        self.assertEqual(findings(*(body(field, '') for field in fields)), [])
        self.assertEqual(findings({**joined, 'raw': True}), [])

    def test_merged_checklist_item_is_scoped_to_the_checklist(self):
        heading = body('2.1.8. Summary Checklist', '2.1.8. チェックリスト', section_title=True)
        label = body('Rationale', '根拠')
        item = body("_ Explain the building block's purpose", '_ 目的の説明', indent=6)
        merged = body(f"{label['text']} {item['text']}", '')
        self.assertEqual([f.kind for f in findings(heading, merged)], ['merged-checklist-item'])
        self.assertEqual(findings(heading, label, item), [])
        self.assertEqual(findings(heading, {**merged, 'raw': True}), [])
        self.assertEqual(findings(heading, {**heading, 'text': '2.2. Design'}, merged), [])

    def test_mixed_numeric_and_letter_list_marker_is_excluded_from_nominal_audit(self):
        row = body('3a) Forwarding plane requirements - requirements related to router forwarding behavior.',
                   '3a) 転送プレーンの要件。')
        self.assertEqual(list(inspect({'contents': [row]}, include_nominal=True)), [])

    def test_mib_prose_is_reported_only_inside_a_complete_module(self):
        start = body("EXAMPLE-MIB DEFINITIONS ::= BEGIN", "", raw=True)
        comment = body("-- The following objects expose counters.", "以下はカウンターの定義です。")
        raw = body("legacyCounter OBJECT-TYPE", "", raw=True)
        end = body("END\n6.  Security Considerations", "", raw=True)
        prose = body("This section describes the deployment procedure.", "この節で説明する導入手順。")
        self.assertEqual([(f.kind, f.index) for f in findings(start, comment, raw, end, prose)],
                         [("mib-prose", 1)])
        self.assertEqual(findings(start, comment, raw), [])
        self.assertEqual(findings(start, comment, body("6. Security Considerations", "", section_title=True), end), [])
        self.assertEqual(findings(start, {**comment, "raw": True, "ja": ""}, raw, end), [])

    def test_mib_warning_compares_source_even_if_translation_is_reworded(self):
        start = body("EXAMPLE-MIB DEFINITIONS ::= BEGIN", "", raw=True)
        declaration = body("legacyCounter OBJECT-TYPE", "旧カウンターの定義。")
        end = body("END", "", raw=True)
        existing = findings(start, declaration, end)
        self.assertEqual(list(introduced(existing, findings(start, {**declaration, "ja": "カウンターです。"}, end))),
                         [])
        self.assertEqual([f.index for f in introduced([], existing)], [1])

    def test_asn1_module_continues_beyond_nested_macro_end(self):
        start = body('SNMPv2-TC DEFINITIONS ::= BEGIN', '', raw=True)
        macro = body('TEXTUAL-CONVENTION MACRO ::= BEGIN\n    TYPE NOTATION ::= Text\nEND', '', raw=True)
        comment = body('-- Comment within the module', 'モジュールのコメント。')
        end = body('END', '', raw=True)
        prose = body('The module ends on the preceding line.', 'モジュールは前の行で終わります。')
        self.assertEqual([(f.kind, f.index) for f in findings(start, macro, comment, end, prose)],
                         [('asn1-prose', 2)])
        self.assertEqual(findings(start, macro, comment, prose), [])

    def test_xml_prose_requires_a_complete_well_formed_document(self):
        declaration = body('<?xml version="1.0"?>', '', raw=True)
        root = body('<schema><documentation>', '', raw=True)
        description = body('The next item contains a format description.', '次の項目には形式の説明が含まれます。')
        end = body('</documentation></schema>', '', raw=True)
        prose = body('The schema is informative.', 'スキーマは参考情報です。')
        self.assertEqual([(f.kind, f.index) for f in findings(declaration, root, description, end, prose)],
                         [('xml-prose', 2)])
        self.assertEqual(findings(declaration, root, description, prose), [])
        self.assertEqual(findings(declaration, root, description, {**end, 'text': '</schema>'}), [])
        self.assertEqual(findings(root, description, end), [])

    def test_code_ending_joined_to_a_page_heading_is_a_warning(self):
        joined = body('END\x07\x07\x076. Security Considerations', '終了6。セキュリティ上の考慮事項')
        self.assertEqual([f.kind for f in findings(joined)], ['code-heading-join'])
        self.assertEqual(findings(body('END', '', raw=True),
                                  body('6. Security Considerations', '6. セキュリティ上の考慮事項',
                                       section_title=True)), [])
    def test_rfc5789_condition_and_corrected_word_order(self):
        en = "The server can return a 415 response when it does not support the format."
        self.assertEqual(
            [item.kind for item in findings(body(en, "415 応答を返せます。形式に対応しない場合。"))],
            ["detached-clause"],
        )
        self.assertEqual(findings(body(en, "形式に対応しない場合は、415 応答を返せます。")), [])

    def test_purpose_clause_and_polite_sentence_endings(self):
        en = "The receiver uses this check in order to reject invalid frames."
        self.assertEqual(
            [item.ending for item in findings(body(en, "この検査を使います。不正なフレームを拒否するため。"))],
            ["ため"],
        )
        self.assertEqual(findings(body(en, "この検査は、不正なフレームを拒否するためです。")), [])

    def test_fronted_condition(self):
        en = "If authentication fails, the server MUST close the connection."
        self.assertEqual(
            len(findings(body(en, "認証に失敗した場合。サーバーは接続を閉じなければなりません (MUST)。"))),
            1,
        )

    def test_literal_and_structural_exclusions(self):
        en = "The server may close the connection if authentication fails."
        ja = "接続を閉じてもよいです。認証に失敗した場合。"
        self.assertEqual(findings(
            body(en, ja, raw=True),
            body(en, ja, toc=True),
            body(en, ja, section_title=True),
            body(en, ja, list_continuation=True),
            body("• " + en, ja),
            body("a. " + en, ja),
            body(". " + en, ja),
            body("noChannel(1), when no channels exist. fastOnly(2), when only fast channel exists.",
                 "高速チャネルのみが存在する場合。"),
            body("FeatureNotAvailableException - if the VTSAgent does not support the option.",
                 "VTSAgent が対応しない場合。"),
            body("noError: because the agent chooses to create the instance.",
                 "エージェントがインスタンスを作成することを選択したため。"),
            body("Block Length: 16 bits", "ブロック長の定義"),
            body("For cases when the extension is unavailable.", "拡張を使用できない場合。"),
        ), [])

    def test_collapsed_dot_list_remains_a_candidate(self):
        self.assertEqual(len(findings(body(
            ". The server may close the connection if authentication fails. . A final action",
            "接続を閉じてもよいです。認証に失敗した場合。",
        ))), 1)

    def test_cross_paragraph_source_and_raw_boundary(self):
        prev = body("The client should follow the guidelines in Section 5.4", "5.4 節に従うべきです。")
        current = body("to avoid dangerous usage scenarios. In particular, this connection is insecure.",
                       "危険な使用シナリオを回避するため。この接続は安全ではありません。")
        self.assertEqual([item.kind for item in findings(prev, current)], ["paragraph-split"])
        self.assertEqual(findings(prev, body("example", "", raw=True), current), [])

    def test_previous_paragraph_can_end_in_a_quoted_sentence(self):
        prev = body('The relevant notice is "This document is informational."', "告知文です。")
        current = body("For non-IETF documents, a reference is added.",
                       "参照を追加します。非 IETF 文書の場合。")
        self.assertEqual(findings(prev, current), [])

    def test_incomplete_source_without_previous_main_clause(self):
        self.assertEqual(findings(body(
            "If the server has a configuration file. The configuration is consumed on startup.",
            "サーバーに設定ファイルがある場合。設定は起動時に読み込みます。",
        )), [])

    def test_repeated_copyright_notice_is_separate(self):
        result = findings(body(
            "Copies may be distributed provided that the above copyright notice and this paragraph are included.",
            "複製を配布できます。上記の著作権通知とこの段落が含まれる場合。",
        ))
        self.assertEqual([item.kind for item in result], ["copyright"])

    def test_warranty_warning_requires_original_disclaimer(self):
        source = ("The Internet Society disclaims all warranties, express or implied, "
                  "including implied warranties of merchantability or fitness.")
        broken = "すべての保証を否認します。商品性または特定の目的への適合性の権利または黙示の保証を侵害します。"
        corrected = "明示または黙示を問わず、商品性や特定の目的への適合性に関する保証も含め、一切の保証を否認します。"
        self.assertEqual([item.kind for item in findings(
            body(source, broken), body(source, corrected), body("Merchantability.", broken),
            body(source, broken, raw=True),
        )], ["warranty-disclaimer"])

    def test_optional_nominal_audit_preserves_structural_exclusions(self):
        nominal = body("This section describes the deployment procedure.", "この節で説明する導入手順。")
        condition = body("The server may close the connection if authentication fails.",
                         "接続を閉じてもよいです。認証に失敗した場合。")
        obj = {"contents": [
            nominal, condition, {**nominal, "raw": True},
            {**nominal, "section_title": True}, {**nominal, "list_continuation": True},
            {**nominal, "text": "* " + nominal["text"]},
        ]}
        self.assertEqual([f.kind for f in inspect(obj)], ["detached-clause"])
        self.assertEqual([(f.index, f.kind, f.ending) for f in inspect(obj, include_nominal=True)],
                         [(0, "nominal-fragment", "手順"), (1, "detached-clause", "場合")])

    def test_license_fragment_is_only_a_warning_in_the_matching_notice(self):
        source = ("The IETF takes no position regarding the validity or scope of any rights "
                  "or the extent to which a license might or might not be available.")
        broken = "IETF はいかなる立場も取りません。利用可能であること。"
        corrected = "IETF は、許諾が得られるかどうかについて、いかなる立場も取りません。"
        content = [body(source, broken), body(source, corrected),
                   body("The license is available.", broken)]
        self.assertEqual([(f.index, f.kind) for f in inspect({"contents": content})],
                         [(0, "ipr-notice")])
        self.assertEqual([(f.index, f.kind) for f in inspect({"contents": content}, include_nominal=True)],
                         [(0, "ipr-notice"), (2, "nominal-fragment")])

    def test_nominal_label_requires_an_indented_following_paragraph(self):
        label = body("Examples.", "例。")
        next_row = body("A router sends a reply.", "ルーターは応答を返します。", indent=6)
        obj = {"contents": [label, next_row, label]}
        self.assertEqual([(f.index, f.kind) for f in inspect(obj, include_nominal=True)],
                         [(0, "nominal-label"), (2, "nominal-fragment")])

    def test_inline_nominal_label_must_match_both_full_paragraphs(self):
        label = body("Value type: A single URI value.", "値タイプ：単一のURI値。")
        extra_source = {**label, "text": label["text"] + " The server uses this value."}
        extra_translation = {**label, "ja": label["ja"] + " 実装で使われる値。"}
        obj = {"contents": [label, extra_source, extra_translation]}
        self.assertEqual([(f.index, f.kind) for f in inspect(obj, include_nominal=True)],
                         [(0, "nominal-label"), (1, "nominal-fragment"),
                          (2, "nominal-fragment"), (2, "nominal-fragment")])

    def test_inline_label_cardinality_must_match(self):
        label = body("Value type: A single text value. Cardinality: *",
                     "値タイプ：単一のテキスト値。カーディナリティ： *")
        wrong = {**label, "ja": label["ja"].replace("*", "1")}
        absent = {**label, "ja": "値タイプ：単一のテキスト値。"}
        extra = {**label, "text": label["text"] + " The server validates this value."}
        obj = {"contents": [label, wrong, absent, extra]}
        self.assertEqual([(f.index, f.kind) for f in inspect(obj, include_nominal=True)],
                         [(0, "nominal-label"), (1, "nominal-fragment"),
                          (2, "nominal-fragment"), (3, "nominal-fragment")])

    def test_registry_range_label_keeps_mismatched_bounds_in_the_audit(self):
        source = '3-31: range available to IANA for assignment in this registry.'
        correct = body(source, '3-31：このレジストリでの割り当てにIANAが使用できる範囲。')
        wrong = {**correct, 'ja': correct['ja'].replace('3-31', '3-30')}
        result = inspect({'contents': [correct, wrong]}, include_nominal=True)
        self.assertEqual([f.kind for f in result], ['nominal-label', 'nominal-fragment'])

    def test_structured_value_type_label_checks_separator_and_cardinality(self):
        label = body("Value type: One or more text values separated by a COMMA character (U+002C). Cardinality: *",
                     "値タイプ：コンマ文字（U+002C）で区切られた1つ以上のテキスト値。カーディナリティ： *")
        wrong_separator = {**label, "ja": label["ja"].replace("U+002C", "U+003B")}
        wrong_cardinality = {**label, "ja": label["ja"].replace("*", "*1")}
        obj = {"contents": [label, wrong_separator, wrong_cardinality]}
        self.assertEqual([(f.index, f.kind) for f in inspect(obj, include_nominal=True)],
                         [(0, "nominal-label"), (1, "nominal-fragment"), (2, "nominal-fragment")])

    def test_numbered_requirement_requires_matching_number_and_adjacent_sibling(self):
        first = body("14.1) Data integrity: protect the object,", "14.1) データの完全性を保護すること。")
        second = body("14.2) Data confidentiality: protect stored objects.",
                      "14.2）保存したオブジェクトを保護すること。追加の例。")
        expected = [(0, "nominal-label"), (1, "nominal-label"), (1, "nominal-fragment")]
        self.assertEqual([(f.index, f.kind) for f in inspect({"contents": [first, second]}, include_nominal=True)],
                         expected)
        for rows in ([first], [first, {**second, "indent": 6}],
                     [{**first, "ja": first["ja"].replace("14.1", "14.9")}, second]):
            self.assertEqual(next(inspect({"contents": rows}, include_nominal=True)).kind, "nominal-fragment")

    def test_alphabetic_item_requires_matching_marker_and_adjacent_sibling(self):
        first = body("A. How packets reach receivers.", "A. パケットが受信者に届く方法。")
        second = body("B. How senders choose receivers.", "B.送信者が受信者を選ぶ方法。")
        self.assertEqual([f.kind for f in inspect({"contents": [first, second]}, include_nominal=True)],
                         ["nominal-label", "nominal-label"])
        for rows in ([first], [first, {**second, "indent": 7}], [first, {**second, "raw": True}],
                     [first, body("C. How failures are handled.", "C. 障害時の処理方法。")],
                     [{**first, "ja": first["ja"].replace("A.", "D.")}, second],
                     [{**first, "ja": first["ja"] + "送信者が宛先を選びます。"}, second]):
            self.assertEqual(next(inspect({"contents": rows}, include_nominal=True)).kind, "nominal-fragment")

    def test_value_type_description_requires_the_label_and_nested_indent(self):
        label = body("Value type:", "値タイプ：")
        value_type = body("A single timestamp value.", "単一のタイムスタンプ値。", indent=12)
        cases = (
            ([label, value_type], "nominal-label"),
            ([label, {**value_type, "indent": 3}], "nominal-fragment"),
            ([body("Protocol details:", "プロトコルの詳細："), value_type], "nominal-fragment"),
            ([label, {**value_type, "ja": "複数のタイムスタンプ値。"}], "nominal-fragment"),
        )
        for contents, expected in cases:
            result = inspect({"contents": contents}, include_nominal=True)
            self.assertEqual([f.kind for f in result], [expected])

    def test_contextual_label_requires_matching_description_and_structure(self):
        figure = body("+---+\n|   |\n+---+", "", raw=True)
        caption = body("How the decision for isAccessAllowed is made.", "isAccessAllowedの決定方法。")
        field = body("Value", "値")
        description = body("The value of the TLV.", "TLV の値。", indent=6)
        incomplete = {**description, "text": "The value of the TLV. The sender validates it."}
        rows = [caption, figure, caption, field, description,
                field, incomplete, {**description, "indent": 3}]
        self.assertEqual([(f.index, f.kind) for f in inspect({"contents": rows}, include_nominal=True)],
                         [(0, "nominal-fragment"), (2, "nominal-label"), (4, "nominal-label"),
                          (6, "nominal-fragment"), (7, "nominal-fragment")])

    def test_conditional_figure_footnote_requires_its_surrounding_structure(self):
        footnote = body("(*2) If a listener is registered.", "（*2）リスナーが登録されている場合。")
        prior = body("(*1) Registration is optional.", "（*1）登録は任意です。")
        caption = body("Figure 1. Wallet architecture with VTS plug-ins", "図1. VTSプラグインを備えた構成")
        obj = {"contents": [footnote, prior, footnote, caption, prior, footnote]}
        self.assertEqual([(f.index, f.kind) for f in inspect(obj, include_nominal=True)],
                         [(0, "nominal-fragment"), (2, "nominal-label"), (5, "nominal-fragment")])

    def test_new_warning_cannot_be_offset_by_removing_another(self):
        en = "The server may close the connection if authentication fails."
        row = body(en, "サーバーは接続を閉じてもよいです。認証に失敗した場合。")
        other = body(en.replace("authentication", "validation"), "検証に失敗した場合。")
        before = findings(row)
        self.assertEqual(list(introduced(before, findings(body("New paragraph.", "新しい段落です。"), row))), [])
        self.assertEqual([item.fragment for item in introduced(before, findings(other))], ["検証に失敗した場合。"])
        self.assertEqual([item.index for item in introduced(before, findings(row, row))], [1])


if __name__ == "__main__":
    unittest.main()

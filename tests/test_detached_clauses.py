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

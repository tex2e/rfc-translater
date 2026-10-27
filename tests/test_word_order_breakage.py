import json
import os
import sys
import tempfile
from pathlib import Path
import unittest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from lint_translation import (  # noqa: E402
    check_dangling_predicate, check_particle_chain, lint_file,
)


class TestDanglingPredicate(unittest.TestCase):
    """W015: 文末の述語の後ろに名詞句がぶら下がる語順崩れ"""

    def assertDetected(self, ja):
        r = check_dangling_predicate(ja)
        self.assertTrue(r, ja)
        self.assertEqual(r[0][0], "W015")

    def assertClean(self, ja):
        self.assertEqual(check_dangling_predicate(ja), [], ja)

    def test_detects_rfc6648_example(self):
        self.assertDetected("このアプローチでは、コストがメリットを上回っています標準スペース。")

    def test_detects_copyright_boilerplate(self):
        self.assertDetected("この素材の一部の著作権を管理する人は、IETFトラストにそのような素材の"
                            "変更を許可する権利を付与していない可能性がありますIETF標準プロセス外。")

    def test_detects_ipr_boilerplate(self):
        self.assertDetected("IETFは、…権利の有効性または範囲に関していかなる位置を取りません利用可能。")

    def test_detects_past_and_negative_forms(self):
        self.assertDetected("デバイスに接続できませんでしたタイムアウト値。")
        self.assertDetected("メモが承認された日付に設定されましたIESGによる出版。")
        self.assertDetected("I-SID-レベルが必要です粒度。")

    def test_detects_noun_phrase_with_particles(self):
        self.assertDetected("ホップは受信したアドレスに等しくなりますピアからのアドレスメッセージ。")

    def test_allows_normal_sentences(self):
        self.assertClean("このメッセージはサーバーに送信されます。")
        self.assertClean("値は0です。次のフィールドは予約されています。")

    def test_allows_conjunctions_after_predicate(self):
        # 述語に接続助詞・終助詞が続く場合は文の途中であり、崩れではない
        self.assertClean("この値は推奨されますが、必須ではありません。")
        self.assertClean("サーバーは応答しますか、それとも接続を切断しますか。")
        self.assertClean("実装は存在しますので、相互運用性を確認できます。")
        self.assertClean("処理は単純ですし、実装も容易です。")

    def test_allows_words_containing_masu_desu(self):
        # 「ますます」「すでに」「すべて」は語の一部
        self.assertClean("トラフィックはますます増加しています。")
        self.assertClean("この機能はすでに実装されています。")
        self.assertClean("これで処理はすべて完了です。")

    def test_allows_verb_stems_containing_masu(self):
        # 「なりすます」「だます」の語幹の「ます/まし」は述語ではない
        self.assertClean("攻撃者が正規のサーバーになりすました場合。")
        self.assertClean("攻撃者が正規の利用者になりすます攻撃。")

    def test_allows_quoted_predicate(self):
        self.assertClean("サーバーは「完了です」という文字列を返します。")

    def test_allows_new_boilerplate_translations(self):
        ja = ("そのような素材の著作権を管理する者から適切なライセンスを取得しない限り、"
              "IETF標準プロセスの外でこの文書を変更することはできません。"
              "また、RFCとして発行するために書式を整える場合と英語以外の言語に翻訳する場合を除き、"
              "IETF標準プロセスの外でこの文書の派生物を作成することはできません。")
        self.assertClean(ja)


class TestParticleChain(unittest.TestCase):
    """W016: 名詞が抜け落ちて助詞が連続している"""

    def assertDetected(self, ja, chain):
        r = check_particle_chain(ja)
        self.assertTrue(r, ja)
        self.assertEqual(r[0][0], "W016")
        self.assertIn(f"「{chain}」", r[0][1])

    def assertClean(self, ja):
        self.assertEqual(check_particle_chain(ja), [], ja)

    def test_detects_wo_ni(self):
        self.assertDetected("ユニキャストメッセージをに送信します。", "をに")

    def test_detects_ga_ni_and_ga_de(self):
        self.assertDetected("フラグがに設定されている場合", "がに")
        self.assertDetected("DATA_CHANNEL_OPENメッセージがで受信されました。", "がで")

    def test_detects_wo_wo(self):
        self.assertDetected("実装は、完全なUnbindRequestをを実装しなければなりません。", "をを")

    def test_detects_no_no(self):
        self.assertDetected("意味的に等価でなければなりません（例えば、Counter64のの使用）。", "のの")

    def test_detects_ni_ni(self):
        self.assertDetected("送信者は検証フェーズにに入ります。", "にに")

    def test_allows_hiragana_words(self):
        # 直前がひらがなの語 (ものの、ことを、など) は対象外
        self.assertClean("仕様は存在するものの、実装はありません。")
        self.assertClean("ことを確認します。")

    def test_allows_noren_and_nonoshiru(self):
        # 「のれん」(営業権) や「ののしる」は語の一部
        self.assertClean("記事は、受け取るすべてのサイトののれんに依存します。")

    def test_allows_normal_particles(self):
        self.assertClean("サーバーはメッセージをクライアントに送信します。")
        self.assertClean("値が0に設定されている場合、処理を中止します。")


class TestLintFileIntegration(unittest.TestCase):
    def _lint(self, contents, enabled=("W015", "W016")):
        obj = {"title": {"text": "RFC 9999 - Test", "ja": "RFC 9999 - テスト"}, "contents": contents}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "rfc9999-trans.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False)
            return lint_file(path, set(enabled))

    def test_reports_body_paragraphs(self):
        findings = self._lint([
            {"text": "The costs outweigh the benefits in the standards space.",
             "ja": "コストがメリットを上回っています標準スペース。", "indent": 3},
            {"text": "Send the message to the server.",
             "ja": "メッセージをに送信します。", "indent": 3},
        ])
        self.assertEqual([(f.code, f.index) for f in findings], [("W015", 0), ("W016", 1)])

    def test_skips_raw_and_section_titles(self):
        findings = self._lint([
            {"text": "1. Costs", "ja": "1. 上回っています標準スペース。", "indent": 0,
             "section_title": True},
            {"text": "x = y", "ja": "", "indent": 3, "raw": True},
        ])
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()

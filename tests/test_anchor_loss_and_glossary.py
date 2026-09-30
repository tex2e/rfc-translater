import sys
from pathlib import Path
import unittest

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))

from lint_translation import check_anchor_loss, check_glossary  # noqa: E402


class TestAnchorLoss(unittest.TestCase):
    def test_detects_fabricated_numbers(self):
        # rfc3441#162: 数値が捏造され、原文の後半の数値が消えている
        en = ("This implies a forward acceptable peak-to-peak CDV of 8.125 ms, a backward "
              "acceptable peak-to-peak CDV of 4.675 ms, forward cumulative peak-to-peak CDV of "
              "3.455 ms, a backward cumulative peak-to-peak CDV of 2.155 ms, a forward "
              "end-to-end transit delay of 32 ms, a backward end-to-end transit delay of 18 ms.")
        ja = ("これは、順方向の許容ピーク間CDVが8.125 ms、逆方向の許容ピーク間CDVが4.675 ms、"
              "順方向の累積ピーク間CDVが3.455 ms、逆方向の累積ピーク間CDVが1.234 msであることを意味します。")
        r = check_anchor_loss(en, ja)
        self.assertIsNotNone(r)
        self.assertEqual(r[0], "W013")

    def test_detects_truncated_translation(self):
        # rfc4556#56: 段落の大半が落ちている
        en = ("a) Key transport algorithms identified in the keyEncryptionAlgorithm field of the "
              "type KeyTransRecipientInfo [RFC3852] for encrypting the temporary key in the "
              "encryptedKey field [RFC3852] with a public key, as described in [RFC3852]: "
              "rsaEncryption (this is the RSAES-PKCS1-v1_5 encryption scheme) [RFC3370] [RFC3447].")
        ja = "a) 暗号化スキーム）[RFC3370] [RFC3447]。"
        self.assertIsNotNone(check_anchor_loss(en, ja))

    def test_allows_faithful_translation(self):
        en = ("The MaxRtrAdvInterval MUST be no less than 4 seconds and no greater than "
              "21600 seconds. The default value for MaxRtrAdvInterval is 10800 seconds.")
        ja = ("MaxRtrAdvIntervalは、4秒以上21600秒以下でなければなりません (MUST)。"
              "MaxRtrAdvIntervalのデフォルト値は10800秒です。")
        self.assertIsNone(check_anchor_loss(en, ja))

    def test_allows_thousands_separator(self):
        en = "The swarm sizes for the torrents were 9984, 3944, 2561, and 2023."
        ja = "torrentのSwarmサイズはそれぞれ9,984、3,944、2,561、2,023でした。"
        self.assertIsNone(check_anchor_loss(en, ja))

    def test_ignores_all_uppercase_paragraph(self):
        self.assertIsNone(check_anchor_loss("TABLE OF CONTENTS", "目次"))

    def test_ignores_paragraph_with_few_anchors(self):
        self.assertIsNone(check_anchor_loss("Section 3 describes it.", "説明します。"))


class TestGlossary(unittest.TestCase):
    def codes(self, en, ja):
        return [detail for _, detail in check_glossary(en, ja)]

    def test_shared_secret_terms(self):
        self.assertTrue(self.codes("a shared secret key", "共有シークレットキー"))
        self.assertTrue(self.codes("a shared secret key", "共有秘密の鍵"))
        self.assertTrue(self.codes("the shared secret", "共有秘密"))
        self.assertTrue(self.codes("shared secret keying material", "共有秘密鍵素材"))
        self.assertFalse(self.codes("a shared secret key", "共有秘密鍵"))
        self.assertFalse(self.codes("the shared secret", "共有シークレット"))
        self.assertFalse(self.codes("shared secret keying material", "共有シークレット鍵素材"))

    def test_known_mistranslations(self):
        self.assertTrue(self.codes("congestion control", "混雑制御"))
        self.assertTrue(self.codes("the ingress PE", "侵入PE"))
        self.assertTrue(self.codes("ATM cells", "ATM細胞"))
        self.assertTrue(self.codes("the TLS handshake", "TLS握手"))
        self.assertTrue(self.codes("the LSP is torn down", "LSPは取り壊されます"))
        self.assertFalse(self.codes("congestion control", "輻輳制御"))
        self.assertFalse(self.codes("the ingress PE", "イングレスPE"))

    def test_only_when_source_has_the_term(self):
        # 原文に congestion がなければ「混雑」は検査しない
        self.assertFalse(self.codes("the road is busy", "道路が混雑しています"))

    def test_exceptions(self):
        # 原文が本当に侵入を述べている場合
        self.assertFalse(self.codes("ingress filtering prevents intrusion", "侵入を防ぎます"))
        # salt と無関係な「塩水」
        self.assertFalse(self.codes("salt water", "塩水"))


if __name__ == "__main__":
    unittest.main()

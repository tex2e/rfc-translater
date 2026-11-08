import unittest

from src.application.usecase.make_html import RfcHtmlHelper


class TestAnnotationSpacing(unittest.TestCase):
    def test_separates_hiragana_after_each_normative_keyword(self):
        for keyword in RfcHtmlHelper.BCP14_KEYWORDS:
            with self.subTest(keyword=keyword):
                text = f'発行すべき ({keyword})かを確認します。'
                spaced = f'発行すべき ({keyword}) かを確認します。'
                self.assertEqual(RfcHtmlHelper.space_after_annotation(text), spaced)
                self.assertEqual(RfcHtmlHelper.space_after_annotation(spaced), spaced)

    def test_preserves_punctuation_existing_spaces_and_other_parentheses(self):
        for suffix in ['。', '、', '（例）', ' か', '  か', 'フィールド', '値', '']:
            text = f'発行すべきです (SHOULD){suffix}'
            self.assertEqual(RfcHtmlHelper.space_after_annotation(text), text)
        self.assertEqual(RfcHtmlHelper.space_after_annotation('(RFC 10002)か'), '(RFC 10002)か')

    def test_rendered_annotation_keeps_spacing_and_highlighting(self):
        rendered = RfcHtmlHelper.render_text('発行すべき (SHOULD)か。', bcp14=True)
        self.assertIn('(<span class="kw kw-should">SHOULD</span>) か。', rendered)
        self.assertEqual(RfcHtmlHelper.render_text('発行すべき (SHOULD)か。'), '発行すべき (SHOULD) か。')


if __name__ == '__main__':
    unittest.main()

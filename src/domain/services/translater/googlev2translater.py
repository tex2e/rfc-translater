
from dotenv import load_dotenv  # pip install python-dotenv
from .metatranslater import Translator, MyTranslateException
from google.cloud import translate_v2 as translate

# 環境変数の読み込み
load_dotenv()
# ※環境変数GOOGLE_APPLICATION_CREDENTIALS にクレデンシャルファイルのパスを記載すること


class TranslatorGoogleV2(Translator):

    # 最初の50万文字（1か月あたり）     無料（毎月$10分のクレジットとして適用）
    # 50万文字以上（1か月あたり）       $20（100 文字あたり）

    def _init_process(self, args):
        self.args = args

    def _translate_process(target: str, text: str) -> dict:

        translate_client = translate.Client()

        if isinstance(text, bytes):
            text = text.decode("utf-8")

        # Text can also be a sequence of strings, in which case this method
        # will return a sequence of results for each text.
        target = 'ja'
        result = translate_client.translate(text, target_language=target)

        # print("Text: {}".format(result["input"]))
        # print("Translation: {}".format(result["translatedText"]))
        # print("Detected source language: {}".format(result["detectedSourceLanguage"]))
        ja_text = result["translatedText"]

        return ja_text

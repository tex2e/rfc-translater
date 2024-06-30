
import re
from dotenv import load_dotenv  # pip install python-dotenv
from .metatranslater import Translator, MyTranslateException
# ChatGPT
from ....domain.services.nlputils import openai, ChatGPT

# 環境変数の読み込み
load_dotenv()


class TranslatorChatGPT(Translator):
    """ChatGPTによる翻訳処理"""

    def _init_process(self, args):
        self.model_name = ChatGPT.get_exact_model_name(args.chatgpt)

    def _translate_process(self, text: str) -> str:
        prompt1 = "次の英語を日本語に翻訳してください。翻訳結果のみ出力し、翻訳できないときは英語のまま出力してください。"
        prompt2 = f"{text}"
        # リクエスト送信
        response = openai.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that translates English to Japanese."},
                {"role": "user", "content": prompt1},
                {"role": "user", "content": prompt2},
            ],
            temperature=0
        )
        # レスポンスから回答内容取得
        ja = response.choices[0].message.content
        # 翻訳結果が空文字のときは例外とする
        if re.match(r'^\s*$', ja):
            raise MyTranslateException(f'Translated text is empty string!\ninput text: "{text}"')
        return ja

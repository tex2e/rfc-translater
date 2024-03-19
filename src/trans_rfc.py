# ------------------------------------------------------------------------------
# RFCの文章を翻訳するプログラム
# ------------------------------------------------------------------------------

import os
import re
import time
import platform
from abc import ABC, abstractmethod
from tqdm import tqdm  # pip install tqdm
from .rfc_utils import RfcUtils
from .rfc_const import RfcFile, RfcJsonElem
# GoogleTranslator
import urllib.parse
from selenium import webdriver  # pip install selenium
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
# ChatGPT
from .nlp_utils import openai, CHATGPT_MODEL35, get_model_name_from_args_chatgpt


# 変換元は必ず小文字で記載すること
trans_rules = {
    'abstract': '概要',
    'introduction': 'はじめに',
    'acknowledgement': '謝辞',
    'acknowledgements': '謝辞',
    'acknowledgments': '謝辞',
    'status of this memo': '本文書の位置付け',  # '本文書の状態',
    'copyright notice': '著作権表示',
    'table of contents': '目次',
    "author's address": '著者の連絡先',
    'conventions': '規約',
    'terminology': '用語',
    'background': '背景',
    'discussion': '考察',
    'security considerations': 'セキュリティに関する考慮事項',
    'iana considerations': 'IANAの考慮事項',
    'references': '参考文献',
    'normative references': '引用文献',
    'informative references': '参考引用',
    'contributors': '貢献者',
    'uses': '用途',
    'specification': '仕様',
    'where': 'ただし',
    'where:': 'ただし：',
    'assume:': '前提：',
    'client:': 'クライアント：',
    'server:': 'サーバ：',
    'value:': '値：',
    'for example:': '例えば：',
}


# 翻訳処理例外
class MyTranslateException(Exception):
    pass


# 翻訳抽象クラス
class Translator(ABC):

    def __init__(self, total, desc='', args=None):
        self.count = 0
        self.total = total
        # プログレスバー
        bar_format = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}{postfix}]"
        self.bar = tqdm(total=total, desc=desc, bar_format=bar_format)
        # 初期化
        self._init_process(args)

    def increment_progress(self, incr=1):
        # プログレスバー用の出力
        self.count += incr
        self.bar.update(incr)

    def output_progress(self, len, wait_time):
        # プログレスバーに詳細情報を追加
        self.bar.set_postfix(len=len, sleep=('%.1f' % wait_time))

    def translate(self, text: str) -> str:
        text = text.strip()
        if len(text) == 0:
            return ""
        # 特定の用語については、翻訳ルール(trans_rules)で翻訳する
        ja = trans_rules.get(text.lower())
        if ja:
            return ja
        return self._translate_process(text)

    def close(self):
        return True

    @abstractmethod
    def _init_process(self):
        pass

    @abstractmethod
    def _translate_process(self, text: str) -> str:
        raise MyTranslateException()


# Selenium + Google による翻訳処理
class TranslatorSeleniumGoogletrans(Translator):

    def _init_process(self, args):
        options = Options()
        options.add_argument('--headless')
        browser = None
        if platform.system() == 'Windows':
            # Windows:
            path = os.path.join('C:', 'Apps', 'webdriver', 'geckodriver.exe')
            WEBDRIVER_EXE_PATH = os.getenv('WEBDRIVER_EXE_PATH', default=path)
            browser = webdriver.Firefox(executable_path=WEBDRIVER_EXE_PATH, options=options)
        else:
            # Ubuntu:
            # sudo apt install python3-pip firefox
            # sudo pip3 install selenium
            #options.binary_location = '/usr/bin/firefox'
            browser = webdriver.Firefox(options=options)
        browser.implicitly_wait(3)
        self._browser = browser

    def _translate_process(self, text: str) -> str:

        # URLエンコード
        text = text.replace('%', '%25')  # 「%」をURLエンコードする
        text = text.replace('|', '%7C')  # 「|」をURLエンコードする
        text = text.replace('/', '%2F')  # 「/」をURLエンコードする

        for i in range(0, 3):
            browser = self._browser
            # 翻訳したい文をURLに埋め込んでからアクセスする
            text_for_url = urllib.parse.quote_plus(text, safe='')
            dest='ja'
            url = "https://translate.google.co.jp/#en/{1}/{0}".format(text_for_url, dest)
            # print('[+] url:', url)
            browser.get(url)
            # 数秒待機する
            wait_time = 6 + len(text) / 1000
            self.output_progress(len=len(text), wait_time=wait_time)  # プログレスバーに詳細情報を追加
            time.sleep(wait_time)
            # 翻訳結果を抽出する
            elems = browser.find_elements(By.CSS_SELECTOR, "span[jsname='W297wb']")
            ja = "\n".join(elem.text for elem in elems)
            ja = re.sub(r'(?<!\n)\n(?!\n)', '', ja)
            # 翻訳結果が空文字のときは別のCSSセレクタでリトライする（例：「224.0.0.18」を翻訳するとURLになって構造が変わるため）
            if re.match(r'^\s*$', ja):
                elems = browser.find_elements(By.CSS_SELECTOR, "span[jsname='jqKxS']")
                ja = "\n".join(elem.text for elem in elems)
                ja = re.sub(r'(?<!\n)\n(?!\n)', '', ja)

            # 翻訳結果が空文字のときはリトライする（最大3回）
            if re.match(r'^\s*$', ja):
                time.sleep(30)
                continue

            return ja

        # リトライしても翻訳結果が空文字のときは例外とする
        raise MyTranslateException(f'Translated text is empty string!\ninput text: "{text}"\nsend url: "{url}"')

    def close(self):
        if self._browser is None:
            return True
        return self._browser.quit()


# ChatGPTによる翻訳処理
class TranslatorChatGPT(Translator):

    def _init_process(self, args):
        self.model_name = get_model_name_from_args_chatgpt(args.chatgpt)

    def _translate_process(self, text: str) -> str:

        model_name = self.model_name
        prompt1 = "次の英語を日本語に翻訳してください。余計な説明は不要です。翻訳できないときは入力をそのまま出力してください。"
        prompt2 = f"{text}"
        # リクエスト送信
        response = openai.chat.completions.create(
            model=model_name,
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


def trans_rfc(rfc_number: int | str, args) -> bool:

    if type(rfc_number) is int:
        # 通常のRFCのとき
        input_file = RfcFile.get_filepath_data_json(rfc_number)
        output_file = RfcFile.get_filepath_data_trans_json(rfc_number)
        midway_file = RfcFile.get_filepath_data_midway_json(rfc_number)
    elif m := re.match(r'draft-(?P<rfc_draft_id>.+)', rfc_number):
        # ドラフト版のRFCのとき
        rfc_draft_id = m['rfc_draft_id']
        input_file = RfcFile.get_filepath_data_json(rfc_draft_id)
        output_file = RfcFile.get_filepath_data_trans_json(rfc_draft_id)
        midway_file = RfcFile.get_filepath_data_midway_json(rfc_draft_id)
    else:
        raise RuntimeError(f"fetch_rfc: Unknown format number={rfc_number}")

    if os.path.isfile(midway_file):
        # 途中まで翻訳済みのファイルがあれば復元する
        obj = RfcFile.read_json_file(midway_file)
    else:
        obj = RfcFile.read_json_file(input_file)

    # 翻訳機の選択
    total_len = len([con for con in obj[RfcJsonElem.CONTENTS] if not con.get(RfcJsonElem.Contents.RAW)])
    desc = 'RFC %s' % rfc_number
    if args.chatgpt:
        # ChatGPTによる翻訳
        print(f"[*] ChatGPTで翻訳します ({get_model_name_from_args_chatgpt(args.chatgpt)})")
        translator = TranslatorChatGPT(total=total_len, desc=desc, args=args)
    else:
        # Google翻訳
        translator = TranslatorSeleniumGoogletrans(total=total_len, desc=desc, args=args)

    # ChatGPTのとき、翻訳編集者に表示する内容を修正
    if args.chatgpt:
        if len(obj[RfcJsonElem.UPDATED_BY].strip()) == 0:
            obj[RfcJsonElem.UPDATED_BY] = '自動生成(GPT)'

    try:
        # タイトルの翻訳
        if not obj[RfcJsonElem.TITLE].get(RfcJsonElem.Title.JA):
            titles = obj[RfcJsonElem.TITLE][RfcJsonElem.Title.TEXT].split(' - ', 1)  # "RFC XXXX - Title"
            if len(titles) <= 1:
                obj[RfcJsonElem.TITLE][RfcJsonElem.Title.JA] = "RFC %s" % rfc_number
            else:
                text = titles[1]
                ja = translator.translate(text)
                obj[RfcJsonElem.TITLE][RfcJsonElem.Title.JA] = "RFC %s - %s" % (rfc_number, ja)

        # 段落の翻訳
        for i, obj_contents_i in enumerate(obj[RfcJsonElem.CONTENTS]):

            # 既に翻訳済みの段落はスキップする
            if obj_contents_i.get(RfcJsonElem.Contents.JA):
                translator.increment_progress()  # 進捗+1
                continue

            # 英語原文
            text = obj_contents_i[RfcJsonElem.Contents.TEXT]
            # 英語原文の前文字（箇条書きの記号などを翻訳しないようにするため）
            pre_text = ""
            # 日本語翻訳文
            text_ja = ""

            # 箇条書きのパターン
            # 「-」「o」「*」「+」「$」「A.」「A.1.」「a)」「1)」「(a)」「(1)」「[1]」「[a]」「a.」
            pattern = r'^([\-o\*\+\$] |(?:[A-Z]\.)?(?:\d{1,2}\.)+(?:\d{1,2})? |\(?[0-9a-z]\) |\[[0-9a-z]{1,2}\] |[a-z]\. )(.*)$'

            if obj_contents_i.get(RfcJsonElem.Contents.RAW) is True:
                # 図表は翻訳しない
                pre_text, text = ('', '')
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = pre_text + text_ja  # 翻訳結果を格納
            elif m := re.match(pattern, text):
                # 記号的意味を持つ文字から始まる文は箇条書きなので、その前文字を除外して翻訳する。
                pre_text, text = m[1], m[2]
                # 翻訳の実行
                text_ja = translator.translate(text)
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = pre_text + text_ja  # 翻訳結果を格納
                translator.increment_progress()  # 進捗+1
            elif m := re.match(r'^Appendix ([A-Z])\. (.*)$', text):
                # 原文がセクション付録の場合
                pre_text, text = (f'付録{m[1]}. ', m[2])
                # 翻訳の実行
                text_ja = translator.translate(text)
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = pre_text + text_ja  # 翻訳結果を格納
                translator.increment_progress()  # 進捗+1
            else:
                # 通常の本文
                pre_text, text = ('', text)
                # 翻訳の実行
                text_ja = translator.translate(text)
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = pre_text + text_ja  # 翻訳結果を格納
                translator.increment_progress()  # 進捗+1

        print("", flush=True)

        # 正常終了した時
        # 翻訳成果物をファイルに出力する
        RfcFile.write_json_file(output_file, obj)
        print(f"[+] Save file: {output_file}")
        # 不要な入力ファイルの削除
        os.remove(input_file)
        print(f"[+] Delete file: {input_file}")
        # 不要な中間ファイルの削除
        if os.path.isfile(midway_file):
            os.remove(midway_file)
            print(f"[+] Delete file: {midway_file}")
        return True

    except (NoSuchElementException, TimeoutException, WebDriverException, MyTranslateException, KeyboardInterrupt) as e:
        # NoSuchElementException: Google翻訳で別のページが返ってきたときに発生する例外
        # TimeoutException: ネットワークなどの問題で発生する例外
        # WebDriverException: メモリ不足などでWebDriverがエラーしたとき
        # KeyboardInterrupt: ユーザが意図的に処理を停止したときに発生する例外
        print(f'[-] Translator Error! ({RfcUtils.get_now()})')
        print(f'[-] error={e}')

        # 異常終了した時
        # 途中まで翻訳済みのファイルを生成する
        RfcFile.write_json_file(midway_file, obj)
        print(f"[+] Save file: {midway_file}")
        # 例外をそのまま投げる
        raise

    finally:
        translator.close()


def trans_test():
    import argparse
    args = argparse.Namespace()
    args.chatgpt = CHATGPT_MODEL35
    # translator = TranslatorSeleniumGoogletrans(total=1)
    # ja = translator.translate('test sample.')
    translator = TranslatorChatGPT(total=1, args=args)
    ja = translator.translate('psk')
    print('[+] result:', ja)

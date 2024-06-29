# ------------------------------------------------------------------------------
# RFCの文章を翻訳するプログラム
# ------------------------------------------------------------------------------

import os
import re
import time
import platform
from pprint import pprint
import abc
from tqdm import tqdm  # pip install tqdm
from ...rfc_utils import RfcUtils
from ...rfc_const import RfcFile, RfcJsonElem
from ..models.rfc import IRfc, Rfc, RfcDraft
from ..repository.irfcjsondatarepository import IRfcJsonDataRepository
from ..repository.irfcjsontransrepository import IRfcJsonTransRepository
from ..repository.irfcjsontransmidwayrepository import IRfcJsonTransMidwayRepository
from dotenv import load_dotenv  # pip install python-dotenv

# GoogleTranslator
import urllib.parse
from selenium import webdriver  # pip install selenium
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
# ChatGPT
from ...nlp_utils import openai, ChatGPT

# 環境変数の読み込み
load_dotenv()

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
    'client:': 'クライアント:',
    'server:': 'サーバ:',
    'value:': '値：',
    'for example:': '例えば：',
    'notation and terminology': '表記と用語',
    'conventions and terminology': '規則と用語',
    'preliminaries': '前提条件',
}


class MyTranslateException(Exception):
    """翻訳処理例外"""
    pass


class Translator(abc.ABC):
    """翻訳処理抽象クラス"""

    def __init__(self, total, desc='', args=None):
        self.count = 0
        self.total = total
        # プログレスバー
        bar_format = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}{postfix}]"
        self.bar = tqdm(total=total, desc=desc, bar_format=bar_format)
        # 初期化
        self._init_process(args)

    def increment_progress(self, incr=1):
        """進捗の更新"""
        # プログレスバー用の出力
        self.count += incr
        self.bar.update(incr)

    def output_progress(self, len, wait_time):
        """進捗の詳細情報の更新"""
        # プログレスバーに詳細情報を追加
        self.bar.set_postfix(len=len, sleep=('%.1f' % wait_time))

    def translate(self, text: str) -> str:
        """英語から日本語への翻訳"""
        text = text.strip()
        if len(text) == 0:
            return ""
        # 特定の用語については、翻訳ルール(trans_rules)で翻訳する
        ja = trans_rules.get(text.lower())
        if ja:
            return ja
        return self._translate_process(text)

    def close(self):
        """翻訳終了処理"""
        return True

    @abc.abstractmethod
    def _init_process(self):
        # 子クラスで実装する翻訳開始処理
        pass

    @abc.abstractmethod
    def _translate_process(self, text: str) -> str:
        # 子クラスで実装する翻訳処理
        raise MyTranslateException()


class TranslatorSeleniumGoogletrans(Translator):
    """Selenium + Google による翻訳処理"""

    def _init_process(self, args):
        self.args = args
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
            # browser = webdriver.Firefox(options=options)
            domain = os.environ.get('WEBDRIVER_DOMAIN', 'localhost:4444')
            browser = webdriver.Remote(
                command_executor=f'http://{domain}/wd/hub',
                options=webdriver.ChromeOptions()
            )
        browser.implicitly_wait(3)
        self._browser = browser

    def _translate_process(self, text: str) -> str:
        for _ in range(0, 3):
            browser = self._browser
            # 翻訳したい文をURLに埋め込んでからアクセスする
            text_for_url = urllib.parse.quote_plus(text, safe='()|')
            # url = "https://translate.google.co.jp/#en/{1}/{0}".format(text_for_url, 'ja')
            url = "https://translate.google.co.jp/?hl=ja&sl=en&tl=ja&text={0}&op=translate".format(text_for_url)
            if self.args.debug:
                pprint(f'[+] url: {url}')
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

            # 翻訳結果の微修正
            ja = re.sub('https：', 'https:', ja)

            return ja

        # リトライしても翻訳結果が空文字のときは例外とする
        raise MyTranslateException(f'Translated text is empty string!\ninput text: "{text}"\nsend url: "{url}"')

    def close(self):
        if self._browser is None:
            return True
        return self._browser.quit()


class TranslatorGoogleV2(Translator):

    # 最初の50万文字（1か月あたり）     無料（毎月$10分のクレジットとして適用）
    # 50万文字以上（1か月あたり）       $20（100 文字あたり）

    def _init_process(self, args):
        self.args = args

    def _translate_process(target: str, text: str) -> dict:

        from dotenv import load_dotenv  # pip install python-dotenv
        # 環境変数の読み込み
        load_dotenv()
        # ※環境変数GOOGLE_APPLICATION_CREDENTIALS にクレデンシャルファイルのパスを記載すること
    
        from google.cloud import translate_v2 as translate

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


def trans_rfc(rfc: IRfc,
              rfc_json_data_repo: IRfcJsonDataRepository,
              rfc_json_trans_repo: IRfcJsonTransRepository,
              rfc_json_trans_midway_repo: IRfcJsonTransMidwayRepository,
              args) -> bool:
    """指定したRFCを翻訳する"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_data_repo, IRfcJsonDataRepository)
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)
    assert isinstance(rfc_json_trans_midway_repo, IRfcJsonTransMidwayRepository)

    print(f"[*] trans_rfc({rfc.get_id()})")

    input_file = RfcFile.get_filepath_data_json(rfc)
    output_file = RfcFile.get_filepath_data_trans_json(rfc)
    midway_file = RfcFile.get_filepath_data_midway_json(rfc)

    if os.path.isfile(midway_file):
        print(f'[+] found midway file: {midway_file}')
        # 途中まで翻訳済みのファイルがあれば復元する
        obj = rfc_json_trans_midway_repo.find(rfc)
    else:
        obj = rfc_json_data_repo.find(rfc)

    # 翻訳対象の段落数
    total_len = len([con for con in obj[RfcJsonElem.CONTENTS] if not con.get(RfcJsonElem.Contents.RAW)])
    desc = 'RFC %s' % rfc.get_id()
    # 翻訳機の選択
    if args.chatgpt:
        # ChatGPTによる翻訳
        print(f"[*] ChatGPTで翻訳します ({ChatGPT.get_exact_model_name(args.chatgpt)})")
        translator = TranslatorChatGPT(total=total_len, desc=desc, args=args)
    else:
        # Google翻訳
        print(f"[*] Google翻訳で翻訳します")
        translator = TranslatorSeleniumGoogletrans(total=total_len, desc=desc, args=args)
        # translator = TranslatorGoogleV2(total=total_len, desc=desc, args=args)

    # ChatGPTのとき、翻訳編集者に表示する内容を修正
    if args.chatgpt:
        if len(obj[RfcJsonElem.UPDATED_BY].strip()) == 0:
            obj[RfcJsonElem.UPDATED_BY] = '自動生成(GPT)'

    try:
        # タイトルの翻訳
        if not obj[RfcJsonElem.TITLE].get(RfcJsonElem.Title.JA):
            titles = obj[RfcJsonElem.TITLE][RfcJsonElem.Title.TEXT].split(' - ', 1)  # "RFC XXXX - Title"
            if len(titles) <= 1:
                obj[RfcJsonElem.TITLE][RfcJsonElem.Title.JA] = "RFC %s" % rfc.get_id()
            else:
                text = titles[1]
                ja = translator.translate(text)
                obj[RfcJsonElem.TITLE][RfcJsonElem.Title.JA] = "RFC %s - %s" % (rfc.get_id(), ja)

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
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = ''  # 翻訳結果を格納
            elif m := re.match(r'^([a-zA-Z]{1,3}:)$', text):
                # 数式の変数説明は翻訳しない
                text = m[1]
                obj[RfcJsonElem.CONTENTS][i][RfcJsonElem.Contents.JA] = text  # 原文をそのまま格納
                translator.increment_progress()  # 進捗+1
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

        if args.chatgpt:
            # 翻訳結果チェック
            is_translation_failed = False
            for i, obj_contents_i in enumerate(obj[RfcJsonElem.CONTENTS]):
                ja_text = obj_contents_i[RfcJsonElem.Contents.JA]
                if len(re.findall(r'翻訳(?:できません|する)|I\'m sorry|入力がありません|入力をそのまま出力します|そのままの文章', ja_text)) > 0:
                    is_translation_failed = True
                    en_text = obj_contents_i[RfcJsonElem.Contents.TEXT]
                    print(f"[-] ChatGPT翻訳失敗：{en_text}")
            if is_translation_failed:
                print(f"[-] 一部の原文で翻訳が失敗しました。内容を確認して手動修正してください！")

        # 正常終了した時
        # 翻訳成果物をファイルに出力する
        rfc_json_trans_repo.save(rfc, obj)
        print(f"[+] Save file: {output_file}")
        # 不要な入力ファイルの削除
        if rfc_json_data_repo.delete(rfc):
            print(f"[+] Delete file: {input_file}")
        # 不要な中間ファイルの削除
        if rfc_json_trans_midway_repo.delete(rfc):
            print(f"[+] Delete file: {midway_file}")
        return True

    except (NoSuchElementException, TimeoutException, WebDriverException, MyTranslateException, KeyboardInterrupt, Exception) as e:
        # NoSuchElementException: Google翻訳で別のページが返ってきたときに発生する例外
        # TimeoutException: ネットワークなどの問題で発生する例外
        # WebDriverException: メモリ不足などでWebDriverがエラーしたとき
        # KeyboardInterrupt: ユーザが意図的に処理を停止したときに発生する例外
        print(f'[-] Translator Error! ({RfcUtils.get_now()})')
        print(f'[-] error={e}')

        # 異常終了した時
        # 途中まで翻訳済みのファイルを生成する
        rfc_json_trans_midway_repo.save(rfc, obj)
        print(f"[+] Save file: {midway_file}")
        # 例外をそのまま投げる
        raise

    finally:
        translator.close()


def trans_test(args):
    """翻訳処理の動作確認テスト"""
    # import argparse
    # args = argparse.Namespace()
    # args.chatgpt = ChatGPT.MODEL35
    translator = TranslatorSeleniumGoogletrans(total=1, args=args)
    # translator = TranslatorGoogleV2(total=1, args=args)
    # ja = translator.translate('test sample.')
    # translator = TranslatorChatGPT(total=1, args=args)
    # ja = translator.translate('psk')
    ja = translator.translate('The first stems from the fact that entanglement enables stronger-than-classical correlations, leading to opportunities for tasks that require coordination. As a trivial example, consider the problem of consensus between two nodes who want to agree on the value of a single bit. They can use the quantum network to prepare the state (|00⟩ + |11⟩)/sqrt(2) with each node holding one of the two qubits. Once either of the two nodes performs a measurement, the state of the two qubits collapses to either |00⟩ or |11⟩, so whilst the outcome is random and does not exist before measurement, the two nodes will always measure the same value. We can also build the more general multi-qubit state (|00...⟩ + |11...⟩)/sqrt(2) and perform the same algorithm between an arbitrary number of nodes. These stronger-than-classical correlations generalise to measurement schemes that are more complicated as well.')
    print('[+] result:', ja)
    translator.increment_progress()

# ------------------------------------------------------------------------------
# RFCの文章を翻訳するプログラム
# ------------------------------------------------------------------------------

import os
import re
import json
import time
from tqdm import tqdm  # pip install tqdm
import urllib.parse
from selenium import webdriver  # pip install selenium
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
import platform
from .rfc_utils import RfcUtils
from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')

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
    "the key words \"must\", \"must not\", \"required\", \"shall\", \"shall not\", \"should\", \"should not\", \"recommended\", \"may\", and \"optional\" in this document are to be interpreted as described in rfc 2119 [rfc2119].":
        "この文書のキーワード \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", および \"OPTIONAL\" はRFC 2119 [RFC2119]で説明されているように解釈されます。",
    "the key words \"must\", \"must not\", \"required\", \"shall\", \"shall not\", \"should\", \"should not\", \"recommended\", \"not recommended\", \"may\", and \"optional\" in this document are to be interpreted as described in bcp 14 [rfc2119] [rfc8174] when, and only when, they appear in all capitals, as shown here.":
        "この文書のキーワード \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", および \"OPTIONAL\" はBCP 14 [RFC2119] [RFC8174]で説明されているように、すべて大文字の場合にのみ解釈されます。",
    "this document is subject to bcp 78 and the ietf trust's legal provisions relating to ietf documents (https://trustee.ietf.org/license-info) in effect on the date of publication of this document. please review these documents carefully, as they describe your rights and restrictions with respect to this document. code components extracted from this document must include simplified bsd license text as described in section 4.e of the trust legal provisions and are provided without warranty as described in the simplified bsd license.":
        "このドキュメントは、このドキュメントの発行日に有効なBCP 78およびIETFドキュメントに関連するIETFトラストの法的規定（https://trustee.ietf.org/license-info）の対象となります。 これらのドキュメントは、このドキュメントに関するお客様の権利と制限について説明しているため、注意深く確認してください。 このドキュメントから抽出されたコードコンポーネントには、Trust LegalProvisionsのセクション4.eで説明されているSimplifiedBSD Licenseテキストが含まれている必要があり、Simplified BSDLicenseで説明されているように保証なしで提供されます。",
}


# 翻訳処理例外
class MyTranslateException(Exception):
    pass


# 翻訳抽象クラス
class Translator:

    def __init__(self, total, desc=''):
        self.count = 0
        self.total = total
        # プログレスバー
        bar_format = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}{postfix}]"
        self.bar = tqdm(total=total, desc=desc, bar_format=bar_format)

    def increment_progress(self, incr=1):
        # プログレスバー用の出力
        self.count += incr
        self.bar.update(incr)

    def output_progress(self, len, wait_time):
        # プログレスバーに詳細情報を追加
        self.bar.set_postfix(len=len, sleep=('%.1f' % wait_time))

    def close(self):
        return True


class TranslatorSeleniumGoogletrans(Translator):
    # Selenium + Google

    def __init__(self, total, desc=''):
        super(TranslatorSeleniumGoogletrans, self).__init__(total, desc)

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

    def translate(self, text: str, dest='ja') -> str:
        if len(text) == 0:
            return ""
        # 特定の用語については、翻訳ルール(trans_rules)で翻訳する
        ja = trans_rules.get(text.lower())
        if ja:
            return ja

        # URLエンコード
        text = text.replace('%', '%25')  # 「%」をURLエンコードする
        text = text.replace('|', '%7C')  # 「|」をURLエンコードする
        text = text.replace('/', '%2F')  # 「/」をURLエンコードする

        for i in range(0, 3):
            browser = self._browser
            # 翻訳したい文をURLに埋め込んでからアクセスする
            text_for_url = urllib.parse.quote_plus(text, safe='')
            url = "https://translate.google.co.jp/#en/{1}/{0}".format(text_for_url, dest)
            # print('[+] url:', url)
            browser.get(url)
            # 数秒待機する
            wait_time = 3 + len(text) / 1000
            self.output_progress(len=len(text), wait_time=wait_time)  # プログレスバーに詳細情報を追加
            time.sleep(wait_time)
            # 翻訳結果を抽出する
            elems = browser.find_elements(By.CSS_SELECTOR, "span[jsname='W297wb']")
            ja = "\n".join(elem.text for elem in elems)
            ja = re.sub(r'(?<!\n)\n(?!\n)', '', ja)
            # 翻訳結果が空文字のときは別のCSSセレクタでリトライする（例：224.0.0.18を翻訳するとURLになって構造が変わるため）
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
        raise MyTranslateException(f"Translated text is empty string! input text: {text}")

    def close(self):
        if self._browser is None:
            return True
        return self._browser.quit()


def chunks(alist: list, n: int):
    for i in range(0, len(alist), n):
        yield alist[i:i + n]

def trans_rfc(rfc_number: int | str) -> bool:

    # 整数はRFC、文字列はDraft
    if type(rfc_number) is int:
        # 通常のRFCのとき
        input_dir = 'data/%04d' % (rfc_number // 1000 % 10 * 1000)
        input_file = f'{input_dir}/rfc{rfc_number}.json'
        output_file = f'{input_dir}/rfc{rfc_number}-trans.json'
        midway_file = f'{input_dir}/rfc{rfc_number}-midway.json'
    elif m := re.match(r'draft-(?P<org>[^-]+)-(?P<wg>[^-]+)-(?P<name>.+)', rfc_number):
        # ドラフト版のRFCのとき
        organization   = m['org']
        working_group  = m['wg']
        rfc_draft_name = m['name']
        input_dir = f'data/draft/{working_group}'
        input_file = f'{input_dir}/draft-{organization}-{working_group}-{rfc_draft_name}.json'
        output_file = f'{input_dir}/draft-{organization}-{working_group}-{rfc_draft_name}-trans.json'
        midway_file = f'{input_dir}/draft-{organization}-{working_group}-{rfc_draft_name}-midway.json'
    else:
        raise RuntimeError(f"fetch_rfc: Unknown format number={rfc_number}")

    if os.path.isfile(midway_file):  # 途中まで翻訳済みのファイルがあれば復元する
        obj = RfcUtils.read_json_file(midway_file)
    else:
        obj = RfcUtils.read_json_file(input_file)

    translator = TranslatorSeleniumGoogletrans(
        total=len(obj['contents']),
        desc='RFC %s' % rfc_number)
    # is_canceled = False

    try:
        # タイトルの翻訳
        if not obj['title'].get('ja'):
            titles = obj['title']['text'].split(' - ', 1)  # "RFC XXXX - Title"
            if len(titles) <= 1:
                obj['title']['ja'] = "RFC %s" % rfc_number
            else:
                text = titles[1]
                ja = translator.translate(text)
                obj['title']['ja'] = "RFC %s - %s" % (rfc_number, ja)

        # 段落の翻訳
        for i, obj_contents_i in enumerate(obj['contents']):

            # 既に翻訳済みの段落はスキップする
            if obj_contents_i.get('ja'):
                translator.increment_progress()  # 進捗+1
                continue

            # 英語原文
            text = obj_contents_i['text']
            # 英語原文の前文字（箇条書きの記号などを翻訳しないようにするため）
            pre_text = ""
            # 日本語翻訳文
            text_ja = ""

            # 箇条書きのパターン
            # 「-」「o」「*」「+」「$」「A.」「A.1.」「a)」「1)」「(a)」「(1)」「[1]」「[a]」「a.」
            pattern = r'^([\-o\*\+\$] |(?:[A-Z]\.)?(?:\d{1,2}\.)+(?:\d{1,2})? |\(?[0-9a-z]\) |\[[0-9a-z]{1,2}\] |[a-z]\. )(.*)$'

            if obj_contents_i.get('raw') is True:
                # 図表は翻訳しない
                pre_text, text = ('', '')
            elif m := re.match(pattern, text):
                # 記号的意味を持つ文字から始まる文は箇条書きなので、その前文字を除外して翻訳する。
                pre_text, text = m[1], m[2]
            elif m := re.match(r'^Appendix ([A-Z])\. (.*)$', text):
                # 原文がセクション付録の場合
                pre_text, text = (f'付録{m[1]}. ', m[2])
            else:
                # 通常の本文
                pre_text, text = ('', text)

            # 翻訳の実行
            text_ja = translator.translate(text)

            # 翻訳結果を格納
            obj['contents'][i]['ja'] = pre_text + text_ja

            translator.increment_progress()  # 進捗+1

        print("", flush=True)

        # 正常終了した時
        # 翻訳成果物をファイルに出力する
        RfcUtils.write_json_file(output_file, obj)
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
        print(f'[-] Translator Error! ({datetime.now(JST)})')
        print(f'[-] error={e}')

        # 異常終了した時
        # 途中まで翻訳済みのファイルを生成する
        RfcUtils.write_json_file(midway_file, obj)
        print(f"[+] Save file: {midway_file}")
        # 例外をそのまま投げる
        raise

    finally:
        translator.close()


def trans_test() -> bool:
    translator = TranslatorSeleniumGoogletrans(total=1)
    ja = translator.translate('test sample.', dest='ja')
    print('[+] result:', ja)


if __name__ == '__main__':
    trans_test()

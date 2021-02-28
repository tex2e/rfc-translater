
import os
import re
import json
import time
from googletrans import Translator as GoogleTranslater # pip install googletrans
from tqdm import tqdm # pip install tqdm
from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')
import urllib.parse
from selenium import webdriver  # pip install selenium
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException

trans_rules = {
    'abstract': '概要',
    'introduction': 'はじめに',
    'acknowledgement': '謝辞',
    'acknowledgements': '謝辞',
    'status of this memo': '本文書の状態',
    'copyright notice': '著作権表示',
    'table of contents': '目次',
    'conventions': '規約',
    'terminology': '用語',
    'discussion': '考察',
    'references': '参考文献',
    'normative references': '引用文献',
    'informative references': '参考引用',
    'contributors': '貢献者',
    'where': 'ただし',
    'where:': 'ただし：',
    'assume:': '前提：',
    "The key words \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", and \"OPTIONAL\" in this document are to be interpreted as described in RFC 2119 [RFC2119].": 
        "この文書のキーワード \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", および \"OPTIONAL\" はRFC 2119 [RFC2119]で説明されているように解釈されます。",
    "The key words \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"NOT RECOMMENDED\", \"MAY\", and \"OPTIONAL\" in this document are to be interpreted as described in BCP 14 [RFC2119] [RFC8174] when, and only when, they appear in all capitals, as shown here.": 
        "この文書のキーワード \"MUST\", \"MUST NOT\", \"REQUIRED\", \"SHALL\", \"SHALL NOT\", \"SHOULD\", \"SHOULD NOT\", \"RECOMMENDED\", \"MAY\", および \"OPTIONAL\" はBCP 14 [RFC2119] [RFC8174]で説明されているように、すべて大文字の場合にのみ解釈されます。",
    "This document is subject to BCP 78 and the IETF Trust's Legal Provisions Relating to IETF Documents (https://trustee.ietf.org/license-info) in effect on the date of publication of this document. Please review these documents carefully, as they describe your rights and restrictions with respect to this document. Code Components extracted from this document must include Simplified BSD License text as described in Section 4.e of the Trust Legal Provisions and are provided without warranty as described in the Simplified BSD License.": 
        "このドキュメントは、このドキュメントの発行日に有効なBCP 78およびIETFドキュメントに関連するIETFトラストの法的規定（https://trustee.ietf.org/license-info）の対象となります。 これらのドキュメントは、このドキュメントに関するお客様の権利と制限について説明しているため、注意深く確認してください。 このドキュメントから抽出されたコードコンポーネントには、Trust LegalProvisionsのセクション4.eで説明されているSimplifiedBSD Licenseテキストが含まれている必要があり、Simplified BSDLicenseで説明されているように保証なしで提供されます。",
}

class TransMode:
    PY_GOOGLETRANS  = 1
    SELENIUM_GOOGLE = 2


# 翻訳抽象クラス
class Translator:

    def __init__(self, total, desc=''):
        self.count = 0
        self.total = total
        # プログレスバー
        bar_format = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}{postfix}]"
        self.bar = tqdm(total=total, desc=desc, bar_format=bar_format)

    def increment_count(self, incr=1):
        # プログレスバー用の出力
        self.count += incr
        self.bar.update(incr)

    def output_progress(self, len, wait_time):
        # プログレスバーに詳細情報を追加
        self.bar.set_postfix(len=len, sleep=('%.1f' % wait_time))


class TranslatorGoogletrans(Translator):
    # py-googletrans

    def __init__(self, total, desc=''):
        super(TranslatorGoogletrans, self).__init__(total, desc)

        self.translator = GoogleTranslater()

    def translate(self, text, dest='ja'):
        # 特定の用語については、翻訳ルール(trans_rules)で翻訳する
        ja = trans_rules.get(text.lower())
        if ja:
            return ja
        # URLエンコード処理でエラー回避用に、&の後ろに空白を入れる
        text = re.sub(r'&(#?[a-zA-Z0-9]+);', r'& \1;', text)
        # 翻訳処理
        ja = self.translator.translate(text, dest='ja')
        # 翻訳の間隔を開ける
        wait_time = 3 + len(text) / 100 # IMPORTANT!!!
        # プログレスバーに詳細情報を追加
        self.output_progress(len=len(text), wait_time=wait_time)
        time.sleep(wait_time)
        return ja.text

    def translate_texts(self, texts, dest='ja'):
        # URLエンコード処理でエラー回避用に、&の後ろに空白を入れる
        texts = list(map(lambda text: re.sub(r'&(#?[a-zA-Z0-9]+);', r'& \1;', text), texts))
        # 翻訳処理
        texts_ja = self.translator.translate(texts, dest='ja')
        res = [text_ja.text for text_ja in texts_ja]
        total_len = sum([len(t) for t in texts])
        # 翻訳の間隔を開ける
        wait_time = 5 + total_len / 1000 # IMPORTANT!!!
        # プログレスバーに詳細情報を追加
        self.output_progress(len=total_len, wait_time=wait_time)
        time.sleep(wait_time)
        # 特定の用語については、翻訳ルール(trans_rules)で翻訳する
        for i, text in enumerate(texts):
            ja = trans_rules.get(text.lower())
            if ja:
                res[i] = ja
        # 関数の括弧（）は半角に変換する
        res = [re.sub(r'（）', '()', text_ja) for text_ja in res]
        return res


class TranslatorSeleniumGoogletrans(Translator):
    # Selenium + Google

    def __init__(self, total, desc=''):
        super(TranslatorSeleniumGoogletrans, self).__init__(total, desc)

        WEBDRIVER_EXE_PATH = os.getenv('WEBDRIVER_EXE_PATH',
            default='C:\Apps\webdriver\geckodriver.exe')
        options = Options()
        options.add_argument('--headless')
        browser = webdriver.Firefox(executable_path=WEBDRIVER_EXE_PATH, options=options)
        browser.implicitly_wait(3)
        self._browser = browser

    def translate(self, text, dest='ja'):
        if len(text) == 0:
            return ""
        # 特定の用語については、翻訳ルール(trans_rules)で翻訳する
        ja = trans_rules.get(text.lower())
        if ja:
            return ja
        # 「/」をURLエンコードする
        text = text.replace('/', '%2F')

        browser = self._browser
        # 翻訳したい文をURLに埋め込んでからアクセスする
        text_for_url = urllib.parse.quote_plus(text, safe='')
        url = "https://translate.google.co.jp/#en/ja/{0}".format(text_for_url)
        browser.get(url)
        # 数秒待機する
        wait_time = 3 + len(text) / 1000
        time.sleep(wait_time)
        # 翻訳結果を抽出する
        elems = browser.find_elements_by_css_selector("span[jsname='W297wb']")
        ja = "".join(elem.text for elem in elems)
        # プログレスバーに詳細情報を追加
        self.output_progress(len=len(text), wait_time=wait_time)
        return ja

    def translate_texts(self, texts, dest='ja'):
        res = []
        for text in texts:
            ja = self.translate(text)
            res.append(ja)
            self.increment_count()
        return res


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

def trans_rfc(number, mode):

    input_dir = 'data/%04d' % (number//1000%10*1000)
    input_file = '%s/rfc%d.json' % (input_dir, number)
    output_file = '%s/rfc%d-trans.json' % (input_dir, number)
    midway_file = '%s/rfc%d-midway.json' % (input_dir, number)

    if os.path.isfile(midway_file):  # 途中まで翻訳済みのファイルがあれば復元する
        with open(midway_file, 'r', encoding="utf-8") as f:
            obj = json.load(f)
    else:
        with open(input_file, 'r', encoding="utf-8") as f:
            obj = json.load(f)

    desc = 'RFC %d' % number
    if mode == TransMode.PY_GOOGLETRANS:
        translator = TranslatorGoogletrans(total=len(obj['contents']), desc=desc)
    else:
        translator = TranslatorSeleniumGoogletrans(total=len(obj['contents']), desc=desc)
    is_canceled = False

    try:
        # タイトルの翻訳
        if not obj['title'].get('ja'):  # 既に翻訳済みの段落はスキップする
            titles = obj['title']['text'].split(' - ', 1)  # "RFC XXXX - Title"
            if len(titles) <= 1:
                obj['title']['ja'] = "RFC %d" % number
            else:
                text = titles[1]
                ja = translator.translate(text)
                obj['title']['ja'] = "RFC %d - %s" % (number, ja)

        # 段落の翻訳
        #   複数の段落をまとめて翻訳する
        CHUNK_NUM = 15
        for obj_contents in chunks(list(enumerate(obj['contents'])), CHUNK_NUM):

            texts = []     # 原文
            pre_texts = [] # 原文の前文字 (箇条書きの記号など)

            for i, obj_contents_i in obj_contents:

                # 既に翻訳済みの段落 や 図表 は翻訳しないでスキップする
                if (obj_contents_i.get('ja') or (obj_contents_i.get('raw') == True)):
                    texts.append('')
                    pre_texts.append('')
                    continue

                text = obj_contents_i['text']

                # 「-」「*」「o」「N.」などの記号的意味を持つ文字から始まる文は、その前文字を除外して翻訳
                pattern = r'^(- |\* |o |\+ |(?:[A-Z]\.)?(?:\d{1,2}\.)+(?:\d{1,2})? |[a-z]\) |\[[0-9a-z]{1,2}\] |[a-z]\. )(.*)$'
                m = re.match(pattern, text)
                if m:
                    pre_texts.append(m[1])
                    texts.append(m[2])
                else:
                    pre_texts.append('')
                    texts.append(text)

            if mode == TransMode.PY_GOOGLETRANS:
                translator.increment_count(len(texts))

            texts_ja = translator.translate_texts(texts)

            # 翻訳結果を格納
            for (i, obj_contents_i), pre_text, text_ja in \
                    zip(obj_contents, pre_texts, texts_ja):
                obj['contents'][i]['ja'] = pre_text + text_ja

        print("", flush=True)

    except json.decoder.JSONDecodeError as e:
        print('[-] googletrans is blocked by Google :(')
        print('[-]', datetime.now(JST))
        is_canceled = True
    except NoSuchElementException as e:
        print('[-] Google Translate is blocked by Google :(')
        print('[-]', datetime.now(JST))
        is_canceled = True
    except KeyboardInterrupt as e:
        print('Interrupted!')
        is_canceled = True

    if not is_canceled:
        with open(output_file, 'w', encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        # 不要になったファイルの削除
        os.remove(input_file)
        if os.path.isfile(midway_file):
            os.remove(midway_file)
        return True
    else:
        with open(midway_file, 'w', encoding="utf-8", newline="\n") as f:
            # 途中まで翻訳済みのファイルを生成する
            json.dump(obj, f, indent=2, ensure_ascii=False)
        return False


def trans_test(mode=TransMode.SELENIUM_GOOGLE):
    if mode == TransMode.PY_GOOGLETRANS:
        translator = TranslatorGoogletrans(total=1)
        ja = translator.translate('test', dest='ja')
        return ja == 'テスト'
    else:
        translator = TranslatorSeleniumGoogletrans(total=1)
        ja = translator.translate('test', dest='ja')
        print('result:', ja)
        return ja in ('テスト', 'しけん')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(total=1)
    parser.add_argument('text', help='english text')
    args = parser.parse_args()

    translator = TranslatorGoogletrans(total=1)
    ja = translator.translate(args.text, dest='ja')
    print(ja)


# googletrans:
# 連続してアクセスすると、以下のメッセージが表示されてIPアドレス単位でブロックされるので注意。
#
#
#   お使いのコンピュータ ネットワークから通常と異なるトラフィックが検出されました。
#   後でもう一度リクエストを送信してみてください。このページが表示された理由
#
#   このページは、お使いのコンピュータ ネットワークから利用規約に違反すると考えられる
#   リクエストが自動検出されたときに表示されます。
#   ブロックは、これらのリクエストが停止されると間もなく解除されます。
#
#   このトラフィックは、リクエストを自動送信する不正なソフトウェア、ブラウザ プラグイン、
#   またはスクリプトによって発生した可能性があります。ネットワーク接続が共有のものである場合は、
#   同じ IP アドレスを使用している別のコンピュータが発生元の可能性がありますので、
#   管理者に相談してください。詳しくはこちらをご覧ください。
#
#   ロボットが使用するような高度な検索語を使用したり、リクエストを非常にすばやく送信した場合も、
#   このページが表示されることがあります。
#
#   IP アドレス: XX.XX.XX.XX
#   時間: 2019-10-16T03:56:15Z
#   URL: https://translate.google.com/translate_a/single?...
#
#

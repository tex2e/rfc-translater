
import os
import re
import json
import time
from tqdm import tqdm # pip install tqdm
from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')
import urllib.parse
from selenium import webdriver  # pip install selenium
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
import platform

# ルールは必ず小文字で登録すること
trans_rules = {
    'abstract': '概要',
    'introduction': 'はじめに',
    'acknowledgement': '謝辞',
    'acknowledgements': '謝辞',
    'status of this memo': '本文書の位置付け', #'本文書の状態',
    'copyright notice': '著作権表示',
    'table of contents': '目次',
    'conventions': '規約',
    'terminology': '用語',
    'background': '背景',
    'discussion': '考察',
    'security considerations': 'セキュリティに関する考慮事項',
    'references': '参考文献',
    'normative references': '引用文献',
    'informative references': '参考引用',
    'contributors': '貢献者',
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
            WEBDRIVER_EXE_PATH = os.getenv('WEBDRIVER_EXE_PATH',
                default='C:\Apps\webdriver\geckodriver.exe')
            browser = webdriver.Firefox(executable_path=WEBDRIVER_EXE_PATH, options=options)
        else:
            # Ubuntu:
            # sudo apt install python3-pip firefox
            # sudo pip3 install selenium
            options.binary_location = '/usr/bin/firefox'
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
        # 「%」をURLエンコードする
        text = text.replace('%', '%25')
        # 「|」をURLエンコードする
        text = text.replace('|', '%7C')
        # 「/」をURLエンコードする
        text = text.replace('/', '%2F')

        browser = self._browser
        # 翻訳したい文をURLに埋め込んでからアクセスする
        text_for_url = urllib.parse.quote_plus(text, safe='')
        url = "https://translate.google.co.jp/#en/{1}/{0}".format(text_for_url, dest)
        browser.get(url)
        # 数秒待機する
        wait_time = 3 + len(text) / 1000
        time.sleep(wait_time)
        # 翻訳結果を抽出する
        elems = browser.find_elements(By.CSS_SELECTOR, "span[jsname='W297wb']")
        ja = "".join(elem.text for elem in elems)
        # プログレスバーに詳細情報を追加
        self.output_progress(len=len(text), wait_time=wait_time)
        return ja

    def translate_texts(self, texts: list[str], dest='ja') -> list[str]:
        res = []
        for text in texts:
            ja = self.translate(text)
            res.append(ja)
            self.increment_count()
        return res

    def close(self):
        if self._browser is None:
            return True
        return self._browser.quit()


def chunks(l: list, n: int) -> list:
    for i in range(0, len(l), n):
        yield l[i:i + n]

def trans_rfc(rfc_number: int | str) -> bool:

    # 整数はRFC、文字列はDraft
    if type(rfc_number) is int:
        is_draft = False
        input_dir = 'data/%04d' % (rfc_number//1000%10*1000)
        input_file = f'{input_dir}/rfc{rfc_number}.json'
        output_file = f'{input_dir}/rfc{rfc_number}-trans.json'
        midway_file = f'{input_dir}/rfc{rfc_number}-midway.json'
    elif m := re.match(r'draft-(?P<org>[^-]+)-(?P<wg>[^-]+)-(?P<name>.+)', rfc_number):
        is_draft = True
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
        with open(midway_file, 'r', encoding="utf-8") as f:
            obj = json.load(f)
    else:
        with open(input_file, 'r', encoding="utf-8") as f:
            obj = json.load(f)

    desc = 'RFC %s' % rfc_number
    translator = TranslatorSeleniumGoogletrans(total=len(obj['contents']), desc=desc)
    is_canceled = False

    try:
        # タイトルの翻訳
        if not obj['title'].get('ja'):  # 既に翻訳済みの段落はスキップする
            titles = obj['title']['text'].split(' - ', 1)  # "RFC XXXX - Title"
            if len(titles) <= 1:
                obj['title']['ja'] = "RFC %s" % rfc_number
            else:
                text = titles[1]
                ja = translator.translate(text)
                obj['title']['ja'] = "RFC %s - %s" % (rfc_number, ja)

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

                # 記号的意味を持つ文字から始まる文は箇条書きなので、その前文字を除外して翻訳する。
                # 「-」「o」「*」「+」「$」「A.」「A.1.」「a)」「1)」「(a)」「(1)」「[1]」「[a]」「a.」
                pattern = r'^([\-o\*\+\$] |(?:[A-Z]\.)?(?:\d{1,2}\.)+(?:\d{1,2})? |\(?[0-9a-z]\) |\[[0-9a-z]{1,2}\] |[a-z]\. )(.*)$'
                m = re.match(pattern, text)
                if m:
                    pre_texts.append(m[1])
                    texts.append(m[2])
                else:
                    pre_texts.append('')
                    texts.append(text)

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
    finally:
        translator.close()

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


def trans_test() -> bool:
    translator = TranslatorSeleniumGoogletrans(total=1)
    ja = translator.translate('test', dest='ja')
    print('result:', ja)
    return ja in ('テスト', 'しけん')

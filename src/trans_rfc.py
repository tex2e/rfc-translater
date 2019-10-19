
import os
import re
import json
import time


class Translator: # selenium

    def __init__(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        self.options = Options()
        self.options.add_argument('--headless')
        self.browser = webdriver.Chrome(options=self.options)
        self.browser.implicitly_wait(3)

        self.count = 0
        self.total = 0

    def translate(self, text, dest='ja'):
        from bs4 import BeautifulSoup
        import urllib.parse

        # Start translation
        text_for_url = urllib.parse.quote_plus(text, safe='')
        url = "https://translate.google.co.jp/#en/ja/{0}".format(text_for_url)
        self.browser.get(url)

        # take interval
        wait_time = 2 + len(text) / 100 # IMPORTANT!!!
        if self.total > 0:
            print('%3d/%d: ' % (self.count, self.total), end='')
        print('len(text)=%d, sleep=%.1f' % (len(text), wait_time))
        time.sleep(wait_time)

        # Get translation result
        ja = BeautifulSoup(self.browser.page_source, "html.parser").find(class_="tlid-translation translation")
        return ja.text

    def quit(self):
        self.browser.quit()


class Translator2: # googletrans

    def __init__(self):
        from googletrans import Translator as GoogleTranslater

        self.translator = GoogleTranslater()
        self.count = 0
        self.total = 0

    def translate(self, text, dest='ja'):
        ja = self.translator.translate(text, dest='ja')
        # take interval
        wait_time = 1 + len(text) / 60 # IMPORTANT!!!
        if self.total > 0:
            print('%3d/%d: ' % (self.count, self.total), end='')
        print('len(text)=%d, sleep=%.1f' % (len(text), wait_time))
        time.sleep(wait_time)
        return ja.text

    def quit(self):
        return


def _find_toc_pattern(text):
    return re.search(r'\.{5,}\d', text)

def trans_rfc(number, mode='selenium'):

    input_dir = 'data/%04d/%03d' % (number//1000%10*1000, number//100%10*100)
    input_file = '%s/rfc%d.json' % (input_dir, number)
    output_file = '%s/rfc%d-trans.json' % (input_dir, number)
    midway_file = '%s/rfc%d-midway.json' % (input_dir, number)

    if os.path.isfile(midway_file): # 途中まで翻訳済みのファイルがあれば復元する
        with open(midway_file, 'r') as f:
            obj = json.load(f)
    else:
        with open(input_file, 'r') as f:
            obj = json.load(f)

    translator = None
    if mode == 'selenium':
        translator = Translator()
    elif mode == 'googletrans':
        translator = Translator2()

    translator.count = 0
    translator.total = len(obj['contents'])
    is_canceled = False

    try:
        # タイトルの翻訳
        if not obj['title'].get('ja'): # 既に翻訳済みの段落はスキップする
            text = obj['title']['text'].split(' - ', 1)[1] # "RFC XXXX - Title"
            ja = translator.translate(text)
            obj['title']['ja'] = "RFC %d - %s" % (number, ja)

        # 段落の翻訳
        for i, paragraph in enumerate(obj['contents']):

            if paragraph.get('ja'): # 既に翻訳済みの段落はスキップする
                continue

            text = paragraph['text']

            if _find_toc_pattern(text): # TOCはページ番号を除去して翻訳する
                text = re.sub(r'\.{5,}\d+', '', text)
            elif paragraph.get('raw') == True: # 図や表は翻訳しない
                obj['contents'][i]['ja'] = ''
                continue

            translator.count = i + 1
            ja = translator.translate(text)
            obj['contents'][i]['ja'] = ja

    except json.decoder.JSONDecodeError as e:
        print('[-] googletrans is blocked by Google :(')
        is_canceled = True
    except KeyboardInterrupt as e:
        print('Interrupted!')
        is_canceled = True
    finally:
        translator.quit()

    if not is_canceled:
        with open(output_file, 'w') as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        # 不要になったファイルの削除
        os.remove(input_file)
        if os.path.isfile(midway_file):
            os.remove(midway_file)
    else:
        with open(midway_file, 'w') as f: # 途中まで翻訳済みのファイルを生成する
            json.dump(obj, f, indent=2, ensure_ascii=False)


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

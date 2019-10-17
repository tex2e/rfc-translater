
import os
import re
import json
import time


class Translator: # selenium

    def __init__(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from bs4 import BeautifulSoup
        import urllib.parse

        self.options = Options()
        self.options.add_argument('--headless')
        self.browser = webdriver.Chrome(options=self.options)
        self.browser.implicitly_wait(3)

        self.count = 0
        self.total = 0

    def translate(self, text, dest='ja'):
        # Start translation
        text_for_url = urllib.parse.quote_plus(text, safe='')
        url = "https://translate.google.co.jp/#en/ja/{0}".format(text_for_url)
        self.browser.get(url)

        # take interval
        wait_time = 1 + len(text) / 25 # IMPORTANT!!!
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
        ja = translator.translate(text, dest='ja')
        # take interval
        wait_time = 1 + len(text) / 25 # IMPORTANT!!!
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
    output_file2 = '%s/rfc%d-midway.json' % (input_dir, number)

    with open(input_file, 'r') as f:
        obj = json.load(f)

    if mode == 'googletrans':
        Translator = Translator2

    translator = Translator()
    translator.count = 0
    translator.total = len(obj['contents'])
    is_canceled = False

    try:
        text = obj['title']['text'].split(' - ', 1)[1] # "RFC XXXX - Title"
        ja = translator.translate(text)
        obj['title']['ja'] = "RFC %d - %s" % (number, ja)

        for i, paragraph in enumerate(obj['contents']):
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
        os.remove(input_file)

    else:
        with open(output_file2, 'w') as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)

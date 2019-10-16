
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import urllib.parse

import os
import re
import json
import time


class Translator:

    def __init__(self):
        self.options = Options()
        self.options.add_argument('--headless')
        self.browser = webdriver.Chrome(options=self.options)
        self.browser.implicitly_wait(3)

    def translate(self, text):
        # Start translation
        url_text = "https://translate.google.co.jp/#en/ja/{0}".format(text)
        url = urllib.parse.quote_plus(url_text, "/:?=&#")
        self.browser.get(url)

        # take interval
        wait_time = 1 + len(text) / 20
        print('len(text):', len(text), 'sleep:', wait_time)
        time.sleep(wait_time)

        # Get translation result
        ja = BeautifulSoup(self.browser.page_source, "html.parser").find(class_ = "tlid-translation translation").text

        return ja

    def quit(self):
        self.browser.quit()


def _find_toc_pattern(text):
    return re.search(r'\.{5,}\d', text)

def trans_rfc(number):

    input_dir = 'data/%04d/%03d' % (round(number, -3), round(number, -2))
    input_file = '%s/rfc%d.json' % (input_dir, number)
    output_file = '%s/rfc%d-trans.json' % (input_dir, number)
    output_file2 = '%s/rfc%d-midway.json' % (input_dir, number)

    with open(input_file, 'r') as f:
        obj = json.load(f)

    translator = Translator()
    is_canceled = False

    try:
        print('RFC %d:' % number)

        text = obj['title']['text'].split(' - ')[1] # "RFC XXXX - Title"
        ja = translator.translate(text)
        obj['title']['ja'] = "RFC %d - %s" % (number, ja)

        for i, paragraph in enumerate(obj['contents']):
            text = paragraph['text']

            if _find_toc_pattern(text): # TOCはページ番号を除去して翻訳する
                text = re.sub(r'\.{5,}\d+', '', text)
            elif paragraph.get('raw') == True: # 図や表は翻訳しない
                obj['contents'][i]['ja'] = ''
                continue

            ja = translator.translate(text)
            obj['contents'][i]['ja'] = ja

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

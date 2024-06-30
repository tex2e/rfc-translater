
import os
import re
import time
import platform
from pprint import pprint
from .metatranslater import Translator, MyTranslateException
# GoogleTranslator
import urllib.parse
from selenium import webdriver  # pip install selenium
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.common.by import By


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
        try:
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

        except (NoSuchElementException, TimeoutException, WebDriverException) as e:
            # NoSuchElementException: Google翻訳で別のページが返ってきたときに発生する例外
            # WebDriverException: メモリ不足などでWebDriverがエラーしたとき
            raise MyTranslateException() from e


    def close(self):
        if self._browser is None:
            return True
        return self._browser.quit()


import os
import time
from dotenv import load_dotenv
from selenium import webdriver  # pip install selenium
from selenium.webdriver.firefox.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException

# .envファイルからの環境変数の読み込み
load_dotenv()


class MyAccessPageException(Exception):
    """ページアクセス例外"""
    pass


class AccessPage():
    """ページアクセス処理"""

    def __init__(self) -> None:
        self._browser = None

    def initial_process(self):
        options = Options()
        options.add_argument('--headless')
        browser = None
        # Ubuntu:
        # browser = webdriver.Firefox(options=options)
        domain = os.environ.get('WEBDRIVER_DOMAIN', 'localhost:4444')
        # print(f"[*] webdriver.Remote: {domain}")
        browser = webdriver.Remote(
            command_executor=f'http://{domain}/wd/hub',
            options=webdriver.ChromeOptions()
        )
        browser.implicitly_wait(3)
        self._browser = browser

    def fetch_url(self, urls: str) -> str:
        try:
            browser = self._browser
            for url in urls:
                print(f'[*] url: {url}')
                browser.get(url)
                title = browser.title
                print(f'[*] title: {title}')
                time.sleep(3)
            return

        except (NoSuchElementException, TimeoutException, WebDriverException) as e:
            # NoSuchElementException: Google翻訳で別のページが返ってきたときに発生する例外
            # WebDriverException: メモリ不足などでWebDriverがエラーしたとき
            raise MyAccessPageException() from e

    def close(self):
        if self._browser is None:
            return True
        return self._browser.quit()



def access_page(args):

    urls = args.access_page

    assert isinstance(urls, list)

    print(f"[*] access_page({urls})")
    fetchpage = AccessPage()
    try:
        fetchpage.initial_process()
        fetchpage.fetch_url(urls)
    finally:
        fetchpage.close()


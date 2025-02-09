
import abc
from tqdm import tqdm  # pip install tqdm

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
    "the key words \"must\", \"must not\", \"required\", \"shall\", \"shall not\", \"should\", \"should not\", \"recommended\", \"not recommended\", \"may\", and \"optional\" in this document are to be interpreted as described in bcp 14 [rfc2119] [rfc8174] when, and only when, they appear in all capitals, as shown here.": 'このドキュメント内のキーワード「MUST」、「MUST NOT」、「REQUIRED」、「SHALL」、「SHALL NOT」、「SHOULD」、「SHOULD NOT」、「RECOMMENDED」、「NOT RECOMMENDED」、「MAY」、および「OPTIONAL」は、ここに示すようにすべて大文字で表示されている場合にのみ、BCP 14 [RFC2119] [RFC8174] で説明されているように解釈されます。',
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

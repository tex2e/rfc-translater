# ------------------------------------------------------------------------------
# 翻訳済みJSONからHTMLを生成するためのプログラム
# ------------------------------------------------------------------------------

import re
import textwrap
import markupsafe
from pprint import pprint
from mako.lookup import TemplateLookup
from ..models.rfc import RfcFile, RfcJsonElem, IRfc, RfcDraft
from ..repository.irfcjsontransrepository import IRfcJsonTransRepository
from ..repository.irfcjsondatasummaryrepository import IRfcJsonDataSummaryRepository
from ..repository.irfchtmlrepository import IRfcHtmlRepository


def make_html(rfc: IRfc,
              rfc_json_trans_repo: IRfcJsonTransRepository,
              rfc_json_data_summary_repo: IRfcJsonDataSummaryRepository,
              rfc_json_html_repo: IRfcHtmlRepository) -> None:
    """RFCのHTMLを作成する"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)
    assert isinstance(rfc_json_data_summary_repo, IRfcJsonDataSummaryRepository)
    assert isinstance(rfc_json_html_repo, IRfcHtmlRepository)

    print(f'[*] make_html({rfc.get_id()})')

    input_file = rfc_json_trans_repo.findpath(rfc)
    if not input_file:
        print("[-] make_html: Not found:", input_file)
        return

    # 翻訳したRFC (json) の読み込み
    obj = rfc_json_trans_repo.find(rfc)

    # ChatGPTによる要約が存在すれば、その情報 (json) の読み込み
    summary = rfc_json_data_summary_repo.find(rfc)

    # テンプレートエンジン「Mako」を使って、値をバインドする
    mylookup = TemplateLookup(directories=["./"], input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template(RfcFile.TEMPLATE_HTML_RFC)
    output = mytemplate.render_unicode(ctx=obj, summary=summary, is_draft=isinstance(rfc, RfcDraft),
                                       RfcJsonElem=RfcJsonElem, RfcHtmlHelper=RfcHtmlHelper)

    # 翻訳したRFC (html) の作成
    rfc_json_html_repo.save(rfc, output)


class RfcHtmlHelper:
    """テンプレートエンジン側に関数を渡すための汎用クラス"""

    @staticmethod
    def my_replace_filter(text):
        """HTML文字列をエスケープする"""
        text = text.replace('\n\n', '\x06\x06')
        text = str(markupsafe.escape(text))
        text = text.replace('\x06\x06', '<br>')
        return text

    @staticmethod
    def text_to_id(text: str) -> str:
        """セクションのタイトルのidを作成する"""
        tmp = text
        tmp = re.sub(r'[. ]', '-', tmp)
        tmp = re.sub(r'[^-a-zA-Z0-9]', '', tmp)
        return tmp

    @staticmethod
    def indent(text: str, prefix: str) -> str:
        """文字列（複数行可）にインデントを追加する"""
        return textwrap.indent(text, prefix)

    @staticmethod
    def get_updated_by(text: str) -> str:
        """更新者の作成"""
        if text == '':
            return "自動生成"
        return text

    @staticmethod
    def is_rfc_greater_than_or_equal_to_8650(text: str | int) -> bool:
        """RFCが8650より大きいか（XML版が存在するか）を判定する"""
        return isinstance(text, int) and text >= 8650

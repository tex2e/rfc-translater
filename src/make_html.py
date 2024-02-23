# ------------------------------------------------------------------------------
# 翻訳済みJSONからHTMLを生成するためのプログラム
# ------------------------------------------------------------------------------

import os
import re
import textwrap
import markupsafe
from pprint import pprint
from .rfc_const import RfcFile, RfcJsonElem
from mako.lookup import TemplateLookup

def make_html(rfc_number: int | str) -> None:

    if type(rfc_number) is int:
        # RFCのとき
        is_draft = False
        input_file = RfcFile.get_filepath_data_trans_json(rfc_number)
        input_summary_file = RfcFile.get_filepath_data_summary_json(rfc_number)
        output_file = RfcFile.get_filepath_html_rfc(rfc_number)
    elif m := re.match(r'draft-(?P<rfc_draft_id>.+)', rfc_number):
        # Draft版のRFCのとき
        is_draft = True
        rfc_draft_id = m['rfc_draft_id']
        input_file = RfcFile.get_filepath_data_trans_json(rfc_draft_id)
        input_summary_file = RfcFile.get_filepath_data_summary_json(rfc_draft_id)
        output_file = RfcFile.get_filepath_html_rfc(rfc_draft_id)
    else:
        raise RuntimeError(f"make_html: Unknown format number={rfc_number}")

    input_file = os.path.normpath(input_file)
    output_file = os.path.normpath(output_file)

    if not os.path.isfile(input_file):
        print("[-] make_html: Not found:", input_file)
        return

    # 翻訳したRFC (json) の読み込み
    obj = RfcFile.read_json_file(input_file)

    # ChatGPTによる要約が存在すれば、その情報 (json) の読み込み
    summary = None
    if input_summary_file != '' and os.path.exists(input_summary_file):
        summary = RfcFile.read_json_file(input_summary_file)

    # テンプレートエンジン「Mako」を使って、値をバインドする
    mylookup = TemplateLookup(directories=["./"], input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template(RfcFile.TEMPLATE_HTML_RFC)
    output = mytemplate.render_unicode(ctx=obj, summary=summary, is_draft=is_draft,
                                       RfcJsonElem=RfcJsonElem, RfcHtmlHelper=RfcHtmlHelper)

    # 翻訳したRFC (html) の作成
    RfcFile.write_html_file(output_file, output)


class RfcHtmlHelper:

    @staticmethod
    def my_replace_filter(text):
        text = text.replace('\n\n', '\x06\x06')
        text = str(markupsafe.escape(text))
        text = text.replace('\x06\x06', '<br>')
        return text

    @staticmethod
    def text_to_id(text: str) -> str:
        tmp = text
        tmp = re.sub(r'[. ]', '-', tmp)
        tmp = re.sub(r'[^-a-zA-Z0-9]', '', tmp)
        return tmp

    @staticmethod
    def indent(text: str, prefix: str) -> str:
        return textwrap.indent(text, prefix)

    @staticmethod
    def get_updated_by(text: str) -> str:
        if text == '':
            return "自動生成"
        return text


if __name__ == '__main__':
    pass

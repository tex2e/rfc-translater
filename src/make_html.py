# ------------------------------------------------------------------------------
# 翻訳済みJSONからHTMLを生成するためのプログラム
# ------------------------------------------------------------------------------

import os
import re
from mako.lookup import TemplateLookup
from .rfc_const import RfcFile

def make_html(rfc_number: int | str) -> None:

    if type(rfc_number) is int:
        # RFCのとき
        is_draft = False
        input_file = RfcFile.get_filepath_trans_json(rfc_number)
        input_summary_file = RfcFile.get_filepath_summary_json(rfc_number)
        output_file = RfcFile.get_filepath_rfc_html(rfc_number)
    elif m := re.match(r'draft-(?P<rfc_draft_id>.+)', rfc_number):
        # Draft版のRFCのとき
        is_draft = True
        rfc_draft_id = m['rfc_draft_id']
        input_file = RfcFile.get_filepath_trans_json(rfc_draft_id)
        input_summary_file = RfcFile.get_filepath_summary_json(rfc_draft_id)
        output_file = RfcFile.get_filepath_rfc_html(rfc_draft_id)
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
    output = mytemplate.render_unicode(ctx=obj, summary=summary, is_draft=is_draft)

    # 翻訳したRFC (html) の作成
    RfcFile.write_html_file(output_file, output)

if __name__ == '__main__':
    pass

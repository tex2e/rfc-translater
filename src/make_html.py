# ------------------------------------------------------------------------------
# 翻訳済みJSONからHTMLを生成するためのプログラム
# ------------------------------------------------------------------------------

import os
import re
import json
from mako.lookup import TemplateLookup
from .rfc_utils import RfcUtils
from .rfc_const import RfcFile

def make_html(rfc_number: int | str) -> None:

    # 変数の初期化
    if type(rfc_number) is int:  # RFCは整数
        is_draft = False
        input_file = RfcFile.get_filepath_trans_json(rfc_number)
        input_summary_file = RfcFile.get_filepath_summary_json(rfc_number)
        output_dir = RfcFile.OUTPUT_HTML_DIR
        output_file = RfcFile.get_filepath_rfc_html(rfc_number)
    elif m := re.match(r'draft-(?P<org>[^-]+)-(?P<wg>[^-]+)-(?P<name>.+)', rfc_number):  # Draftは文字列
        is_draft = True
        organization   = m['org']
        working_group  = m['wg']
        rfc_draft_name = m['name']
        input_dir = f'data/draft/{working_group}'
        input_file = f'{input_dir}/draft-{organization}-{working_group}-{rfc_draft_name}-trans.json'
        input_summary_file = ''
        output_dir = 'html/draft'
        output_file = f'{output_dir}/draft-{organization}-{working_group}-{rfc_draft_name}.html'
    else:
        raise RuntimeError(f"make_html: Unknown format number={rfc_number}")

    input_file = os.path.normpath(input_file)
    output_file = os.path.normpath(output_file)

    if not os.path.isfile(input_file):
        print("[-] make_html: Not found:", input_file)
        return

    # 翻訳したRFC (json) の読み込み
    obj = RfcUtils.read_json_file(input_file)

    # ChatGPTによる要約が存在すれば、その情報 (json) の読み込み
    summary = None
    if input_summary_file != '' and os.path.exists(input_summary_file):
        with open(input_summary_file) as f:
            summary = json.load(f)

    # テンプレートエンジン「Mako」を使って、値をバインドする
    mylookup = TemplateLookup(
        directories=["./"],
        input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template(RfcFile.TEMPLATE_HTML_RFC)
    output = mytemplate.render_unicode(ctx=obj, summary=summary, is_draft=is_draft)

    # 出力ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)

    # 翻訳したRFC (html) の作成
    with open(output_file, 'w', encoding="utf-8", newline="\n") as f:
        f.write(output)


if __name__ == '__main__':
    # import argparse
    # parser = argparse.ArgumentParser()
    # parser.add_argument('rfc_number', type=int)
    # args = parser.parse_args()
    # make_html(args.rfc_number)
    pass

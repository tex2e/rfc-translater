
import os
import json
from mako.template import Template
from mako.lookup import TemplateLookup

def make_html(rfc_number):
    input_dir = 'data/%04d' % (rfc_number//1000%10*1000)
    input_file = '%s/rfc%d-trans.json' % (input_dir, rfc_number)
    output_dir = 'html'
    output_file = '%s/rfc%d.html' % (output_dir, rfc_number)

    input_file = os.path.normpath(input_file)
    output_file = os.path.normpath(output_file)

    if not os.path.isfile(input_file):
        print("make_html: Not found:", input_file)
        return

    # 翻訳したRFC (json) の読み込み
    with open(input_file, 'r', encoding="utf-8") as f:
        obj = json.load(f)

    # テンプレートエンジン「Mako」を使って、値をバインドする
    mylookup = TemplateLookup(
        directories=["./"],
        input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template('templates/rfc.html')
    output = mytemplate.render_unicode(ctx=obj)

    # 出力ディレクトリの作成
    os.makedirs(output_dir, exist_ok=True)

    # 翻訳したRFC (html) の作成
    with open(output_file, 'w', encoding="utf-8", newline="\n") as f:
        f.write(output)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_number', type=int)
    args = parser.parse_args()

    make_html(args.rfc_number)

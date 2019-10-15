
import os
import re
import json
from googletrans import Translator

def _find_code_pattern(text):
    return text.find('---') >= 0

def _find_toc_pattern(text):
    return re.search(r'\.{5,}\d', text)

def trans_rfc(number):

    input_dir = 'data/%04d/%03d' % (round(number, -3), round(number, -2))
    input_file = '%s/rfc%d.json' % (input_dir, number)
    output_file = '%s/rfc%d-trans.json' % (input_dir, number)

    with open(input_file, 'r') as f:
        obj = json.load(f)

    translator = Translator()

    for i, paragraph in enumerate(obj):

        text = paragraph['text']
        if _find_code_pattern(text): # 図や表は翻訳しない
            obj[i]['ja'] = ''
            continue

        if _find_toc_pattern(text): # TOCのページ番号を除去する
            text = re.sub(r'\.{5,}\d+', '', text)

        ja = translator.translate(text, dest='ja')
        obj[i]['ja'] = ja.text

    with open(output_file, 'w') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

    os.remove(input_file)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_number', type=int)
    args = parser.parse_args()

    trans_rfc(args.rfc_number)

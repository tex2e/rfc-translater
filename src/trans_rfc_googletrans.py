
# Don't use!

# from googletrans import Translator
# translator = Translator()
# translator.translate('Test', dest='ja')

import os
import re
import json
from googletrans import Translator
import time

def _find_code_pattern(text):
    return text.find('---') >= 0

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
        for i, paragraph in enumerate(obj['contents']):
            text = paragraph['text']

            if _find_toc_pattern(text): # TOCはページ番号を除去して翻訳する
                text = re.sub(r'\.{5,}\d+', '', text)
            elif paragraph.get('raw') == True: # 図や表は翻訳しない
                obj['contents'][i]['ja'] = ''
                continue

            try:
                ja = translator.translate(text, dest='ja')
            except json.decoder.JSONDecodeError as e:
                print(e)
                print('[-] googletrans is blocked by Google :(')
                is_canceled = True
                break

            obj['contents'][i]['ja'] = ja.text

            wait_time = len(text) / 20
            time.sleep(wait_time)

    except KeyboardInterrupt as e:
        print('Interrupted!')
        is_canceled = True

    if not is_canceled:
        with open(output_file, 'w') as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        os.remove(input_file)

    else:
        with open(output_file2, 'w') as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_number', type=int)
    args = parser.parse_args()

    trans_rfc(args.rfc_number)


# 連続してアクセスすると、以下のメッセージが表示されてIPアドレス単位でブロックされるので注意。
#
#
#   お使いのコンピュータ ネットワークから通常と異なるトラフィックが検出されました。
#   後でもう一度リクエストを送信してみてください。このページが表示された理由
#
#   このページは、お使いのコンピュータ ネットワークから利用規約に違反すると考えられる
#   リクエストが自動検出されたときに表示されます。
#   ブロックは、これらのリクエストが停止されると間もなく解除されます。
#
#   このトラフィックは、リクエストを自動送信する不正なソフトウェア、ブラウザ プラグイン、
#   またはスクリプトによって発生した可能性があります。ネットワーク接続が共有のものである場合は、
#   同じ IP アドレスを使用している別のコンピュータが発生元の可能性がありますので、
#   管理者に相談してください。詳しくはこちらをご覧ください。
#
#   ロボットが使用するような高度な検索語を使用したり、リクエストを非常にすばやく送信した場合も、
#   このページが表示されることがあります。
#
#   IP アドレス: XX.XX.XX.XX
#   時間: 2019-10-16T03:56:15Z
#   URL: https://translate.google.com/translate_a/single?...
#
#

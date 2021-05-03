
import sys
import re
import json
import codecs
from datetime import datetime, timedelta, timezone
JST = timezone(timedelta(hours=+9), 'JST')
import textwrap
from bs4 import BeautifulSoup
from pprint import pprint

def make_json_from_html(rfc_number):

    # RFCデータ(HTML)の読み込み
    input_file = 'html/rfc%d.html' % rfc_number
    with open(input_file, 'r', encoding="utf-8", newline="\n") as f:
        html_text = f.read()

    # 保存用JSONの構造
    data = {
        "title": {"text": "", "ja": ""},
        "number": 0,
        "created_at": str(datetime.now(JST)),
        "updated_by": "",
        "contents": []
    }

    soup = BeautifulSoup(html_text, "html.parser")
    # print(html_text)

    # 英語タイトル
    data['title']['text'] = soup.find('title').text.replace(" 日本語訳", "")
    # 日本語タイトル
    data['title']['ja'] = soup.find(class_="title_ja").find("strong").text

    # RFC番号
    m = re.match(r'RFC ?(\d+)', data['title']['text'])
    if m:
        data['number'] = int(m[1])

    # 更新者
    data['updated_by'] = soup.find(class_="updated_by").text.replace("翻訳編集 : ", "")

    # 各段落
    for row in soup.find_all(class_='row'):
        # 各段落情報の新規作成
        row_data = {}

        # 要素数チェック
        texts = list(row.find_all(class_='text'))
        if len(texts) <= 0:
            continue

        # タグ名（pre:図表, h5:見出し, p:文章）
        tag_name = texts[0].name

        # インデント
        row_data['indent'] = 0
        if tag_name == 'p':
            indent = 0
            for class_ in texts[0].attrs.get('class'):
                if class_.startswith('indent-'):
                    row_data['indent'] = int(class_.replace('indent-', ''))
                    break

        # 英文
        row_data['text'] = texts[0].text.strip()

        # タグ名が図表のとき
        if texts[0].name == 'pre':
            # 翻訳なしフラグ
            row_data['raw'] = True
            # インデント
            indent_data = texts[0].text.strip("\n")
            dedent_data = textwrap.dedent(indent_data)
            diff = len(indent_data.split("\n")[0]) - len(dedent_data.split("\n")[0])
            row_data['indent'] = diff
            row_data['text'] = dedent_data.strip('\n')
            # 目次フラグ
            if 'toc' in texts[0].attrs.get('class'):
                row_data['toc'] = True
            # 翻訳文
            row_data['ja'] = ""

        # タグ名が見出しのとき
        if texts[0].name == 'h5':
            # 見出しフラグ
            row_data['section_title'] = True

        # 翻訳文
        if len(texts) >= 2:
            row_data['ja'] = texts[1].text.strip()

        # 各段落情報の追加
        data['contents'].append(row_data)

    # pprint(data)

    # RFCデータ(JSON)の書き込み
    output_file = 'data/%d/rfc%d-trans.json' % (rfc_number // 1000 % 10 * 1000, rfc_number)
    with open(output_file, 'w', encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    rfc_number = int(sys.argv[1])
    make_json_from_html(rfc_number)

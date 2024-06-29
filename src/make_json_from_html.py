# ------------------------------------------------------------------------------
# PullReqで修正されたHTMLをJSONに反映するためのプログラム
# ------------------------------------------------------------------------------

import sys
import textwrap
from pprint import pprint
from bs4 import BeautifulSoup
from .rfc_const import RfcFile
from .rfc_utils import RfcUtils
from .domain.models.rfc import IRfc, Rfc

def make_json_from_html(rfc: IRfc) -> None:
    """HTMLからJSONへ変換する"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc, Rfc)  # Draft版以外のみ対応

    # RFCデータ(HTML)の読み込み
    input_file = RfcFile.get_filepath_html_rfc(rfc)
    html_text = RfcFile.read_html_file(input_file)

    # 保存用JSONの構造
    data = {
        "title": {"text": "", "ja": ""},
        "number": 0,
        "created_at": str(RfcUtils.get_now()),
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
    data['number'] = RfcUtils.get_rfc_number_int(data['title']['text'])
    print(f"[*] RFC: {data['number']}")

    # 更新者
    data['updated_by'] = soup.find(class_="updated_by").text.replace("翻訳編集 : ", "")
    print(f"[*] 更新者: {data['updated_by']}")

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

        # 文章のとき、indent-N というクラス名から、インデントレベル N を取得する
        if tag_name == 'p':
            for class_ in texts[0].attrs.get('class'):
                if class_.startswith('indent-'):
                    row_data['indent'] = int(class_.replace('indent-', ''))
                    break

        # 英文 (en)
        row_data['text'] = texts[0].text.strip()

        # 図表のとき、各要素を HTML から取得する
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

        # 見出しのとき、見出しフラグをTrueにする
        if texts[0].name == 'h5':
            row_data['section_title'] = True

        # 翻訳文 (ja)
        if len(texts) >= 2:
            row_data['ja'] = texts[1].text.strip()

        # HTMLに翻訳文が無い（消えてしまった）場合は、空文字を追加する
        if not ('ja' in row_data):
            row_data['ja'] = ""

        # 各段落情報の追加
        data['contents'].append(row_data)

    # pprint(data)

    # RFCデータ(JSON)の書き込み
    output_file = RfcFile.get_filepath_data_trans_json(rfc.get_id())
    RfcFile.write_json_file(output_file, data)


if __name__ == '__main__':
    rfc_number = int(sys.argv[1])
    make_json_from_html(rfc_number)

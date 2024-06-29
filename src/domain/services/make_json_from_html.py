# ------------------------------------------------------------------------------
# PullReqで修正されたHTMLをJSONに反映するためのプログラム
# ------------------------------------------------------------------------------

import sys
import textwrap
from pprint import pprint
from bs4 import BeautifulSoup
from ..models.rfc import RfcFile, IRfc, Rfc, RfcJsonElem
from ..repository.irfcjsontransrepository import IRfcJsonTransRepository
from ..repository.irfchtmlrepository import IRfcHtmlRepository
from .rfc_utils import RfcUtils

def make_json_from_html(rfc: IRfc,
                        rfc_html_repo: IRfcHtmlRepository,
                        rfc_json_trans_repo: IRfcJsonTransRepository) -> None:
    """HTMLからJSONへ変換する"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc, Rfc)  # Draft版以外のみ対応
    assert isinstance(rfc_html_repo, IRfcHtmlRepository)
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)

    # RFCデータ(HTML)の読み込み
    html_text = rfc_html_repo.find(rfc)

    # 保存用JSONの構造
    data = {
        RfcJsonElem.TITLE: { RfcJsonElem.Title.TEXT: "", RfcJsonElem.Title.JA: "" },
        RfcJsonElem.NUMBER: 0,
        RfcJsonElem.CREATED_AT: str(RfcUtils.get_now()),
        RfcJsonElem.UPDATED_BY: "",
        RfcJsonElem.CONTENTS: []
    }

    soup = BeautifulSoup(html_text, "html.parser")
    # print(html_text)

    # 英語タイトル
    data[RfcJsonElem.TITLE][RfcJsonElem.Title.TEXT] = soup.find('title').text.replace(" 日本語訳", "")
    # 日本語タイトル
    data[RfcJsonElem.TITLE][RfcJsonElem.Title.JA] = soup.find(class_="title_ja").find("strong").text

    # RFC番号
    data[RfcJsonElem.NUMBER] = RfcUtils.get_rfc_number_int(data[RfcJsonElem.TITLE][RfcJsonElem.Title.TEXT])
    print(f"[*] RFC: {data[RfcJsonElem.NUMBER]}")

    # 更新者
    data[RfcJsonElem.UPDATED_BY] = soup.find(class_="updated_by").text.replace("翻訳編集 : ", "")
    print(f"[*] 更新者: {data[RfcJsonElem.UPDATED_BY]}")

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
        row_data[RfcJsonElem.Contents.INDENT] = 0

        # 文章のとき、indent-N というクラス名から、インデントレベル N を取得する
        if tag_name == 'p':
            for class_ in texts[0].attrs.get('class'):
                if class_.startswith('indent-'):
                    row_data[RfcJsonElem.Contents.INDENT] = int(class_.replace('indent-', ''))
                    break

        # 英文 (en)
        row_data[RfcJsonElem.Contents.TEXT] = texts[0].text.strip()

        # 図表のとき、各要素を HTML から取得する
        if texts[0].name == 'pre':
            # 翻訳なしフラグ
            row_data[RfcJsonElem.Contents.RAW] = True
            # インデント
            indent_data = texts[0].text.strip("\n")
            dedent_data = textwrap.dedent(indent_data)
            diff = len(indent_data.split("\n")[0]) - len(dedent_data.split("\n")[0])
            row_data[RfcJsonElem.Contents.INDENT] = diff
            row_data[RfcJsonElem.Contents.TEXT] = dedent_data.strip('\n')
            # 目次フラグ
            if 'toc' in texts[0].attrs.get('class'):
                row_data[RfcJsonElem.Contents.TOC] = True
            # 翻訳文
            row_data[RfcJsonElem.Contents.JA] = ""

        # 見出しのとき、見出しフラグをTrueにする
        if texts[0].name == 'h5':
            row_data[RfcJsonElem.Contents.SECTION_TITLE] = True

        # 翻訳文 (ja)
        if len(texts) >= 2:
            row_data[RfcJsonElem.Contents.JA] = texts[1].text.strip()

        # HTMLに翻訳文が無い（消えてしまった）場合は、空文字を追加する
        if not (RfcJsonElem.Contents.JA in row_data):
            row_data[RfcJsonElem.Contents.JA] = ""

        # 各段落情報の追加
        data[RfcJsonElem.CONTENTS].append(row_data)

    # pprint(data)

    # RFCデータ(JSON)の書き込み
    rfc_json_trans_repo.save(rfc, data)


if __name__ == '__main__':
    rfc_number = Rfc(sys.argv[1])
    make_json_from_html(rfc_number)

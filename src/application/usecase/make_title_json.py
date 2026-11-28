# ------------------------------------------------------------------------------
# 全RFCの日本語タイトル一覧のJSONを作成するプログラム
# ------------------------------------------------------------------------------

import os
from ...domain.services.rfcfile import RfcFile
from ...infrastructure.repository.rfcjsontransrepository import IRfcJsonTransRepository
from ...infrastructure.repository.rfctitlejsonrepository import IRfcTitleRepository


def make_title_json(rfc_title_repo: IRfcTitleRepository,
                    rfc_json_trans_repo: IRfcJsonTransRepository) -> None:
    """翻訳済みJSONから全RFCの日本語タイトル一覧を作成する

    RFCの変遷グラフや、本文中のRFCへのリンクの概要表示で、リンク先RFCのタイトルを表示するために使用する。
    翻訳対象外（RFC 2220 未満）のRFCは、タイトルだけを訳したJSONから補う。
    """

    assert isinstance(rfc_title_repo, IRfcTitleRepository)
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)

    print(f'[*] make_title_json()')

    titles = rfc_json_trans_repo.findall_titles_ja()

    # 本文を翻訳していないRFCのタイトル（翻訳済みのタイトルがあればそちらを優先する）
    if os.path.exists(RfcFile.UNTRANSLATED_RFC_TITLE_JSON_FILE):
        untranslated = RfcFile.read_json_file(RfcFile.UNTRANSLATED_RFC_TITLE_JSON_FILE)
        for number, title in untranslated.items():
            titles.setdefault(number, title['ja'])

    # RFC番号順（昇順）に並べる（5桁以上のRFCのために数値でソートする）
    obj = {number: titles[number] for number in sorted(titles, key=int)}

    print(f'[+] make_title_json: {len(obj)} titles')

    # Save file
    rfc_title_repo.save(obj)

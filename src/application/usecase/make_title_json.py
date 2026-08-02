# ------------------------------------------------------------------------------
# 全RFCの日本語タイトル一覧のJSONを作成するプログラム
# ------------------------------------------------------------------------------

from ...infrastructure.repository.rfcjsontransrepository import IRfcJsonTransRepository
from ...infrastructure.repository.rfctitlejsonrepository import IRfcTitleRepository


def make_title_json(rfc_title_repo: IRfcTitleRepository,
                    rfc_json_trans_repo: IRfcJsonTransRepository) -> None:
    """翻訳済みJSONから全RFCの日本語タイトル一覧を作成する

    RFCの変遷グラフで、リンク先RFCのタイトルを表示するために使用する。
    """

    assert isinstance(rfc_title_repo, IRfcTitleRepository)
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)

    print(f'[*] make_title_json()')

    titles = rfc_json_trans_repo.findall_titles_ja()

    # RFC番号順（昇順）に並べる（5桁以上のRFCのために数値でソートする）
    obj = {number: titles[number] for number in sorted(titles, key=int)}

    print(f'[+] make_title_json: {len(obj)} titles')

    # Save file
    rfc_title_repo.save(obj)

# ------------------------------------------------------------------------------
# IETFのWebサイトからRFCをTXT形式で取得し、文章・図・表・コードの判定をするためのプログラム
# ------------------------------------------------------------------------------

import re
import lxml.html
from pprint import pprint
from ..services.rfc_utils import RfcUtils
from ..models.rfc import RfcFile, RfcJsonElem, IRfc, Rfc, RfcDraft, RFCNotFoundException
from ..models.rfc.contents.paragraph import BREAK
from ..models.rfc.contents.paragraphs import Paragraphs
from ..repository.irfcjsondatarepository import IRfcJsonDataRepository


def fetch_rfc_txt(rfc: IRfc,
                  rfc_json_plain_repo: IRfcJsonDataRepository,
                  args) -> None:
    """RFCの取得処理 (TXT版)"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_plain_repo, IRfcJsonDataRepository)

    print(f"[*] fetch_rfc_txt({rfc.get_id()})")

    # すでに出力ファイルが存在する場合は終了 (--forceオプションが有効なとき以外)
    if not args.force and rfc_json_plain_repo.find(rfc):
        return

    # RFCページのDOMツリーの取得
    url = RfcFile.get_url_rfc_html(rfc)
    page = RfcUtils.fetch_url(url)
    tree = lxml.html.fromstring(RfcUtils.html_rm_link_tag(page.content))

    # タイトル取得
    title = tree.xpath('//title/text()')
    if len(title) == 0:
        raise RFCNotFoundException
    title = title[0].strip()

    # タイトルの取得（パターンマッチ）
    if re.match(r'RFC [^ ]+ - .*$', title):  # RFC
        tmp = title
        tmp = re.sub(r' ?\(RFC \d+\)$', '', tmp)
        tmp = re.sub(r' ?\(Internet-Draft, \d+\)$', '', tmp)
        tmp = re.sub(r'^RFC (\d+) -', f'RFC {rfc.get_id()} -', tmp)  # 廃止RFCの場合、最新RFCにリダイレクトされるため
        # title = "RFC %s - %s" % (number, tmp)
        title = tmp
    elif re.match(r'draft-[-a-zA-Z0-9]+\d$', title):  # Draft版
        title = title
    else:
        # タイトルがRFC形式と一致しない場合
        raise Exception("[-] Cannot extract RFC Title!: RFC=%s, title=%s" % (rfc.get_id(), title))

    # RFCページのTXT形式の取得
    url_txt = RfcFile.get_url_rfc_txt(rfc)
    page = RfcUtils.fetch_url(url_txt)
    text = page.content.decode('ascii', errors='ignore')

    # ページ区切りの削除＋前後段落の結合（例：RFC 3830）
    # （RFC8650以降はページ区切りが無くなりました）
    contents = text.split("\n\n")
    contents = [con for con in contents if len(con) > 0]
    contents_len = len(contents)
    for i, content in enumerate(contents):
        # pprint(content)

        # ページ区切りのとき
        if re.search(r'\x0c', content):  # ASCIIのETX(テキスト終了)が存在する場合はページ区切りと判断

            # -1: For efficiency reasons, one SHOULD also avoid a
            #  0: Arkko, et al.     Standards Track      [Page 65]
            #     RFC 3830             MIKEY           August 2004   ←ページ区切り
            # +1: security overkill, e.g., by not using a public key...

            contents[i + 0] = ''  # ページ区切りの除去
            if i + 1 >= contents_len:
                continue

            # ページをまたぐ文章に対応する処理
            first_index = 0
            last_index = -1
            prev_last_line = contents[i - 1].rstrip('\n').split('\n')[last_index]    # 前ページの最後の行
            next_first_line = contents[i + 1].lstrip('\n').split('\n')[first_index]  # 次ページの最初の行
            indent1 = RfcUtils.get_indent(prev_last_line)
            indent2 = RfcUtils.get_indent(next_first_line)
            # print('newpage:', i)
            # print('  ', indent1, prev_last_line)
            # print('  ', indent2, next_first_line)

            # 以下の条件のとき、段落がページをまたいでいると判断する
            #   1) 前ページの最後の段落の字下げの幅と、次ページの最初の段落の字下げの幅が同じとき
            #   2) 前ページの最後の段落が、文終端の「.」や「;」や「|」ではないとき
            if not prev_last_line.endswith('.') \
                    and not re.search(r'[;|]$', prev_last_line) \
                    and re.match(r'^ *[a-zA-Z0-9(]', next_first_line) \
                    and indent1 == indent2:
                # 内容がページをまたぐ場合、BREAKを挿入する
                # BREAK は文章のときは空白に置き換えて、コードのときは改行の置き換える。
                contents[i + 1] = contents[i - 1].rstrip('\n') + BREAK + contents[i + 1].lstrip('\n')
                contents[i - 1] = ''

    # 全ての段落を結合する（段落の区切りは\n\n）
    text = '\n\n'.join(contents).strip()

    # 文字列を段落の配列に変換する
    paragraphs = Paragraphs(text)

    # 段落情報をJSONに変換する
    obj = {}
    obj[RfcJsonElem.TITLE] = { RfcJsonElem.Title.TEXT: title }
    obj[RfcJsonElem.NUMBER] = rfc.get_id()
    obj[RfcJsonElem.CREATED_AT] = str(RfcUtils.get_now())
    obj[RfcJsonElem.UPDATED_BY] = ''
    obj[RfcJsonElem.CONTENTS] = []
    if isinstance(rfc, Rfc):
        obj[RfcJsonElem.NUMBER] = int(obj[RfcJsonElem.NUMBER])
    if isinstance(rfc, RfcDraft):
        obj[RfcJsonElem.IS_DRAFT] = True

    for paragraph in paragraphs:
        obj[RfcJsonElem.CONTENTS].append({
            RfcJsonElem.Contents.INDENT: paragraph.indent,
            RfcJsonElem.Contents.TEXT: paragraph.text,
        })
        if paragraph.is_section_title:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.SECTION_TITLE] = True
        if paragraph.is_code:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.RAW] = True
        if paragraph.is_toc:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.TOC] = True

    # JSONの保存
    rfc_json_plain_repo.save(rfc, obj)

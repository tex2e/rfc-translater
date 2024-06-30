# ------------------------------------------------------------------------------
# IETFのWebサイトからRFCをXML形式で取得し、文章・図・表・コードの判定をするためのプログラム
# ------------------------------------------------------------------------------

import re
import textwrap
from pprint import pprint
import lxml.etree  # pip install lxml
from ...domain.services.rfcutils import RfcUtils
from ...domain.valueobject.rfc import RfcJsonElem, RfcXmlElem, IRfc, Rfc, RfcDraft, RFCNotFoundException
from ...infrastructure.repository.rfcjsondatarepository import IRfcJsonDataRepository
from ...infrastructure.apiclient.rfcapiclient import IRfcApiClient
from ...application.service.custom_xml2rfc import generate_text_writer


def fetch_rfc_xml(rfc: IRfc,
                  rfc_json_plain_repo: IRfcJsonDataRepository,
                  rfc_api: IRfcApiClient,
                  args) -> None:
    """RFCの取得処理 (XML版)"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_plain_repo, IRfcJsonDataRepository)
    assert isinstance(rfc_api, IRfcApiClient)

    print(f"[*] fetch_rfc_xml({rfc.get_id()})")
    force = args.force

    # すでに出力ファイルが存在する場合は終了 (--forceオプションが有効なとき以外)
    if not force and rfc_json_plain_repo.find(rfc):
        return

    # RFC (XML) の取得
    page = rfc_api.fetch_xml(rfc)
    xml: bytes = page.content

    # RFCタイトル取得
    root = lxml.etree.fromstring(xml)
    titles = root.xpath(f'/{RfcXmlElem.RFC}/{RfcXmlElem.FRONT}/{RfcXmlElem.TITLE}/text()')
    if len(titles) > 0:
        title = f"RFC {rfc.get_id()} - {titles[0]}"
    else:
        raise Exception("[-] Cannot extract RFC Title!: RFC=%s" % (rfc.get_id()))

    # XML解析
    text_writer = generate_text_writer(xml)
    text_writer.process()

    # デバッグ
    debug = args.debug
    if debug:
        _debug(text_writer._contents)

    # 段落情報をJSONに変換する
    obj = {}
    obj[RfcJsonElem.TITLE] = { RfcJsonElem.Title.TEXT: title }
    obj[RfcJsonElem.NUMBER] = rfc.get_id()
    obj[RfcJsonElem.CREATED_AT] = str(RfcUtils.get_now())
    obj[RfcJsonElem.UPDATED_BY] = ''
    obj[RfcJsonElem.CONTENTS] = []
    # 通常のRFCのとき、RFC番号は整数型に変換する
    if isinstance(rfc, Rfc):
        obj[RfcJsonElem.NUMBER] = int(obj[RfcJsonElem.NUMBER])
    # Draft版RFCのとき、DraftフラグをONにする
    if isinstance(rfc, RfcDraft):
        obj[RfcJsonElem.IS_DRAFT] = True

    for content in text_writer._contents:
        if re.match(r'^\s*$', content.text):
            continue

        obj[RfcJsonElem.CONTENTS].append({
            RfcJsonElem.Contents.INDENT: content.indent,
            RfcJsonElem.Contents.TEXT: content.text,
        })
        if content.title:
            # obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.TITLE] = True
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.INDENT] = 0
        if content.section_title:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.SECTION_TITLE] = True
        if content.raw:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.RAW] = True
        if content.toc:
            obj[RfcJsonElem.CONTENTS][-1][RfcJsonElem.Contents.TOC] = True

    # JSONの保存
    rfc_json_plain_repo.save(rfc, obj)


def _debug(contents):
    for content in contents:
        print(f'[*] indent={content.indent}, section_title={content.section_title}, toc={content.toc}, raw={content.raw}, tag={content.tag}')
        if content.section_title:
            print('')
            print(f'### {content.text}')
            print('')
        else:
            content_text = textwrap.dedent(content.text)
            content_text = re.sub(re.compile(r'^\n', re.MULTILINE), '', content_text)
            content_text = re.sub(re.compile(r'\n$', re.MULTILINE), '', content_text)
            if not content.raw:
                content_text = content_text.lstrip()
            print(textwrap.indent(content_text, prefix=(" " * content.indent)))
            print('')

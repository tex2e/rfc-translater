# ------------------------------------------------------------------------------
# IETFのWebサイトからRFCステータスとWGの一覧を取得するプログラム
# ------------------------------------------------------------------------------

import re
from pprint import pprint
from lxml import etree  # pip install lxml
from ...domain.services.rfcutils import RfcUtils
from ...domain.valueobject.rfc import RfcIndexXmlElem, RfcIndexJsonElem
from ...infrastructure.repository.rfcstatusjsonrepository import IRfcStatusRepository
from ...infrastructure.apiclient.rfcindexapiclient import IRfcIndexApiClient


# RFC Index内の月名（英語）から月番号への変換表
MONTH_NAME_TO_NUMBER = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4,
    'May': 5, 'June': 6, 'July': 7, 'August': 8,
    'September': 9, 'October': 10, 'November': 11, 'December': 12,
}


def fetch_status(rfc_status_repo: IRfcStatusRepository,
                 rfc_api: IRfcIndexApiClient) -> None:
    """RFC IndexのXML版を取得してRFCリストを作成する"""

    assert isinstance(rfc_status_repo, IRfcStatusRepository)
    assert isinstance(rfc_api, IRfcIndexApiClient)

    print(f'[*] fetch_status()')

    page = rfc_api.fetch_index_xml()
    page_content = RfcUtils.remove_namespace_from_xml(page.content)
    tree = etree.XML(page_content)

    obj = {}

    for item in tree.xpath(f'/{RfcIndexXmlElem.RFC_INDEX}/{RfcIndexXmlElem.RFC_ENTRY}'):
        subtree = etree.XML(etree.tostring(item))

        rfc_ids = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_ids) == 0:
            continue
        rfc_id = rfc_ids[0]

        m = re.match(r'^RFC([0-9]+)$', rfc_id)
        if not m:
            continue
        rfc_number_str = m.group(1)

        obj[rfc_number_str] = {}

        # obsoletes
        rfc_obsoletes = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.OBSOLETES}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_obsoletes) > 0:
            rfc_obsoletes = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_obsoletes]
            obj[rfc_number_str][RfcIndexJsonElem.OBSOLETES] = rfc_obsoletes

        # obsoleted-by
        rfc_obsoleted_by = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.OBSOLETED_BY}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_obsoleted_by) > 0:
            rfc_obsoleted_by = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_obsoleted_by]
            obj[rfc_number_str][RfcIndexJsonElem.OBSOLETED_BY] = rfc_obsoleted_by

        # updates
        rfc_updates = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.UPDATES}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_updates) > 0:
            rfc_updates = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_updates]
            obj[rfc_number_str][RfcIndexJsonElem.UPDATES] = rfc_updates

        # updated-by
        rfc_updated_by = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.UPDATED_BY}/{RfcIndexXmlElem.DOC_ID}/text()')
        if len(rfc_updated_by) > 0:
            rfc_updated_by = [RfcUtils.replace_rfcXXXX_to_XXXX(x) for x in rfc_updated_by]
            obj[rfc_number_str][RfcIndexJsonElem.UPDATED_BY] = rfc_updated_by

        # current-status
        rfc_current_status = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.CURRENT_STATUS}/text()')
        if len(rfc_current_status) > 0:
            rfc_current_status = RfcUtils.replace_upper_to_camel(rfc_current_status[0])
            obj[rfc_number_str][RfcIndexJsonElem.CURRENT_STATUS] = rfc_current_status

        # wg (working-group)
        rfc_wgs = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.WG_ACRONYM}/text()')
        if len(rfc_wgs) > 0:
            rfc_wg = rfc_wgs[0]
            if re.match(r'^[^ ]+$', rfc_wg):
                obj[rfc_number_str][RfcIndexJsonElem.WG] = str(rfc_wg)

        # date (発行年月)
        rfc_years = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.DATE}/{RfcIndexXmlElem.YEAR}/text()')
        if len(rfc_years) > 0:
            rfc_months = subtree.xpath(f'/{RfcIndexXmlElem.RFC_ENTRY}/{RfcIndexXmlElem.DATE}/{RfcIndexXmlElem.MONTH}/text()')
            # 月が不明なRFCも存在するため、その場合は1月として扱う
            rfc_month = MONTH_NAME_TO_NUMBER.get(rfc_months[0].strip(), 1) if len(rfc_months) > 0 else 1
            obj[rfc_number_str][RfcIndexJsonElem.DATE] = '%s-%02d' % (rfc_years[0].strip(), rfc_month)

    # Save file
    rfc_status_repo.save(obj)

    # errata (却下されたものを除く)。頻繁に変わるため、更新状況とは別のファイルに保存する
    rfc_status_repo.save_errata(make_errata(obj, rfc_api.fetch_errata_json()))


# Errataの状態・種類（JSONでは頭文字だけを保存する）
ERRATA_STATUS_CODES = {'Verified': 'V', 'Held for Document Update': 'H', 'Reported': 'R'}
ERRATA_TYPE_CODES = {'Technical': 'T', 'Editorial': 'E'}
# 一覧に表示する「対象の節」の最大文字数（自由記述のため長い文が入っていることがある）
ERRATA_SECTION_LABEL_MAX = 40


def make_errata(obj: dict, errata_list: list) -> dict:
    """RFC EditorのErrata一覧を、RFC番号ごとの [[ID, 状態, 種類, 対象の節, [節番号...]], ...] にまとめる"""
    errata_by_rfc = {}
    for errata in errata_list:
        m = re.match(r'^RFC0*([0-9]+)$', errata.get('doc-id') or '')
        status = ERRATA_STATUS_CODES.get(errata.get('errata_status_code'))
        if not m or not status or m.group(1) not in obj:
            continue  # 却下(Rejected)されたものとRFC以外の文書は含めない
        label = ' '.join((errata.get('section') or '').split())
        if len(label) > ERRATA_SECTION_LABEL_MAX:
            label = label[:ERRATA_SECTION_LABEL_MAX - 1] + '…'
        errata_by_rfc.setdefault(m.group(1), []).append([
            int(errata['errata_id']),
            status,
            ERRATA_TYPE_CODES.get(errata.get('errata_type_code'), ''),
            label,
            parse_errata_sections(errata.get('section') or ''),
        ])
    for entries in errata_by_rfc.values():
        entries.sort(key=lambda e: e[0])
    return dict(sorted(errata_by_rfc.items(), key=lambda kv: int(kv[0])))


def parse_errata_sections(text: str) -> list:
    """Errataの「対象の節」（自由記述）から節番号を取り出す。
    例: "4.2.10." → ["4.2.10"], "4.3.2, B.3.2" → ["4.3.2", "B.3.2"], "2.8 & Appx E" → ["2.8", "E"],
        "12, pg.18" → ["12"], "Appendix D.6" → ["D.6"], "GLOBAL" → []"""
    # ページ番号（"pg. 4", "page 2"）は節番号ではない
    text = re.sub(r'\b(?:pg|pp|page)s?\.?\s*\d+(?:\s*-\s*\d+)?', ' ', text, flags=re.IGNORECASE)
    sections = []
    for part in re.split(r'\s*(?:,|&|;|\+|/|\band\b)\s*', text):
        part = part.strip()
        appendix = re.match(r'^(?:Appendix|Appx|App)\.?\s+', part, flags=re.IGNORECASE)
        if appendix:
            part = part[appendix.end():]
        part = re.sub(r'^(?:Sections?|Sec)\.?\s*|^§\s*', '', part, flags=re.IGNORECASE)
        m = re.match(r'^(\d+(?:\.\d+)*|[A-Z](?:\.\d+)*)\.?(?=$|\s|\(|:)', part)
        if not m:
            # 文中の "In Section 25.1:" "see Appendix B" のような書き方
            m = re.search(r'\b(?:Sections?|Appendix)\s+(\d+(?:\.\d+)*|[A-Z](?:\.\d+)*)\b', part, flags=re.IGNORECASE)
            if not m or not re.match(r'^(?:\d|[A-Z])', m.group(1)):
                continue
            appendix = appendix or re.match(r'[A-Z]', m.group(1))
        number = m.group(1)
        # 英字1文字だけの節（付録）は、"Appendix" が付いているか、その文字だけが書かれている場合に限る
        # （"A grouping ..." のような文の書き出しを付録Aと誤らないため）
        if re.fullmatch(r'[A-Z]', number) and not appendix and part.rstrip('.') != number:
            continue
        if number not in sections:
            sections.append(number)
    return sections

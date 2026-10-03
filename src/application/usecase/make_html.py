# ------------------------------------------------------------------------------
# 翻訳済みJSONからHTMLを生成するためのプログラム
# ------------------------------------------------------------------------------

from __future__ import annotations

import os
import re
import textwrap
import markupsafe
from pprint import pprint
from mako.lookup import TemplateLookup
from ...domain.valueobject.rfc import RfcJsonElem, IRfc, RfcDraft
from ...domain.services.rfcfile import RfcFile
from ...infrastructure.repository.rfcjsontransrepository import IRfcJsonTransRepository
from ...infrastructure.repository.rfcjsondatasummaryrepository import IRfcJsonDataSummaryRepository
from ...infrastructure.repository.rfchtmlrepository import IRfcHtmlRepository


def make_html(rfc: IRfc,
              rfc_json_trans_repo: IRfcJsonTransRepository,
              rfc_json_data_summary_repo: IRfcJsonDataSummaryRepository,
              rfc_json_html_repo: IRfcHtmlRepository) -> None:
    """RFCのHTMLを作成する"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)
    assert isinstance(rfc_json_data_summary_repo, IRfcJsonDataSummaryRepository)
    assert isinstance(rfc_json_html_repo, IRfcHtmlRepository)

    print(f'[*] make_html({rfc.get_id()})')

    input_file = rfc_json_trans_repo.findpath(rfc)
    if not input_file:
        print("[-] make_html: Not found:", input_file)
        return

    # 翻訳したRFC (json) の読み込み
    obj = rfc_json_trans_repo.find(rfc)
    if not obj:
        print("[-] make_html: Not found json:", input_file)
        return

    # 要約が存在すれば、その情報 (json) の読み込み
    summary = rfc_json_data_summary_repo.find(rfc)

    # テンプレートエンジン「Mako」を使って、値をバインドする
    mylookup = TemplateLookup(directories=["./"], input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template(RfcFile.TEMPLATE_HTML_RFC)
    is_draft = isinstance(rfc, RfcDraft)
    contents = obj[RfcJsonElem.CONTENTS]
    output = mytemplate.render_unicode(ctx=obj, summary=summary, is_draft=is_draft,
                                       bcp14=RfcHtmlHelper.uses_bcp14(contents),
                                       orig_url=RfcHtmlHelper.get_orig_url(obj[RfcJsonElem.NUMBER], is_draft),
                                       paragraph_ids=RfcHtmlHelper.make_paragraph_ids(contents),
                                       rule_start=RfcHtmlHelper.rule_start_index(contents),
                                       toc_section_ids=RfcHtmlHelper.make_toc_section_ids(contents),
                                       RfcJsonElem=RfcJsonElem, RfcHtmlHelper=RfcHtmlHelper)

    # 翻訳したRFC (html) の作成
    rfc_json_html_repo.save(rfc, output)


class RfcHtmlHelper:
    """テンプレートエンジン側に関数を渡すための汎用クラス"""

    @staticmethod
    def my_replace_filter(text):
        """HTML文字列をエスケープする"""
        text = text.replace('\n\n', '\x06\x06')
        text = str(markupsafe.escape(text))
        text = text.replace('\x06\x06', '<br>')
        return text

    @staticmethod
    def escape(text: str) -> str:
        """HTML文字列をエスケープする（テンプレートの式の途中で使う）"""
        return str(markupsafe.escape(text))

    @staticmethod
    def render_text(text: str, is_draft: bool = False, bcp14: bool = False) -> str:
        """文章をHTMLに変換する（エスケープ、段落内改行、規範キーワードの強調、RFC参照のリンク化）"""
        html = RfcHtmlHelper.my_replace_filter(text)
        if bcp14:
            html = RfcHtmlHelper.highlight_keywords(html)
        html = RfcHtmlHelper.link_rfc_refs(html, is_draft)
        if RfcHtmlHelper.bullet_class(text):
            # 箇条書き記号を固定幅にして、折り返した行の先頭を記号の後ろの文字にそろえる
            html = f'<span class="bullet-mark">{html[0]}</span>{html[1:]}'
        return html

    # RFC 2119 / RFC 8174 (BCP 14) のキーワードと規範強度（長い語から順に照合する）
    BCP14_KEYWORDS = {
        'MUST NOT': 'mustnot', 'SHALL NOT': 'mustnot',
        'SHOULD NOT': 'shouldnot', 'NOT RECOMMENDED': 'shouldnot',
        'MUST': 'must', 'SHALL': 'must', 'REQUIRED': 'must',
        'SHOULD': 'should', 'RECOMMENDED': 'should',
        'MAY': 'may', 'OPTIONAL': 'may',
    }
    # 前後が英数字・下線・ハイフンの場合は識別子の一部（例: MUST_STAPLE）とみなして除外する
    BCP14_PATTERN = re.compile(
        r'(?<![A-Za-z0-9_-])(MUST\s+NOT|SHALL\s+NOT|SHOULD\s+NOT|NOT\s+RECOMMENDED'
        r'|MUST|SHALL|REQUIRED|SHOULD|RECOMMENDED|MAY|OPTIONAL)(?![A-Za-z0-9_-])')

    @staticmethod
    def uses_bcp14(contents: list) -> bool:
        """文書がRFC 2119 / RFC 8174 (BCP 14) を参照しているか。
        大文字のキーワードが規範的な意味を持つのは、BCP 14 を参照している文書だけである"""
        return any(re.search(r'RFC ?2119|RFC ?8174|BCP ?14\b', p[RfcJsonElem.Contents.TEXT])
                   for p in contents)

    @staticmethod
    def highlight_keywords(escaped_html: str) -> str:
        """エスケープ済みの文章中の規範キーワード（英文の MUST、訳文の (MUST) など）を規範強度ごとのクラスで囲む"""
        def _wrap(m: re.Match) -> str:
            level = RfcHtmlHelper.BCP14_KEYWORDS[re.sub(r'\s+', ' ', m[1])]
            return f'<span class="kw kw-{level}">{m[1]}</span>'
        return RfcHtmlHelper.BCP14_PATTERN.sub(_wrap, escaped_html)

    @staticmethod
    def link_rfc_refs(escaped_html: str, is_draft: bool = False) -> str:
        """エスケープ済みの文章中の "[RFC5280]" をRFCへのリンクにする。
        翻訳済みHTMLが存在するRFCは自サイト内へ、存在しないRFCはIETFのサイトへリンクする"""
        def _link(m: re.Match) -> str:
            number = int(m[1])
            if RfcHtmlHelper.exists_rfc_html(number):
                href = f'../rfc{number}.html' if is_draft else f'./rfc{number}.html'
            else:
                href = f'https://datatracker.ietf.org/doc/html/rfc{number}'
            return f'<a href="{href}">{m[0]}</a>'
        return re.sub(r'\[RFC([0-9]+)\]', _link, escaped_html)

    # 翻訳済みHTMLが存在するRFC番号の一覧（全RFCを生成するときに毎回globしないようにキャッシュする）
    _existing_rfc_html_numbers = None

    @staticmethod
    def exists_rfc_html(number: int) -> bool:
        """翻訳済みのHTMLが公開されているか（RFC 2220 未満は公開対象外）"""
        if number < 2220:
            return False
        if RfcHtmlHelper._existing_rfc_html_numbers is None:
            RfcHtmlHelper._existing_rfc_html_numbers = {
                int(m[1]) for name in os.listdir('html')
                if (m := re.fullmatch(r'rfc(\d+)\.html', name))
            }
        return number in RfcHtmlHelper._existing_rfc_html_numbers

    @staticmethod
    def section_number(text: str) -> str | None:
        """見出しの章節番号を取得する（"4.1.2.  Client Hello" → "4.1.2", "Appendix A.  X" → "A"）"""
        # 英大文字1字だけの番号は "A." のようにピリオドがあるときだけ付録番号とみなす（"A Framework" を除外）
        m = re.match(r'^(?:Appendix\s+([A-Z])\.?|(\d+(?:\.\d+)*)\.?|([A-Z](?:\.\d+)+)\.?|([A-Z])\.)(?=\s|$)', text)
        return next((g for g in m.groups() if g), None) if m else None

    @staticmethod
    def section_level(text: str) -> int:
        """見出しの階層（"4." → 1, "4.1.2." → 3, 番号なし → 1）。表示上は4階層までを区別する"""
        number = RfcHtmlHelper.section_number(text)
        if number is None:
            return 1
        return min(number.count('.') + 1, 4)

    # データ上は文章として扱われている、RFC冒頭の定型の見出し
    FRONT_HEADINGS = {
        'abstract', 'status of this memo', 'copyright notice', 'table of contents',
        'iesg note', 'full copyright statement', 'copyright and license notice',
    }

    @staticmethod
    def is_front_heading(paragraph: dict) -> bool:
        """冒頭の定型見出し（Abstract など）か。JSONの構造は変えずに表示だけ見出しにする"""
        return (paragraph.get(RfcJsonElem.Contents.INDENT, 0) == 0
                and paragraph[RfcJsonElem.Contents.TEXT].strip().lower() in RfcHtmlHelper.FRONT_HEADINGS)

    @staticmethod
    def rule_start_index(contents: list) -> int:
        """見出しの上に区切り線を付け始める段落の番号。
        タイトル（見出し扱いのものを含む）と Abstract の上には線を付けない。
        Abstract が最初の定型見出しでないときは、最初の見出しの上だけ線を付けない"""
        for i, p in enumerate(contents):
            if p.get(RfcJsonElem.Contents.RAW):
                continue
            text = p[RfcJsonElem.Contents.TEXT].strip()
            if text.lower() == 'abstract':
                return i + 1
            # 他の定型見出しや番号付きの章が先に来たら、冒頭の Abstract はない
            if RfcHtmlHelper.is_front_heading(p) or (
                    p.get(RfcJsonElem.Contents.SECTION_TITLE) and RfcHtmlHelper.section_number(text)):
                break
        for i, p in enumerate(contents):
            if not p.get(RfcJsonElem.Contents.RAW) and (
                    p.get(RfcJsonElem.Contents.SECTION_TITLE) or RfcHtmlHelper.is_front_heading(p)):
                return i + 1
        return 0

    @staticmethod
    def bullet_class(text: str) -> str:
        """箇条書き記号（- o * +）で始まる文章には、記号をぶら下げて表示するためのクラスを付ける"""
        return ' bullet' if re.match(r'^[-o*+•]\s', text) else ''

    @staticmethod
    def make_paragraph_ids(contents: list) -> list[str]:
        """各段落のid（見出しはidを持つため None）。
        段落番号は直前の見出しからの連番にし、他の章の編集でリンク先がずれにくいようにする"""
        ids = []
        used = set()
        section_id = 'top'
        count = 0
        for paragraph in contents:
            if paragraph.get(RfcJsonElem.Contents.SECTION_TITLE) == True:
                section_id = RfcHtmlHelper.text_to_id(paragraph[RfcJsonElem.Contents.TEXT]) or 'section'
                count = 0
                ids.append(None)
                continue
            count += 1
            pid = f'{section_id}-p{count}'
            while pid in used:
                pid += '_'
            used.add(pid)
            ids.append(pid)
        return ids

    @staticmethod
    def make_toc_section_ids(contents: list) -> dict[str, str]:
        """目次中の章節番号から見出しのidへの対応表（"6.1.6." → "6-1-6--Outputs"）"""
        section_ids = {}
        for paragraph in contents:
            if paragraph.get(RfcJsonElem.Contents.SECTION_TITLE) == True:
                section_id = RfcHtmlHelper.text_to_id(paragraph[RfcJsonElem.Contents.TEXT])
                key = re.sub(r'--+.+$', '-', section_id).replace('-', '.')
                key = re.sub(r'^(Appendix)\.', r'\1 ', key)
                section_ids.setdefault(key, section_id)
        return section_ids

    @staticmethod
    def render_toc(text: str, section_ids: dict[str, str], is_draft: bool = False) -> str:
        """目次（整形済みテキスト）をエスケープし、章節番号を本文の見出しへのリンクにする"""
        escaped = str(markupsafe.escape(text))
        def _link(m: re.Match) -> str:
            if m[1] in section_ids:
                return f'<a href="#{section_ids[m[1]]}">{m[1]}</a>'
            return m[1]
        escaped = re.sub(r'(?<= )((?:[A-Z]\.)?(?:\d+\.)+|Appendix [A-Z]\.)(?= )', _link, escaped)
        return RfcHtmlHelper.link_rfc_refs(escaped, is_draft)

    @staticmethod
    def get_orig_url(number: str | int, is_draft: bool) -> str:
        """原文のURL（RFC 8650以降はXML版が存在するためRFC Editorの新形式HTMLを使う）"""
        if is_draft:
            return f'https://datatracker.ietf.org/doc/html/{number}'
        if RfcHtmlHelper.is_rfc_greater_than_or_equal_to_8650(number):
            return f'https://www.rfc-editor.org/rfc/rfc{number}.html'
        return f'https://datatracker.ietf.org/doc/html/rfc{number}'

    @staticmethod
    def text_to_id(text: str) -> str:
        """セクションのタイトルのidを作成する"""
        tmp = text
        tmp = re.sub(r'[. ]', '-', tmp)
        tmp = re.sub(r'[^-a-zA-Z0-9]', '', tmp)
        return tmp

    @staticmethod
    def indent(text: str, prefix: str) -> str:
        """文字列（複数行可）にインデントを追加する"""
        return textwrap.indent(text, prefix)

    @staticmethod
    def get_updated_by(text: str) -> str:
        """更新者の作成"""
        if text == '':
            return "自動生成"
        return text

    @staticmethod
    def is_rfc_greater_than_or_equal_to_8650(text: str | int) -> bool:
        """RFCが8650より大きいか（XML版が存在するか）を判定する"""
        return isinstance(text, int) and text >= 8650

# ------------------------------------------------------------------------------
# RFCの文章を翻訳するプログラム
#
# 翻訳そのものはClaudeのサブエージェント（.claude/agents/rfc-translator.md）が行う。
# このプログラムは、その前後の決定的な処理（翻訳対象の抽出・訳文の検証と適用・確定）を担当する。
#   1. trans_prepare : 取得済みJSONから作業ファイル (rfcXXXX-midway.json) を作る
#   2. trans_export  : 未翻訳の段落をJSONで出力する
#   3. trans_import  : 訳文JSONを検証して作業ファイルに適用する
#   4. trans_finish  : 全段落の翻訳完了を確認して rfcXXXX-trans.json に確定する
# ------------------------------------------------------------------------------

import re
import sys
import json
import fcntl
import hashlib
import tempfile
import os
from contextlib import contextmanager
from ...domain.valueobject.rfc import RfcJsonElem, IRfc
from ...infrastructure.repository.rfcjsondatarepository import IRfcJsonDataRepository
from ...infrastructure.repository.rfcjsontransrepository import IRfcJsonTransRepository
from ...infrastructure.repository.rfcjsontransmidwayrepository import IRfcJsonTransMidwayRepository

# 箇条書きのパターン
# 「-」「o」「*」「+」「$」「A.」「A.1.」「a)」「1)」「(a)」「(1)」「[1]」「[a]」「a.」
BULLET_PATTERN = r'^([\-o\*\+\$] |(?:[A-Z]\.)?(?:\d{1,2}\.)+(?:\d{1,2})? |\(?[0-9a-z]\) |\[[0-9a-z]{1,2}\] |[a-z]\. )(.*)$'
# 数式の変数説明のパターン（翻訳しない）
VARIABLE_PATTERN = r'^([a-zA-Z]{1,3}:)$'
# 付録の見出しのパターン
APPENDIX_PATTERN = r'^Appendix ([A-Z])\. (.*)$'
# 訳文に混入してはならない不可視文字（ゼロ幅スペースなど）
INVISIBLE_CHARS_PATTERN = r'[​‌‍⁠﻿]'
# 未翻訳の判定に使うパターン
JAPANESE_CHARS_PATTERN = r'[ぁ-んァ-ヶ一-龠]'
REFERENCE_ENTRY_PATTERN = r'^\[[^\]]+\]\s'
UNTRANSLATED_MIN_WORDS = 5  # 小文字の英単語がこの数以上あれば文章とみなす
# 前後の文脈として出力する段落数
CONTEXT_SIZE = 2
# 1回の翻訳依頼（バッチ）に含める段落数と原文の文字数の上限
BATCH_MAX_ITEMS = 40
BATCH_MAX_CHARS = 12000


class TransError(Exception):
    """翻訳作業の手順や訳文に問題があるときの例外"""


def get_required_prefix(text: str) -> str:
    """訳文の先頭にそのまま残すべき文字列（箇条書きの記号など）を取得する"""
    if m := re.match(APPENDIX_PATTERN, text, re.DOTALL):
        return f'付録{m[1]}. '
    if m := re.match(BULLET_PATTERN, text, re.DOTALL):
        return m[1]
    return ''


def validate_ja(content: dict, ja: object) -> str | None:
    """訳文が段落の形式上の要件を満たしているか検証する。問題があればその内容を返す"""
    if not isinstance(ja, str) or not ja.strip():
        return '訳文が空です'
    if content.get(RfcJsonElem.Contents.RAW) is True:
        return 'raw（図表・プログラム）の段落は翻訳できません'
    if re.search(INVISIBLE_CHARS_PATTERN, ja):
        return '訳文にゼロ幅スペースなどの不可視文字が含まれています'
    if ja != ja.strip():
        return '訳文の前後に空白があります'
    text = content[RfcJsonElem.Contents.TEXT]
    prefix = get_required_prefix(text)
    if prefix and not ja.startswith(prefix):
        return f'訳文は {prefix!r} から始めてください（記号や番号は原文のまま残す）'
    # 文章なのに日本語が1文字もない訳文は未翻訳とみなす
    # （参考文献のエントリや、名称・識別子だけの段落は原文のまま残すため対象外）
    if not re.search(JAPANESE_CHARS_PATTERN, ja) and len([w for w in text.split() if re.match(r'^[a-z]{3,}[,.;:]?$', w)]) >= UNTRANSLATED_MIN_WORDS \
            and not re.match(REFERENCE_ENTRY_PATTERN, text):
        return '訳文に日本語が含まれていません（未翻訳）'
    return None


def is_translated(content: dict) -> bool:
    """段落が翻訳済みか（rawの段落は翻訳不要のため翻訳済みとして扱う）"""
    if content.get(RfcJsonElem.Contents.RAW) is True:
        return RfcJsonElem.Contents.JA in content
    return bool(content.get(RfcJsonElem.Contents.JA))


def is_title_translated(obj: dict) -> bool:
    return bool(obj[RfcJsonElem.TITLE].get(RfcJsonElem.Title.JA))


@contextmanager
def _locked(filepath: str):
    """複数のサブエージェントが同時に訳文を適用しても壊れないように排他する"""
    # ロックファイルはレポジトリ内に残さないように一時ディレクトリに置く
    key = hashlib.sha1(os.path.abspath(filepath).encode()).hexdigest()
    with open(os.path.join(tempfile.gettempdir(), f'rfc-trans-{key}.lock'), 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _find_working_repo(rfc: IRfc,
                       rfc_json_trans_repo: IRfcJsonTransRepository,
                       rfc_json_trans_midway_repo: IRfcJsonTransMidwayRepository):
    """作業対象のファイルを管理するレポジトリを取得する。
    翻訳作業中は作業ファイル、確定後は翻訳結果ファイル（訳文の修正用）を対象とする"""
    if rfc_json_trans_midway_repo.find(rfc):
        return rfc_json_trans_midway_repo
    if rfc_json_trans_repo.find(rfc):
        return rfc_json_trans_repo
    raise TransError(f'RFC {rfc.get_id()} の作業ファイルがありません。先に --trans-prepare を実行してください')


def trans_prepare(rfc: IRfc,
                  rfc_json_data_repo: IRfcJsonDataRepository,
                  rfc_json_trans_midway_repo: IRfcJsonTransMidwayRepository) -> dict:
    """取得済みのRFCから翻訳の作業ファイルを作成する"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_data_repo, IRfcJsonDataRepository)
    assert isinstance(rfc_json_trans_midway_repo, IRfcJsonTransMidwayRepository)

    print(f"[*] trans_prepare({rfc.get_id()})")

    # 途中まで翻訳済みのファイルがあれば再利用する
    if obj := rfc_json_trans_midway_repo.find(rfc):
        print(f'[+] found midway file: {rfc_json_trans_midway_repo.findpath(rfc)}')
    else:
        obj = rfc_json_data_repo.find(rfc)
        if not obj:
            raise TransError(f'RFC {rfc.get_id()} が未取得です。先に --fetch を実行してください')

    # タイトルが「RFC XXXX」のみで翻訳する部分がないとき
    title = obj[RfcJsonElem.TITLE]
    if not title.get(RfcJsonElem.Title.JA) and ' - ' not in title[RfcJsonElem.Title.TEXT]:
        title[RfcJsonElem.Title.JA] = "RFC %s" % rfc.get_id()

    for content in obj[RfcJsonElem.CONTENTS]:
        if RfcJsonElem.Contents.JA in content:
            continue
        text = content[RfcJsonElem.Contents.TEXT]
        if content.get(RfcJsonElem.Contents.RAW) is True:
            # 図表は翻訳しない
            content[RfcJsonElem.Contents.JA] = ''
        elif re.match(VARIABLE_PATTERN, text):
            # 数式の変数説明は翻訳しない（原文をそのまま格納）
            content[RfcJsonElem.Contents.JA] = text

    rfc_json_trans_midway_repo.save(rfc, obj)
    print(f"[+] Save file: {rfc_json_trans_midway_repo.findpath(rfc)}")
    return trans_status(rfc, rfc_json_trans_midway_repo)


def trans_status(rfc: IRfc,
                 rfc_json_repo) -> dict:
    """翻訳の進捗を取得する"""
    obj = rfc_json_repo.find(rfc)
    contents = obj[RfcJsonElem.CONTENTS]
    remaining = [i for i, content in enumerate(contents) if not is_translated(content)]
    # 未翻訳の段落を、翻訳を依頼する単位（段落番号の範囲）に分割する
    batches = []
    for i in remaining:
        chars = len(contents[i][RfcJsonElem.Contents.TEXT])
        batch = batches[-1] if batches else None
        if batch and batch['items'] < BATCH_MAX_ITEMS and batch['chars'] + chars <= BATCH_MAX_CHARS:
            batch['limit'] = i - batch['offset'] + 1
            batch['items'] += 1
            batch['chars'] += chars
        else:
            batches.append({'offset': i, 'limit': 1, 'items': 1, 'chars': chars})
    status = {
        'rfc': rfc.get_id(),
        'file': rfc_json_repo.findpath(rfc),
        'total': len(contents),
        'title_translated': is_title_translated(obj),
        'remaining': len(remaining),
        'remaining_chars': sum(len(contents[i][RfcJsonElem.Contents.TEXT]) for i in remaining),
        'remaining_idx': remaining,
        'batches': batches,
    }
    return status


def trans_export(rfc: IRfc,
                 rfc_json_trans_repo: IRfcJsonTransRepository,
                 rfc_json_trans_midway_repo: IRfcJsonTransMidwayRepository,
                 offset: int = 0, limit: int | None = None,
                 include_translated: bool = False) -> dict:
    """翻訳対象の段落を取得する。

    offsetとlimitは段落番号（idx）の範囲 [offset, offset+limit) を表す。
    前後の段落は文脈の把握用に context として付与する（翻訳対象ではない）"""

    assert isinstance(rfc, IRfc)

    repo = _find_working_repo(rfc, rfc_json_trans_repo, rfc_json_trans_midway_repo)
    obj = repo.find(rfc)
    contents = obj[RfcJsonElem.CONTENTS]
    end = len(contents) if limit is None else min(len(contents), offset + limit)

    def to_context(i: int) -> dict:
        item = {'idx': i, 'text': contents[i][RfcJsonElem.Contents.TEXT]}
        if contents[i].get(RfcJsonElem.Contents.JA):
            item['ja'] = contents[i][RfcJsonElem.Contents.JA]
        return item

    items = []
    for i in range(offset, end):
        content = contents[i]
        if content.get(RfcJsonElem.Contents.RAW) is True:
            continue
        if is_translated(content) and not include_translated:
            continue
        item = {'idx': i, 'text': content[RfcJsonElem.Contents.TEXT]}
        if content.get(RfcJsonElem.Contents.SECTION_TITLE):
            item['section_title'] = True
        if prefix := get_required_prefix(content[RfcJsonElem.Contents.TEXT]):
            item['prefix'] = prefix
        if content.get(RfcJsonElem.Contents.JA):
            item['ja'] = content[RfcJsonElem.Contents.JA]
        items.append(item)

    result = {
        'rfc': rfc.get_id(),
        'title': obj[RfcJsonElem.TITLE],
        'context_before': [to_context(i) for i in range(max(0, offset - CONTEXT_SIZE), offset)
                           if contents[i].get(RfcJsonElem.Contents.RAW) is not True],
        'items': items,
        'context_after': [to_context(i) for i in range(end, min(len(contents), end + CONTEXT_SIZE))
                          if contents[i].get(RfcJsonElem.Contents.RAW) is not True],
    }
    return result


def trans_import(rfc: IRfc,
                 rfc_json_trans_repo: IRfcJsonTransRepository,
                 rfc_json_trans_midway_repo: IRfcJsonTransMidwayRepository,
                 input_obj: dict) -> dict:
    """訳文を検証して作業ファイルに適用する。

    入力形式: {"title_ja": "RFC XXXX - ...", "items": [{"idx": 12, "ja": "..."}, ...]}
    1件でも検証に失敗したときは何も適用しない"""

    assert isinstance(rfc, IRfc)

    repo = _find_working_repo(rfc, rfc_json_trans_repo, rfc_json_trans_midway_repo)
    filepath = repo.findpath(rfc)

    with _locked(filepath):
        obj = repo.find(rfc)
        contents = obj[RfcJsonElem.CONTENTS]
        errors = []

        title_ja = input_obj.get('title_ja')
        if title_ja is not None:
            # 原題の「RFC XXXX - 」の部分は訳文でもそのまま残す
            title_text = obj[RfcJsonElem.TITLE][RfcJsonElem.Title.TEXT]
            title_prefix = title_text.split(' - ', 1)[0] + ' - ' if ' - ' in title_text else ''
            if not isinstance(title_ja, str) or not title_ja.strip():
                errors.append('title_ja: タイトルが空です')
            elif not title_ja.startswith(title_prefix):
                errors.append(f'title_ja: 「{title_prefix}」から始めてください')

        items = input_obj.get('items', [])
        if not isinstance(items, list):
            raise TransError('items は配列で指定してください')
        seen = set()
        for item in items:
            idx = item.get('idx') if isinstance(item, dict) else None
            if not isinstance(idx, int) or isinstance(idx, bool) or not (0 <= idx < len(contents)):
                errors.append(f'idx={idx!r}: 段落番号が範囲外です (0〜{len(contents) - 1})')
                continue
            if idx in seen:
                errors.append(f'idx={idx}: 同じ段落番号が複数あります')
                continue
            seen.add(idx)
            if error := validate_ja(contents[idx], item.get('ja')):
                errors.append(f'idx={idx}: {error}')

        if errors:
            raise TransError('訳文の検証に失敗しました（何も適用していません）:\n  ' + '\n  '.join(errors))

        if title_ja is not None:
            obj[RfcJsonElem.TITLE][RfcJsonElem.Title.JA] = title_ja
        for item in items:
            contents[item['idx']][RfcJsonElem.Contents.JA] = item['ja']
        repo.save(rfc, obj)

    print(f"[+] Save file: {filepath} ({len(items)}段落を適用)")
    return trans_status(rfc, repo)


def trans_finish(rfc: IRfc,
                 rfc_json_data_repo: IRfcJsonDataRepository,
                 rfc_json_trans_repo: IRfcJsonTransRepository,
                 rfc_json_trans_midway_repo: IRfcJsonTransMidwayRepository) -> bool:
    """全段落が翻訳済みであることを確認し、翻訳結果ファイルとして確定する"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_data_repo, IRfcJsonDataRepository)
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)
    assert isinstance(rfc_json_trans_midway_repo, IRfcJsonTransMidwayRepository)

    print(f"[*] trans_finish({rfc.get_id()})")

    obj = rfc_json_trans_midway_repo.find(rfc)
    if not obj:
        raise TransError(f'RFC {rfc.get_id()} の作業ファイルがありません')

    status = trans_status(rfc, rfc_json_trans_midway_repo)
    if not status['title_translated']:
        raise TransError('タイトルが未翻訳です')
    if status['remaining'] > 0:
        raise TransError(f"未翻訳の段落が {status['remaining']} 件あります: idx={status['remaining_idx']}")

    # 翻訳成果物をファイルに出力する
    rfc_json_trans_repo.save(rfc, obj)
    print(f"[+] Save file: {rfc_json_trans_repo.findpath(rfc)}")
    # 不要な入力ファイルの削除
    if rfc_json_data_repo.delete(rfc):
        print(f"[+] Delete file: {rfc_json_data_repo.findpath(rfc)}")
    # 不要な中間ファイルの削除
    midway_file = rfc_json_trans_midway_repo.findpath(rfc)
    if rfc_json_trans_midway_repo.delete(rfc):
        print(f"[+] Delete file: {midway_file}")
    return True


def print_json(obj: object) -> None:
    """結果を標準出力にJSONで出力する"""
    json.dump(obj, sys.stdout, ensure_ascii=False, indent=1)
    print()

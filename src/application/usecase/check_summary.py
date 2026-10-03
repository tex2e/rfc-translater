# ------------------------------------------------------------------------------
# RFCの要約を検証するプログラム
#
# 要約そのものはClaudeが作成する（.claude/skills/summarize-rfc を参照）。
# このプログラムは、作成された rfcXXXX-summary.json の形式を検証する。
# ------------------------------------------------------------------------------

import re
import glob
import os
from ...domain.valueobject.rfc import RfcSummaryJsonElem, IRfc, Rfc
from ...domain.services.rfcfile import RfcFile
from ...infrastructure.repository.rfcjsontransrepository import IRfcJsonTransRepository
from ...infrastructure.repository.rfcjsondatasummaryrepository import IRfcJsonDataSummaryRepository

# 要約文の数と1文あたりの文字数の上限
SUMMARY_MAX_ITEMS = 3
SUMMARY_MAX_CHARS = 200
# created_at の形式 (例: 2026-02-15T00:00:00.000000)
CREATED_AT_PATTERN = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}$'
# 要約文に使ってはならない記号（強調、コードブロック、バックスラッシュ）
FORBIDDEN_MARKUP_PATTERN = r'\*\*|`|\\'
# ですます調の文末（「〜を規定します（RFC 1234を更新）。」のような末尾の補足は許容する）
POLITE_ENDING_PATTERN = r'(です|ます|ません|でした|ました|でしょう|ください)(。|（[^（）]*）。|。（[^（）]*）)$'


def check_summary(rfc: IRfc,
                  rfc_json_trans_repo: IRfcJsonTransRepository,
                  rfc_json_data_summary_repo: IRfcJsonDataSummaryRepository) -> list[str]:
    """要約ファイルの形式を検証する。問題があればその内容の一覧を返す"""

    assert isinstance(rfc, IRfc)
    assert isinstance(rfc_json_trans_repo, IRfcJsonTransRepository)
    assert isinstance(rfc_json_data_summary_repo, IRfcJsonDataSummaryRepository)

    obj = rfc_json_data_summary_repo.find(rfc)
    if obj is None:
        return [f'要約ファイルがありません: {rfc_json_data_summary_repo.findpath(rfc)}']
    if not rfc_json_trans_repo.find(rfc):
        return ['翻訳ファイルがありません。先に翻訳を完了させてください']

    errors = []
    expected_keys = [RfcSummaryJsonElem.NUMBER, RfcSummaryJsonElem.MODEL,
                     RfcSummaryJsonElem.CREATED_AT, RfcSummaryJsonElem.SUMMARY]
    if not isinstance(obj, dict) or list(obj.keys()) != expected_keys:
        return [f'キーは {expected_keys} の順で指定してください']

    number = obj[RfcSummaryJsonElem.NUMBER]
    if isinstance(number, bool) or not isinstance(number, int) or str(number) != rfc.get_id():
        errors.append(f'number: RFC番号 {rfc.get_id()} を整数で指定してください')
    model = obj[RfcSummaryJsonElem.MODEL]
    if not isinstance(model, str) or not model.strip():
        errors.append('model: 要約を生成したモデルのIDを指定してください')
    created_at = obj[RfcSummaryJsonElem.CREATED_AT]
    if not isinstance(created_at, str) or not re.match(CREATED_AT_PATTERN, created_at):
        errors.append('created_at: "2026-02-15T00:00:00.000000" の形式で指定してください')

    summary = obj[RfcSummaryJsonElem.SUMMARY]
    if not isinstance(summary, list) or not (1 <= len(summary) <= SUMMARY_MAX_ITEMS):
        errors.append(f'summary: 要約文を1〜{SUMMARY_MAX_ITEMS}件の配列で指定してください')
        return errors
    for i, text in enumerate(summary):
        if not isinstance(text, str) or not text.strip():
            errors.append(f'summary[{i}]: 要約文が空です')
            continue
        if text != text.strip() or '\n' in text:
            errors.append(f'summary[{i}]: 前後の空白や改行を含めないでください')
        if len(text) > SUMMARY_MAX_CHARS:
            errors.append(f'summary[{i}]: {len(text)}文字あります（{SUMMARY_MAX_CHARS}文字以内）')
        if re.search(FORBIDDEN_MARKUP_PATTERN, text):
            errors.append(f'summary[{i}]: 強調の ** やコードブロックの記号、バックスラッシュは使えません')
        if not re.search(POLITE_ENDING_PATTERN, text):
            errors.append(f'summary[{i}]: ですます調の文で終えてください')
    return errors


def find_unsummarized(begin: int = 2220) -> list[int]:
    """翻訳済みで要約が未作成のRFC番号の一覧を取得する"""
    rfc_numbers = []
    for filepath in glob.glob(RfcFile.GLOB_DATA_TRANS_JSON_FILE):
        m = re.match(r'rfc(\d+)-trans\.json$', os.path.basename(filepath))
        if not m or int(m[1]) < begin:
            continue
        if not os.path.isfile(RfcFile.get_filepath_data_summary_json(Rfc(m[1]))):
            rfc_numbers.append(int(m[1]))
    return sorted(rfc_numbers)

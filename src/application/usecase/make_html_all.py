# ------------------------------------------------------------------------------
# 翻訳済みの全RFC・全DraftのHTMLを作り直すためのプログラム
# ------------------------------------------------------------------------------
#
# 本文中の [RFCxxxx] のリンク先（翻訳済みページ or datatracker）はHTMLの生成時に決まるため、
# 新しいRFCの翻訳を追加したときは、それを参照している既存ページも作り直す必要がある。
# 生成結果は入力が同じなら毎回同じになるため、全件を作り直しても差分が出るのは
# 実際に変化したページだけになる。

from __future__ import annotations

import os
import re
import glob
import io
import contextlib
from concurrent.futures import ProcessPoolExecutor
from ...domain.valueobject.rfc import IRfc, Rfc, RfcDraft
from ...domain.services.rfcfile import RfcFile
from ...infrastructure.repository.rfcjsontransrepository import RfcJsonTransFileRepository
from ...infrastructure.repository.rfcjsondatasummaryrepository import RfcJsonDataSummaryFileRepository
from ...infrastructure.repository.rfchtmlrepository import RfcHtmlFileRepository
from .make_html import make_html


def find_all_targets() -> list[IRfc]:
    """翻訳済みJSONが存在する全RFC（番号順）と全Draft"""
    rfc_numbers = set()
    for filepath in glob.glob(RfcFile.GLOB_DATA_TRANS_JSON_FILE):
        if m := re.fullmatch(r'rfc(\d+)-trans\.json', os.path.basename(filepath)):
            rfc_numbers.add(int(m[1]))
    drafts = set()
    for filepath in glob.glob(RfcFile.GLOB_DATA_DRAFT_TRANS_JSON_FILE):
        if m := re.fullmatch(r'(draft-.+)-trans\.json', os.path.basename(filepath)):
            drafts.add(m[1])
    return [Rfc(str(n)) for n in sorted(rfc_numbers)] + [RfcDraft(d) for d in sorted(drafts)]


def _make_html_quietly(rfc: IRfc) -> str:
    """1件分のHTML作成（並列実行用。件数が多いため個別のログは出さない）"""
    with contextlib.redirect_stdout(io.StringIO()):
        make_html(rfc, RfcJsonTransFileRepository(),
                  RfcJsonDataSummaryFileRepository(),
                  RfcHtmlFileRepository())
    return rfc.get_id()


def make_html_all(max_workers: int | None = None) -> int:
    """全RFC・全DraftのHTMLを並列で作成し、作成した件数を返す"""
    targets = find_all_targets()
    print(f'[*] make_html_all: {len(targets)} files')
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for i, _ in enumerate(executor.map(_make_html_quietly, targets, chunksize=20), start=1):
            if i % 1000 == 0 or i == len(targets):
                print(f'[*] make_html_all: {i}/{len(targets)}')
    return len(targets)

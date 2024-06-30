# ------------------------------------------------------------------------------
# RFC翻訳 各機能の呼び出しメインプログラム
# ------------------------------------------------------------------------------

import sys
import argparse
from ..domain.valueobject.rfc import Rfc, RfcDraft, RFCNotFoundException
from ..application.usecase.fetch_rfc import fetch_rfc
from ..application.usecase.trans_rfc import trans_rfc, trans_test
from ..application.usecase.make_html import make_html
from ..application.usecase.make_index import make_index, make_index_draft
from ..application.usecase.fetch_index import diff_remote_and_local_index
from ..application.usecase.fetch_status import fetch_status
from ..application.usecase.make_json_from_html import make_json_from_html
from ..domain.services.rfc_utils import RfcUtils
from ..infrastructure.repository.rfcjsondatarepository import RfcJsonDataFileRepository
from ..infrastructure.repository.rfcjsontransrepository import RfcJsonTransFileRepository
from ..infrastructure.repository.rfcjsontransmidwayrepository import RfcJsonTransMidwayFileRepository
from ..infrastructure.repository.rfcjsondatasummaryrepository import RfcJsonDataSummaryFileRepository
from ..infrastructure.repository.rfchtmlrepository import RfcHtmlFileRepository
from ..infrastructure.repository.indexhtmlrepository import IndexHtmlFileRepository
from ..infrastructure.repository.indexdrafthtmlrepository import IndexDraftHtmlFileRepository
from ..infrastructure.repository.rfcstatusjsonrepository import RfcStatusJsonFileRepository
from ..infrastructure.apiclient.rfcapiclient import RfcHttpApiClient
from ..infrastructure.apiclient.rfcindexapiclient import RfcIndexHttpApiClient


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rfc', type=str,
                    help='RFC number (ex. --rfc 8446)')
    ap.add_argument('--fetch', action='store_true',
                    help='Only fetch RFC (ex. --rfc 8446 --fetch)')
    ap.add_argument('--trans', action='store_true',
                    help='Only translate (ex. --rfc 8446 --trans)')
    ap.add_argument('--make', action='store_true',
                    help='Only make HTML (ex. --rfc 8446 --fetch)')
    ap.add_argument('--make-json', action='store_true',
                    help='Make JSON from HTML (ex. --make-json --rfc 8446)')
    ap.add_argument('--make-index', action='store_true',
                    help='Make html/index.html (ex. --make-index)')
    ap.add_argument('--force', '-f', action='store_true',
                    help='Ignore cache (ex. --rfc 8446 --fetch --force)')
    ap.add_argument('--begin', type=int,
                    help='Set begin rfc number (ex. --begin 8000)')
    ap.add_argument('--end', type=int,
                    help='Set end rfc number (ex. --begin 8000 --end 9000)')
    ap.add_argument('--only-first', action='store_true',
                    help='Take only first RFC (ex. --begin 8000 --only-first)')
    ap.add_argument('--draft', type=str,
                    help='Take RFC draft (ex. --draft draft-ietf-tls-esni-14)')
    ap.add_argument('--make-index-draft', action='store_true',
                    help='Make draft/index.html (ex. --make-index-draft)')
    ap.add_argument('--fetch-status', action='store_true',
                    help='Make group-rfcs.json and obsoletes.json')
    ap.add_argument('--summarize', action='store_true',
                    help='Summarize RFC by ChatGPT (ex. --summarize --rfc 8446)')
    ap.add_argument('--chatgpt', type=str,
                    help='ChatGPT model version (ex. --chatgpt gpt-3.5-turbo)')
    ap.add_argument('--txt', action='store_true',
                    help='Fetch TXT (ex. --rfc 8446 --fetch --txt)')
    ap.add_argument('--transtest', action='store_true',
                    help='Do translate test')
    ap.add_argument('--debug', action='store_true',
                    help='Show more output for debug')
    args = ap.parse_args()

    # RFCの指定（複数の場合はカンマ区切り）
    rfcs = None
    if args.rfc:
        rfcs = [Rfc(str(rfc_number)) for rfc_number in args.rfc.split(",")]
    elif args.begin and args.end:
        rfcs = [Rfc(str(rfc_number)) for rfc_number in range(args.begin, args.end)]
    elif args.draft:
        rfcs = [RfcDraft(args.draft)]
    elif args.only_first:
        # RFC 2220以降のみを対象とする。ただし、引数beginで変更可能
        begin = 2220
        if args.begin:
            begin = args.begin
        # リモートとローカルの差分でRFCの一覧を作成する
        rfcs = []
        for rfc_number in diff_remote_and_local_index(RfcIndexHttpApiClient(), RfcHtmlFileRepository()):
            if rfc_number >= begin:
                rfcs.append(Rfc(str(rfc_number)))
        # 未翻訳の最初のRFCのみ取得
        if args.only_first:
            rfcs = rfcs[0:1]

    if args.make_index:
        print("[*] トップページ(index.html)の作成")
        make_index(IndexHtmlFileRepository(),
                   RfcHtmlFileRepository())
    elif args.make_index_draft:
        print("[*] draft/index.htmlの作成")
        make_index_draft(IndexDraftHtmlFileRepository(),
                         RfcHtmlFileRepository())
    elif args.fetch_status:
        print("[*] RFCの更新状況とWorkingGroupの一覧作成")
        fetch_status(RfcStatusJsonFileRepository(),
                     RfcIndexHttpApiClient())
    elif args.transtest:
        print("[*] 翻訳テスト開始...")
        trans_test(args)
    elif args.make_json and rfcs:
        # 指定したRFCのJSONを翻訳修正したHTMLから逆作成
        for rfc in rfcs:
            make_json_from_html(rfc, RfcHtmlFileRepository(),
                                RfcJsonTransFileRepository())
    elif args.summarize and rfcs:
        # RFCの要約作成
        from ..application.usecase.nlp_summarize_rfc import summarize_rfc
        for rfc in rfcs:
            if summarize_rfc(rfc, RfcJsonTransFileRepository(),
                             RfcJsonDataSummaryFileRepository(), args):
                # RFCのHTMLを作成
                make_html(rfc, RfcJsonTransFileRepository(),
                          RfcJsonDataSummaryFileRepository(),
                          RfcHtmlFileRepository())
    elif rfcs:
        all_option_none = ((not args.fetch) and (not args.trans) and (not args.make))
        # 取得、翻訳、作成の一連の流れ
        if args.fetch or all_option_none:
            # 指定したRFCの取得 (rfcXXXX.json)
            for rfc in rfcs:
                try:
                    fetch_rfc(rfc, RfcJsonDataFileRepository(),
                              RfcHttpApiClient(), args)
                except RFCNotFoundException:
                    print('Exception: RFCNotFound!')
                    filename = f"html/rfc{rfc.get_id()}-not-found.html"
                    with open(filename, "w") as f:
                        f.write('')
        if args.trans or all_option_none:
            # RFCの翻訳 (rfcXXXX-trans.json)
            for rfc in rfcs:
                trans_rfc(rfc, RfcJsonDataFileRepository(),
                          RfcJsonTransFileRepository(),
                          RfcJsonTransMidwayFileRepository(), args)
        if args.make or all_option_none:
            # RFCのHTMLを作成 (rfcXXXX.html)
            for rfc in rfcs:
                make_html(rfc, RfcJsonTransFileRepository(),
                          RfcJsonDataSummaryFileRepository(),
                          RfcHtmlFileRepository())
    else:
        ap.print_help()
    print("[+] 正常終了 %s (%s)" % (sys.argv[0], RfcUtils.get_now()))

# ------------------------------------------------------------------------------
# RFC翻訳 各機能の呼び出しメインプログラム
# ------------------------------------------------------------------------------

import sys
import json
import argparse
from ..domain.valueobject.rfc import Rfc, RfcDraft, RFCNotFoundException
from ..domain.services.rfcutils import RfcUtils
from ..application.usecase.fetch_rfc import fetch_rfc
from ..application.usecase.trans_rfc import (trans_prepare, trans_export, trans_import, trans_finish,
                                             trans_status, print_json, TransError)
from ..application.usecase.make_html import make_html
from ..application.usecase.make_html_all import make_html_all
from ..application.usecase.make_index import make_index, make_index_draft
from ..application.usecase.make_title_json import make_title_json
from ..application.usecase.fetch_index import diff_remote_and_local_index
from ..application.usecase.fetch_status import fetch_status
from ..application.usecase.make_json_from_html import make_json_from_html
from ..infrastructure.repository.rfcjsondatarepository import RfcJsonDataFileRepository
from ..infrastructure.repository.rfcjsontransrepository import RfcJsonTransFileRepository
from ..infrastructure.repository.rfcjsontransmidwayrepository import RfcJsonTransMidwayFileRepository
from ..infrastructure.repository.rfcjsondatasummaryrepository import RfcJsonDataSummaryFileRepository
from ..infrastructure.repository.rfchtmlrepository import RfcHtmlFileRepository
from ..infrastructure.repository.indexhtmlrepository import IndexHtmlFileRepository
from ..infrastructure.repository.indexdrafthtmlrepository import IndexDraftHtmlFileRepository
from ..infrastructure.repository.rfcstatusjsonrepository import RfcStatusJsonFileRepository
from ..infrastructure.repository.rfctitlejsonrepository import RfcTitleJsonFileRepository
from ..infrastructure.apiclient.rfcapiclient import RfcHttpApiClient
from ..infrastructure.apiclient.rfcindexapiclient import RfcIndexHttpApiClient


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rfc', type=str,
                    help='RFC number (ex. --rfc 8446)')
    ap.add_argument('--fetch', action='store_true',
                    help='Only fetch RFC (ex. --rfc 8446 --fetch)')
    ap.add_argument('--trans-prepare', action='store_true',
                    help='Prepare working file for translation (ex. --rfc 8446 --trans-prepare)')
    ap.add_argument('--trans-export', action='store_true',
                    help='Print untranslated paragraphs as JSON (ex. --rfc 8446 --trans-export --offset 0 --limit 40)')
    ap.add_argument('--trans-import', type=str, metavar='FILE',
                    help='Apply translated JSON to working file (ex. --rfc 8446 --trans-import batch.json)')
    ap.add_argument('--trans-finish', action='store_true',
                    help='Finalize translation as rfcXXXX-trans.json (ex. --rfc 8446 --trans-finish)')
    ap.add_argument('--trans-status', action='store_true',
                    help='Print translation progress as JSON (ex. --rfc 8446 --trans-status)')
    ap.add_argument('--offset', type=int, default=0,
                    help='Start paragraph index for --trans-export')
    ap.add_argument('--limit', type=int,
                    help='Number of paragraphs for --trans-export')
    ap.add_argument('--include-translated', action='store_true',
                    help='Include translated paragraphs in --trans-export (for review)')
    ap.add_argument('--make', action='store_true',
                    help='Only make HTML (ex. --rfc 8446 --make)')
    ap.add_argument('--make-all', action='store_true',
                    help='Remake all HTML (RFCs, drafts and index pages) (ex. --make-all)')
    ap.add_argument('--make-json', action='store_true',
                    help='Make JSON from HTML (ex. --make-json --rfc 8446)')
    ap.add_argument('--make-index', action='store_true',
                    help='Make html/index.html (ex. --make-index)')
    ap.add_argument('--make-title-json', action='store_true',
                    help='Make html/data-rfc-title.json (ex. --make-title-json)')
    ap.add_argument('--force', '-f', action='store_true',
                    help='Ignore cache (ex. --rfc 8446 --fetch --force)')
    ap.add_argument('--begin', type=int,
                    help='Set begin rfc number (ex. --begin 8000)')
    ap.add_argument('--end', type=int,
                    help='Set end rfc number (ex. --begin 8000 --end 9000)')
    ap.add_argument('--only-first', action='store_true',
                    help='Take only first RFC (ex. --begin 8000 --only-first)')
    ap.add_argument('--list-untranslated', action='store_true',
                    help='Print untranslated RFC numbers (ex. --list-untranslated --begin 9000)')
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
    elif args.only_first or args.list_untranslated:
        # RFC 2220以降のみを対象とする。ただし、引数beginで変更可能
        begin = 2220
        if args.begin:
            begin = args.begin
        # リモートとローカルの差分でRFCの一覧を作成する
        rfcs = []
        for rfc_number in sorted(diff_remote_and_local_index(RfcIndexHttpApiClient(), RfcHtmlFileRepository())):
            if rfc_number >= begin:
                rfcs.append(Rfc(str(rfc_number)))
        if args.list_untranslated:
            # 未翻訳のRFC番号を1行ずつ出力する（定期実行の翻訳対象の選定用）
            for rfc in rfcs:
                print(rfc.get_id())
            return
        # 未翻訳の最初のRFCのみ取得
        if args.only_first:
            rfcs = rfcs[0:1]
        if len(rfcs) == 0:
            print("[+] ローカルとリモートのRFCに差分なし")
            print("[+] 正常終了 %s (%s)" % (sys.argv[0], RfcUtils.get_now()))
            return

    if args.make_all:
        # 本文中のRFCへのリンク先は生成時に決まるため、翻訳を追加したら全ページを作り直す
        print("[*] 全RFC・全DraftのHTMLの作成")
        make_html_all()
        print("[*] トップページ(index.html)の作成")
        make_index(IndexHtmlFileRepository(),
                   RfcHtmlFileRepository())
        print("[*] RFCの日本語タイトル一覧(data-rfc-title.json)の作成")
        make_title_json(RfcTitleJsonFileRepository(),
                        RfcJsonTransFileRepository())
        print("[*] draft/index.htmlの作成")
        make_index_draft(IndexDraftHtmlFileRepository(),
                         RfcHtmlFileRepository())
    elif args.make_index:
        print("[*] トップページ(index.html)の作成")
        make_index(IndexHtmlFileRepository(),
                   RfcHtmlFileRepository())
        # トップページと同じくRFC一覧に依存するため、まとめて最新化する
        print("[*] RFCの日本語タイトル一覧(data-rfc-title.json)の作成")
        make_title_json(RfcTitleJsonFileRepository(),
                        RfcJsonTransFileRepository())
    elif args.make_index_draft:
        print("[*] draft/index.htmlの作成")
        make_index_draft(IndexDraftHtmlFileRepository(),
                         RfcHtmlFileRepository())
    elif args.make_title_json:
        print("[*] RFCの日本語タイトル一覧(data-rfc-title.json)の作成")
        make_title_json(RfcTitleJsonFileRepository(),
                        RfcJsonTransFileRepository())
    elif args.fetch_status:
        print("[*] RFCの更新状況とWorkingGroupと発行年月の一覧作成")
        fetch_status(RfcStatusJsonFileRepository(),
                     RfcIndexHttpApiClient())
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
    elif rfcs and (args.trans_prepare or args.trans_export or args.trans_import
                   or args.trans_finish or args.trans_status):
        # RFCの翻訳 (rfcXXXX-trans.json)
        # 翻訳そのものはClaudeが行う（.claude/skills/translate-new-rfc を参照）
        if len(rfcs) != 1:
            print("[-] 翻訳の操作はRFCを1つだけ指定してください")
            sys.exit(1)
        rfc = rfcs[0]
        try:
            if args.trans_prepare:
                print_json(trans_prepare(rfc, RfcJsonDataFileRepository(),
                                         RfcJsonTransMidwayFileRepository()))
            elif args.trans_export:
                print_json(trans_export(rfc, RfcJsonTransFileRepository(),
                                        RfcJsonTransMidwayFileRepository(),
                                        args.offset, args.limit, args.include_translated))
                return
            elif args.trans_import:
                with open(args.trans_import, 'r', encoding='utf-8') as f:
                    input_obj = json.load(f)
                print_json(trans_import(rfc, RfcJsonTransFileRepository(),
                                        RfcJsonTransMidwayFileRepository(), input_obj))
            elif args.trans_finish:
                trans_finish(rfc, RfcJsonDataFileRepository(),
                             RfcJsonTransFileRepository(),
                             RfcJsonTransMidwayFileRepository())
            elif args.trans_status:
                repo = RfcJsonTransMidwayFileRepository()
                if not repo.find(rfc):
                    repo = RfcJsonTransFileRepository()
                if not repo.find(rfc):
                    raise TransError(f'RFC {rfc.get_id()} の作業ファイルがありません')
                print_json(trans_status(rfc, repo))
                return
        except (TransError, json.JSONDecodeError) as e:
            print(f"[-] Error: {e}")
            sys.exit(1)
    elif rfcs:
        all_option_none = ((not args.fetch) and (not args.make))
        # 取得、作成の一連の流れ（翻訳はClaudeが行うため、ここでは実施しない）
        if args.fetch or all_option_none:
            # 指定したRFCの取得 (rfcXXXX.json)
            for rfc in rfcs:
                if all_option_none and RfcJsonTransFileRepository().find(rfc):
                    continue  # 翻訳済みのRFCは取得し直さない
                try:
                    fetch_rfc(rfc, RfcJsonDataFileRepository(),
                              RfcHttpApiClient(), args)
                except RFCNotFoundException:
                    print('Exception: RFCNotFound!')
                    filename = f"html/rfc{rfc.get_id()}-not-found.html"
                    with open(filename, "w") as f:
                        f.write('')
        if args.make or all_option_none:
            # RFCのHTMLを作成 (rfcXXXX.html)
            for rfc in rfcs:
                if all_option_none and not RfcJsonTransFileRepository().find(rfc):
                    print(f"[!] RFC {rfc.get_id()} は未翻訳です。"
                          "Claudeのスキル translate-new-rfc で翻訳してください")
                    continue
                make_html(rfc, RfcJsonTransFileRepository(),
                          RfcJsonDataSummaryFileRepository(),
                          RfcHtmlFileRepository())
    else:
        ap.print_help()
        print()
    print("[+] 正常終了 %s (%s)" % (sys.argv[0], RfcUtils.get_now()))

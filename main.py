# ------------------------------------------------------------------------------
# RFC翻訳 各機能の呼び出しメインプログラム
# ------------------------------------------------------------------------------

import sys
import argparse
from src.fetch_rfc_txt import fetch_rfc_txt, RFCNotFound
from src.fetch_rfc_xml import fetch_rfc_xml
from src.trans_rfc import trans_rfc, trans_test
from src.make_html import make_html
from src.make_index import make_index, make_index_draft
from src.fetch_index import diff_remote_and_local_index
from src.fetch_status import fetch_status
from src.rfc_utils import RfcUtils

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
    ap.add_argument('--begin', type=int,
                    help='Set begin rfc number (ex. --begin 8000)')
    ap.add_argument('--end', type=int,
                    help='Set end rfc number (ex. --begin 8000 --end 9000)')
    ap.add_argument('--make-index', action='store_true',
                    help='Make html/index.html (ex. --make-index)')
    ap.add_argument('--force', '-f', action='store_true',
                    help='Ignore cache (ex. --rfc 8446 --fetch --force)')
    ap.add_argument('--only-first', action='store_true',
                    help='Take only first RFC (ex. --begin 8000 --only-first)')
    ap.add_argument('--draft', type=str,
                    help='Take RFC draft (ex. --draft draft-ietf-tls-esni-14)')
    ap.add_argument('--fetch-status', action='store_true',
                    help='Make group-rfcs.json and obsoletes.json')
    ap.add_argument('--make-index-draft', action='store_true',
                    help='Make draft/index.html (ex. --make-index-draft)')
    ap.add_argument('--transtest', action='store_true',
                    help='Do translate test')
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
        rfcs = [int(rfc_number) for rfc_number in args.rfc.split(",")]
    elif args.begin and args.end:
        rfcs = list(range(args.begin, args.end))
    elif args.draft:
        rfcs = [args.draft]

    if args.make_index:
        print("[*] トップページ(index.html)の作成")
        make_index()
    elif args.make_index_draft:
        print("[*] draft/index.htmlの作成")
        make_index_draft()
    elif args.fetch_status:
        print("[*] RFCの更新状況とWorkingGroupの一覧作成")
        fetch_status()
    elif args.transtest:
        print("[*] 翻訳テスト開始...")
        trans_test(args)
    elif args.summarize and rfcs:
        # RFCの要約作成
        from src.nlp_summarize_rfc import summarize_rfc
        for rfc_number in rfcs:
            print("[*] RFC %s を要約" % rfc_number)
            if summarize_rfc(rfc_number, args):
                # RFCのHTMLを作成
                print("[*] RFC %s のHTMLを生成" % rfc_number)
                make_html(rfc_number)
    elif args.fetch and rfcs:
        # 指定したRFCの取得 (rfcXXXX.json)
        for rfc_number in rfcs:
            print("[*] RFC %s を取得" % rfc_number)
            if (isinstance(rfc_number, int) and rfc_number >= 8650) and (not args.txt):
                fetch_rfc_xml(rfc_number, args)
            else:
                fetch_rfc_txt(rfc_number, args)
    elif args.trans and rfcs:
        # RFCの翻訳 (rfcXXXX-trans.json)
        for rfc_number in rfcs:
            print("[*] RFC %s を翻訳" % rfc_number)
            trans_rfc(rfc_number, args)
    elif args.make and rfcs:
        # RFCのHTMLを作成 (rfcXXXX.html)
        if len(rfcs) == 1:
            print("[*] RFC %s のHTMLを生成" % (rfcs[0]))
        elif len(rfcs) > 1:
            print("[*] RFC %s - %s のHTMLを生成" % (rfcs[0], rfcs[-1]))
        for rfc_number in rfcs:
            make_html(rfc_number)
    elif args.make_json and rfcs:
        # 指定したRFCのJSONを翻訳修正したHTMLから逆作成
        from src.make_json_from_html import make_json_from_html
        for rfc_number in rfcs:
            make_json_from_html(rfc_number)
    elif rfcs:
        # 範囲指定でRFCを順番に取得・翻訳・作成
        for rfc_number in rfcs:
            _fetch_trans_make(rfc_number, args)
    elif args.begin and args.only_first:
        # 未翻訳のRFCを順番に取得・翻訳・作成
        _continuous_main(args)
    else:
        ap.print_help()
    print("[+] 正常終了 %s (%s)" % (sys.argv[0], RfcUtils.get_now()))

def _fetch_trans_make(rfc_number: int | str, args) -> None:
    """RFCの取得、翻訳、HTML作成をまとめて行う"""
    print('[*] RFC %s:' % rfc_number)
    try:
        if (isinstance(rfc_number, int) and rfc_number >= 8560) and (not args.txt):
            fetch_rfc_xml(rfc_number, args)
        else:
            fetch_rfc_txt(rfc_number, args)
    except RFCNotFound:
        print('Exception: RFCNotFound!')
        filename = "html/rfc%s-not-found.html" % rfc_number
        with open(filename, "w") as f:
            f.write('')
        return
    trans_rfc(rfc_number, args)
    make_html(rfc_number)

def _continuous_main(args):
    """複数範囲のRFCを処理する"""
    numbers = [x for x in diff_remote_and_local_index() if x >= 2220]
    if args.begin and args.end:
        # 開始と終了区間の設定
        numbers = [x for x in numbers if args.begin <= x <= args.end]
    elif args.begin:
        # 開始のみ設定
        numbers = [x for x in numbers if args.begin <= x]

    if args.only_first:
        # 最初の1つのRFCのみ選択
        numbers = numbers[0:1]

    for rfc_number in numbers:
        fetch_trans_make(rfc_number, args)

if __name__ == '__main__':
    main()

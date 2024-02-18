# ------------------------------------------------------------------------------
# RFC翻訳 各機能の呼び出しメインプログラム
# ------------------------------------------------------------------------------

import sys
from fetch_rfc import fetch_rfc, RFCNotFound
from trans_rfc import trans_rfc
from make_html import make_html
from make_index import make_index, make_index_draft
from fetch_index import diff_remote_and_local_index

def main(rfc_number: int | str) -> None:
    print('[*] RFC %s:' % rfc_number)

    try:
        fetch_rfc(rfc_number)
    except RFCNotFound:
        print('Exception: RFCNotFound!')
        filename = "html/rfc%s-not-found.html" % rfc_number
        with open(filename, "w") as f:
            f.write('')
        return

    trans_rfc(rfc_number)
    make_html(rfc_number)

def continuous_main(begin=None, end=None, only_first=False):
    numbers = [x for x in diff_remote_and_local_index() if x >= 2220]
    if begin and end:  # 開始と終了区間の設定
        numbers = [x for x in numbers if begin <= x <= end]
    elif begin:  # 開始のみ設定
        numbers = [x for x in numbers if begin <= x]

    if only_first:  # 最初の1つのRFCのみ選択
        numbers = numbers[0:1]

    for rfc_number in numbers:
        main(rfc_number)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--rfc',              type=str,            help='RFC number            (ex. --rfc 8446)')
    ap.add_argument('--fetch',            action='store_true', help='Only fetch RFC        (ex. --rfc 8446 --fetch)')
    ap.add_argument('--trans',            action='store_true', help='Only translate        (ex. --rfc 8446 --trans)')
    ap.add_argument('--make',             action='store_true', help='Only make HTML        (ex. --rfc 8446 --fetch)')
    ap.add_argument('--make-json',        action='store_true', help='Make JSON from HTML   (ex. --make-json --rfc 8446)')
    ap.add_argument('--begin',            type=int,            help='Set begin rfc number  (ex. --begin 8000)')
    ap.add_argument('--end',              type=int,            help='Set end rfc number    (ex. --begin 8000 --end 9000)')
    ap.add_argument('--make-index',       action='store_true', help='Make html/index.html  (ex. --make-index)')
    ap.add_argument('--force', '-f',      action='store_true', help='Ignore cache          (ex. --rfc 8446 --fetch --force)')
    ap.add_argument('--only-first',       action='store_true', help='Take only first RFC   (ex. --begin 8000 --only-first)')
    ap.add_argument('--draft',            type=str,            help='Take RFC draft        (ex. --draft draft-ietf-tls-esni-14)')
    ap.add_argument('--fetch-status',     action='store_true', help='Make group-rfcs.json and obsoletes.json')
    ap.add_argument('--make-index-draft', action='store_true', help='Make draft/index.html (ex. --make-index-draft)')
    ap.add_argument('--transtest',        action='store_true')
    ap.add_argument('--summarize',        action='store_true', help='Summarize RFC by ChatGPT (ex. --summarize --rfc 8446)')
    ap.add_argument('--chatgpt',          type=str,            help='ChatGPT model version    (ex. --chatgpt gpt-3.5-turbo)')
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
        from src.fetch_wg import write_rfc_wg_list, write_rfc_obsoletes
        write_rfc_wg_list()
        write_rfc_obsoletes()
    elif args.transtest:
        print("[*] 翻訳テスト開始...")
        from src.trans_rfc import trans_test
        res = trans_test()
        print('Translate test result:', res)
    elif args.summarize and rfcs:
        # RFCの要約作成
        from src.summarize_rfc import summarize_rfc
        for rfc in rfcs:
            print("[*] RFC %s を要約" % rfc)
            if summarize_rfc(rfc, args.chatgpt, args.force):
                # RFCのHTMLを作成
                print("[*] RFC %s のHTMLを生成" % rfc)
                make_html(rfc)
    elif args.fetch and rfcs:
        # 指定したRFCの取得 (rfcXXXX.json)
        for rfc in rfcs:
            print("[*] RFC %s を取得" % rfc)
            fetch_rfc(rfc, args.force)
    elif args.trans and rfcs:
        # RFCの翻訳 (rfcXXXX-trans.json)
        for rfc in rfcs:
            print("[*] RFC %s を翻訳" % rfc)
            trans_rfc(rfc)
    elif args.make and rfcs:
        # RFCのHTMLを作成 (rfcXXXX.html)
        if len(rfcs) == 1:
            print("[*] RFC %d のHTMLを生成" % (rfcs[0]))
        elif len(rfcs) > 1:
            print("[*] RFC %d - %d のHTMLを生成" % (rfcs[0], rfcs[-1]))
        for rfc in rfcs:
            make_html(rfc)
    elif args.make_json and rfcs:
        # 指定したRFCのJSONを翻訳修正したHTMLから逆作成
        from src.make_json_from_html import make_json_from_html
        for rfc in rfcs:
            make_json_from_html(rfc)
    elif rfcs:
        # 範囲指定でRFCを順番に取得・翻訳・作成
        for rfc in rfcs:
            main(rfc)
    elif args.begin or args.only_first:
        # 未翻訳のRFCを順番に取得・翻訳・作成
        continuous_main(begin=args.begin, end=args.end, only_first=args.only_first)
    else:
        ap.print_help()

print("[+] 正常終了 %s" % sys.argv[0])

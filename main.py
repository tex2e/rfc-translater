# ------------------------------------------------------------------------------
# RFC翻訳 各機能の呼び出しメインプログラム
# ------------------------------------------------------------------------------

import sys
import time
from src.fetch_rfc import fetch_rfc, RFCNotFound
from src.trans_rfc import trans_rfc
from src.make_html import make_html
from src.make_index import make_index, make_index_draft
from src.fetch_index import diff_remote_and_local_index
from src.make_json_from_html import make_json_from_html
from src.fetch_wg import write_rfc_wg_list

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
    # print('[*] diff_remote_and_local:')
    # print(numbers)
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
    parser = argparse.ArgumentParser()
    parser.add_argument('--rfc',         type=str,            help='RFC number            (ex. --rfc 8446)')
    parser.add_argument('--fetch',       action='store_true', help='only fetch RFC        (ex. --rfc 8446 --fetch)')
    parser.add_argument('--trans',       action='store_true', help='only translate        (ex. --rfc 8446 --trans)')
    parser.add_argument('--make',        action='store_true', help='only make HTML        (ex. --rfc 8446 --fetch)')
    parser.add_argument('--make-json',   action='store_true', help='make JSON from HTML   (ex. --make-json --rfc 8446)')
    parser.add_argument('--begin',       type=int,            help='begin rfc number      (ex. --begin 8000)')
    parser.add_argument('--end',         type=int,            help='end rfc number        (ex. --begin 8000 --end 9000)')
    parser.add_argument('--make-index',  action='store_true', help='make html/index.html  (ex. --make-index)')
    parser.add_argument('--force', '-f', action='store_true', help='ignore cache          (ex. --rfc 8446 --fetch --force)')
    parser.add_argument('--only-first',  action='store_true', help='take only first RFC   (ex. --begin 8000 --only-first)')
    parser.add_argument('--draft',       type=str,            help='take RFC draft        (ex. --draft draft-ietf-tls-esni-14)')
    parser.add_argument('--fetch-group', action='store_true', help='fetch WG list         (ex. --fetch-group)')
    parser.add_argument('--make-index-draft',
                                         action='store_true', help='make draft/index.html (ex. --make-index-draft)')
    parser.add_argument('--transtest',   action='store_true')
    parser.add_argument('--summarize',   action='store_true', help='Summarize RFC by ChatGPT (ex. --summarize --rfc 8446)')
    parser.add_argument('--chatgpt',     type=str,            help='ChatGPT model version    (ex. --chatgpt gpt-3.5-turbo)')
    args = parser.parse_args()

    # RFCの指定（複数の場合はカンマ区切り）
    rfcs = None
    if args.rfc:
        rfcs = [int(rfc_number) for rfc_number in args.rfc.split(",")]
    elif args.draft:
        rfcs = [args.draft]

    if args.make_index:
        # トップページ(index.html)の作成
        print("[*] index.htmlの作成")
        make_index()
    elif args.make_index_draft:
        # トップページ(draft/index.html)の作成
        print("[*] draft/index.htmlの作成")
        make_index_draft()
    elif args.fetch_group:
        # WorkingGroupの一覧作成
        print("[*] WorkingGroupの一覧作成")
        write_rfc_wg_list()
    elif args.transtest:
        # 翻訳のテスト
        from src.trans_rfc import trans_test
        res = trans_test()
        print('Translate test result:', res)
    elif args.summarize and args.begin and args.end:
        # 範囲指定でRFCの要約作成
        from src.summarize_rfc import summarize_rfc
        for rfc in range(args.begin, args.end):
            print("[*] RFC %s を要約" % rfc)
            if summarize_rfc(rfc, args.chatgpt, args.force):
                # RFCのHTMLを作成
                print("[*] RFC %s のHTMLを生成" % rfc)
                make_html(rfc)
                time.sleep(1)
    elif args.summarize:
        # RFCの要約作成
        from src.summarize_rfc import summarize_rfc
        for rfc in rfcs:
            print("[*] RFC %s を要約" % rfc)
            if summarize_rfc(rfc, args.chatgpt, args.force):
                # RFCのHTMLを作成
                print("[*] RFC %s のHTMLを生成" % rfc)
                make_html(rfc)
    elif args.fetch and args.begin and args.end:
        # 範囲指定でRFCの取得
        print("[*] RFC %d - %d のRFCを取得" % (args.begin, args.end))
        numbers = list(diff_remote_and_local_index())
        numbers = [x for x in numbers if args.begin <= x <= args.end]
        for rfc_number in numbers:
            fetch_rfc(rfc_number)
    elif args.fetch and rfcs:
        # 指定したRFCの取得
        for rfc in rfcs:
            print("[*] RFC %s を取得" % rfc)
            fetch_rfc(rfc, args.force)
    elif args.trans and rfcs:
        # RFCの翻訳
        for rfc in rfcs:
            print("[*] RFC %s を翻訳" % rfc)
            trans_rfc(rfc)
    elif args.make and args.begin and args.end:
        # 範囲指定でRFCのHTML(rfcXXXX.html)を作成
        print("[*] RFC %d - %d のHTMLを生成" % (args.begin, args.end))
        for rfc_number in range(args.begin, args.end):
            make_html(rfc_number)
    elif args.make and rfcs:
        # 指定したRFCのHTML(rfcXXXX.html)を作成
        for rfc in rfcs:
            make_html(rfc)
    elif args.make_json and rfcs:
        # 指定したRFCのJSONを翻訳修正したHTMLから逆作成
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
        parser.print_help()

print("[+] 正常終了 %s" % sys.argv[0])

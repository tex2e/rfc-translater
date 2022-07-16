
import sys
from src.fetch_rfc import fetch_rfc, RFCNotFound
# from src.trans_rfc import trans_rfc, TransMode
from src.trans_rfc import trans_rfc
from src.make_html import make_html
from src.make_index import make_index
from src.fetch_index import diff_remote_and_local_index
from src.make_json_from_html import make_json_from_html

# def main(rfc_number, transmode):
def main(rfc_number):
    print('RFC %d:' % rfc_number)

    try:
        fetch_rfc(rfc_number)
    except RFCNotFound as e:
        print('Exception: RFCNotFound!')
        filename = "html/rfc%d-not-found.html" % rfc_number
        with open(filename, "w") as f:
            f.write('')
        return
    except Exception as e:
        print(e)
        filename = "html/rfc%d-error.html" % rfc_number
        with open(filename, "w") as f:
            f.write('')
        return

    # res = trans_rfc(rfc_number, transmode)
    res = trans_rfc(rfc_number)
    if res is False: return False
    make_html(rfc_number)

# def continuous_main(transmode, begin=None, end=None, only_first=False):
def continuous_main(begin=None, end=None, only_first=False):
    numbers = list(diff_remote_and_local_index())
    if begin and end:  # 開始と終了区間の設定
        numbers = [x for x in numbers if begin <= x <= end]
    elif begin:  # 開始のみ設定
        numbers = [x for x in numbers if begin <= x]

    if only_first:  # 最初の1つのRFCのみ選択
        numbers = numbers[0:1]

    for rfc_number in numbers:
        # res = main(rfc_number, transmode)
        res = main(rfc_number)
        if res is False:
            break

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rfc', type=str, help='RFC number')
    parser.add_argument('--fetch', action='store_true', help='only fetch RFC')
    parser.add_argument('--trans', action='store_true', help='only translate')
    parser.add_argument('--make', action='store_true', help='only make HTML')
    parser.add_argument('--make-json', action='store_true', help='make JSON from HTML')
    parser.add_argument('--begin', type=int, help='begin rfc number')
    parser.add_argument('--end', type=int, help='end rfc number')
    parser.add_argument('--make-index', dest='make_index',
                        action='store_true', help='make index.html')
    parser.add_argument('--transtest', action='store_true')
    parser.add_argument('--force', '-f', action='store_true')
    # parser.add_argument('--transmode', type=str)
    parser.add_argument('--only-first', action='store_true')
    args = parser.parse_args()

    # RFCの指定（複数の場合はカンマ区切り）
    RFCs = None
    if args.rfc:
        RFCs = [int(rfc_number) for rfc_number in args.rfc.split(",")]

    # # 翻訳ツールの選択：デフォルトはSelenium+Google翻訳
    # transmode = TransMode.SELENIUM_GOOGLE
    # if args.transmode == 'py-googletrans':
    #     transmode = TransMode.PY_GOOGLETRANS

    if args.make_index:
        # トップページ(index.html)の作成
        print("[+] index.htmlの作成")
        make_index()
    elif args.transtest:
        # 翻訳のテスト
        from src.trans_rfc import trans_test
        # res = trans_test(transmode)
        print('Translate test result:', res)
    elif args.fetch and args.begin and args.end:
        # 範囲指定でRFCの取得
        print("[+] RFC %d - %d のRFCを取得" % (args.begin, args.end))
        numbers = list(diff_remote_and_local_index())
        numbers = [x for x in numbers if args.begin <= x <= args.end]
        for rfc_number in numbers:
            fetch_rfc(rfc_number)
    elif args.fetch and RFCs:
        # 指定したRFCの取得
        print("[+] RFC %d を取得")
        for rfc in RFCs:
            fetch_rfc(rfc, args.force)
    elif args.trans and RFCs:
        # RFCの翻訳
        print("[+] RFC %d を翻訳")
        for rfc in RFCs:
            # trans_rfc(rfc, transmode)
            trans_rfc(rfc)
    elif args.make and args.begin and args.end:
        # 範囲指定でRFCのHTML(rfcXXXX.html)を作成
        print("[+] RFC %d - %d のHTMLを生成" % (args.begin, args.end))
        for rfc_number in range(args.begin, args.end):
            make_html(rfc_number)
    elif args.make and RFCs:
        # 指定したRFCのHTML(rfcXXXX.html)を作成
        for rfc in RFCs:
            make_html(rfc)
    elif args.make_json and RFCs:
        # 指定したRFCのJSONを翻訳修正したHTMLから逆作成
        for rfc in RFCs:
            make_json_from_html(rfc)

    elif RFCs:
        # 範囲指定でRFCを順番に取得・翻訳・作成
        for rfc in RFCs:
            #main(rfc, transmode)
            main(rfc)
    else:
        # 未翻訳のRFCを順番に取得・翻訳・作成
        # continuous_main(transmode, begin=args.begin, end=args.end, 
        #                 only_first=args.only_first)
        continuous_main(begin=args.begin, end=args.end, 
                        only_first=args.only_first)

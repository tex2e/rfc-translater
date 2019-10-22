
import sys
from src.fetch_rfc import fetch_rfc, RFCNotFound
from src.trans_rfc import trans_rfc
from src.make_html import make_html
from src.make_index import make_index
from src.fetch_index import diff_remote_and_local_index

def main(rfc_number, trans_mode=None):
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

    res = trans_rfc(rfc_number, mode=trans_mode)
    if res is False: return False
    make_html(rfc_number)

def continuous_main(begin=None, end=None, trans_mode=None):
    numbers = list(diff_remote_and_local_index())
    if begin and end: # 開始と終了区間の設定
        numbers = [x for x in numbers if begin <= x <= end]

    for rfc_number in numbers:
        res = main(rfc_number, trans_mode=trans_mode)
        if res is False: break

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--rfc', type=int, help='RFC number')
    parser.add_argument('--fetch', action='store_true', help='only fetch RFC')
    parser.add_argument('--trans', action='store_true', help='only translate')
    parser.add_argument('--make', action='store_true', help='only make HTML')
    parser.add_argument('--begin', type=int, help='begin rfc number')
    parser.add_argument('--end', type=int, help='end rfc number')
    parser.add_argument('--trans-mode', dest='trans_mode',
        choices=['selenium', 'googletrans'], default='selenium')
    parser.add_argument('--make-index', dest='make_index',
        action='store_true', help='make index.html')
    args = parser.parse_args()

    if args.make_index:
        make_index()
        sys.exit(0)

    if args.fetch and args.rfc:
        fetch_rfc(args.rfc)
    elif args.trans and args.rfc:
        trans_rfc(args.rfc, mode=trans_mode)
    elif args.make and args.begin and args.end:
        for rfc_number in range(args.begin, args.end):
            make_html(rfc_number)
    elif args.make and args.rfc:
        make_html(args.rfc)

    elif args.rfc:
        main(args.rfc, trans_mode=args.trans_mode)
    else:
        continuous_main(begin=args.begin, end=args.end,
            trans_mode=args.trans_mode)

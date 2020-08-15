
import sys
from src.fetch_rfc import fetch_rfc, RFCNotFound
from src.trans_rfc import trans_rfc
from src.make_html import make_html
from src.make_index import make_index
from src.fetch_index import diff_remote_and_local_index


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

    res = trans_rfc(rfc_number)
    if res is False: return False
    make_html(rfc_number)

def continuous_main(begin=None, end=None):
    numbers = list(diff_remote_and_local_index())
    if begin and end:  # 開始と終了区間の設定
        numbers = [x for x in numbers if begin <= x <= end]

    for rfc_number in numbers:
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
    parser.add_argument('--begin', type=int, help='begin rfc number')
    parser.add_argument('--end', type=int, help='end rfc number')
    parser.add_argument('--make-index', dest='make_index',
                        action='store_true', help='make index.html')
    parser.add_argument('--transtest', action='store_true')
    parser.add_argument('--force', '-f', action='store_true')
    args = parser.parse_args()

    RFCs = None
    if args.rfc:
        RFCs = [int(rfc_number) for rfc_number in args.rfc.split(",")]

    if args.make_index:
        make_index()
    elif args.transtest:
        from src.trans_rfc import trans_test
        trans_test()
    elif args.fetch and args.begin and args.end:
        numbers = list(diff_remote_and_local_index())
        numbers = [x for x in numbers if args.begin <= x <= args.end]
        for rfc_number in numbers:
            fetch_rfc(rfc_number)
    elif args.fetch and RFCs:
        for rfc in RFCs:
            fetch_rfc(rfc, args.force)
    elif args.trans and RFCs:
        for rfc in RFCs:
            trans_rfc(rfc)
    elif args.make and args.begin and args.end:
        for rfc_number in range(args.begin, args.end):
            make_html(rfc_number)
    elif args.make and RFCs:
        for rfc in RFCs:
            make_html(rfc)

    elif RFCs:
        for rfc in RFCs:
            main(rfc)
    else:
        continuous_main(begin=args.begin, end=args.end)

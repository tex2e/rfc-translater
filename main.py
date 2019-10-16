
import sys
from src.fetch_rfc import fetch_rfc
from src.trans_rfc import trans_rfc
from src.make_html import make_html

def main(rfc_number):
    fetch_rfc(rfc_number)
    trans_rfc(rfc_number)
    make_html(rfc_number)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_number', type=int)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--trans', action='store_true')
    parser.add_argument('--make', action='store_true')
    args = parser.parse_args()

    rfc_number = args.rfc_number
    if args.fetch:
        fetch_rfc(rfc_number)
        sys.exit()
    if args.trans:
        trans_rfc(rfc_number)
        sys.exit()
    if args.make:
        make_html(rfc_number)
        sys.exit()

    main(rfc_number)

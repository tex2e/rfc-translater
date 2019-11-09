
import os
import re
import json
import textwrap
import argparse
from collections import Counter

FIGURES_FILE = 'figs/figures.json'

def is_table(text):
    ignore_table_pattern = re.compile(r'^\s*((?:\+-+)+\+)', re.MULTILINE)
    res = Counter(ignore_table_pattern.findall(text)).most_common(1)
    if len(res) == 1:
        count = res[0][1]
        return count >= 3
    return False

def collect_figures(rfc_number):
    input_dir = 'data/%04d' % (rfc_number//1000%10*1000)
    input_file = '%s/rfc%d-trans.json' % (input_dir, rfc_number)
    if not os.path.isfile(input_file):
        input_file = '%s/rfc%d.json' % (input_dir, rfc_number)
    if not os.path.isfile(input_file):
        print('file not found: rfc %d' % rfc_number)
        return

    with open(input_file, 'r') as f:
        obj = json.load(f)

    fig_pattern = re.compile(r'__|<---|--->|[+|]--|--[+|]|/\||\|\\|\|\s+\|')
    packet_pattern = re.compile(r'\+-\+-\+-\+-\+-\+-\+-\+')
    sym_pattern = re.compile(r'[-+*/%=#?!_./\\(){}\[\] ]')
    alphanum_pattern = re.compile(r'[a-zA-Z0-9]')

    figs = []
    prev_fig_i = -10
    for i, paragraph in enumerate(obj['contents']):
        text = paragraph['text']
        if (paragraph.get('raw') == True
            and (re.search(fig_pattern, text) # 図の特有のパターンが含まれている
                 and not re.search(packet_pattern, text) # パケット図ではない
                 and not is_table(text) # 表のときは、図と見なさない
                 and sum(map(len, text.split())) >= 60 # 文字数が60以上のとき
                 )
            # 記号数より文字数が多いときは、図と見なさない
            and len(sym_pattern.findall(text)) > len(alphanum_pattern.findall(text))
            ):
            # then
            text = textwrap.indent(paragraph['text'], " " * paragraph['indent']).rstrip()
            if i - 1 == prev_fig_i:
                figs[-1]['text'] += '\n\n' + text.lstrip('\n')
            else:
                figs.append({ 'rfc': rfc_number, 'text': text })
            prev_fig_i = i
    return figs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--rfc', type=int)
    parser.add_argument('--begin', type=int)
    parser.add_argument('--end', type=int)
    parser.add_argument('--write', '-w')
    parser.add_argument('--quiet', '-q', action='store_true', default=False)
    parser.add_argument('--notwrite', '-n', action='store_true', default=False)
    args = parser.parse_args()

    figures_file = args.write

    data = []
    if args.write and os.path.isfile(figures_file):
        with open(figures_file) as f:
            data = json.load(f)

    if args.rfc:
        begin = args.rfc
        end   = args.rfc
    elif args.begin and args.end:
        begin = args.begin
        end   = args.end

    for rfc_number in range(begin, end+1):
        figs = collect_figures(rfc_number)
        if figs is None:
            continue
        if not args.quiet:
            for fig in figs:
                print('RFC %s\n%s\n' % (fig['rfc'], fig['text']))
        data += figs

    if args.write:
        with open(figures_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

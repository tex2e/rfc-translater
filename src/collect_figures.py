
import os
import json
import textwrap

def collect_figures(rfc_number):
    input_dir = 'data/%04d/%03d' % (rfc_number//1000%10*1000, rfc_number//100%10*100)
    input_file = '%s/rfc%d-trans.json' % (input_dir, rfc_number)
    if not os.path.isfile(input_file):
        input_file = '%s/rfc%d.json' % (input_dir, rfc_number)
    if not os.path.isfile(input_file):
        print('file not found: rfc %d' % rfc_number)

    with open(input_file, 'r') as f:
        obj = json.load(f)

    figs = []
    for paragraph in obj['contents']:
        if paragraph.get('raw') == True:
            text = textwrap.indent(paragraph['text'], " " * paragraph['indent'])
            figs.append(text)
    return figs


if __name__ == '__main__':
    figs = collect_figures(2)
    for fig in figs:
        print(fig)

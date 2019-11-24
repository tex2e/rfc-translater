
import os
import json
from mako.template import Template
from mako.lookup import TemplateLookup
import glob
import re

def make_index():
    output_file = 'figs/html/index.html'

    ary = []
    for filepath in sorted(glob.glob('figs/html/*000.html')):
        m = re.match(r'html/((\d+)\.html)', filepath)
        if m:
            filename  = m[1]
            rfc_begin = int(m[2])
            rfc_end   = rfc_begin + 999
            ary.append((filename, rfc_begin, rfc_end))

    mylookup = TemplateLookup(
        directories=["./"],
        input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template('figs/templates/index.html')
    output = mytemplate.render_unicode(ctx=ary)

    with open(output_file, 'w') as f:
        f.write(output)


if __name__ == '__main__':
    # import argparse
    # parser = argparse.ArgumentParser()
    # parser.add_argument('rfc_number', type=int)
    # args = parser.parse_args()

    make_index()

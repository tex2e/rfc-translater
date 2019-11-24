
import os
import json
from mako.template import Template
from mako.lookup import TemplateLookup

def make_html(rfc_number):
    rfc_number -= rfc_number % 1000
    input_file  = 'figs/data/%04d.json' % rfc_number
    output_file = 'figs/html/%04d.html' % rfc_number

    if not os.path.isfile(input_file):
        print("make_html: Not found:", input_file)
        return

    with open(input_file, 'r') as f:
        figs = json.load(f)

    # print(figs)
    obj = {}
    obj['figs'] = figs
    obj['range'] = '{}-{}'.format(rfc_number, rfc_number + 999)

    mylookup = TemplateLookup(
        directories=["./"],
        input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template('figs/templates/page.html')
    output = mytemplate.render_unicode(ctx=obj)

    with open(output_file, 'w') as f:
        f.write(output)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_number', type=int)
    args = parser.parse_args()

    make_html(args.rfc_number)

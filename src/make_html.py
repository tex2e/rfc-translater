
import os
import json
from mako.template import Template
from mako.lookup import TemplateLookup

def make_html(rfc_number):
    input_dir = 'data/%04d/%03d' % (round(rfc_number, -3), round(rfc_number, -2))
    input_file = '%s/rfc%d-trans.json' % (input_dir, rfc_number)
    output_dir = 'html'
    output_file = '%s/rfc%d.html' % (output_dir, rfc_number)

    with open(input_file, 'r') as f:
        obj = json.load(f)

    mylookup = TemplateLookup(
        directories=["./"],
        input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template('templates/rfc.html')
    output = mytemplate.render_unicode(ctx=obj)

    os.makedirs(output_dir, exist_ok=True)

    with open(output_file, 'w') as f:
        f.write(output)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('rfc_number', type=int)
    args = parser.parse_args()

    make_html(args.rfc_number)

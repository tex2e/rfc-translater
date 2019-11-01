
# python src/make_index.py

import re
import glob
from mako.template import Template
from mako.lookup import TemplateLookup

def make_index():
    output_file = 'html/index.html'

    files = []
    for filename in glob.glob('html/rfc*.html'):
        rfcfile = re.sub(r'^html/', '', filename)
        with open(filename) as f:
            html = f.read()
        m = re.search(r'<title>([^<]*)</title>', html)
        title = m[1].replace('日本語訳', '').strip()
        m = re.match(r'rfc(\d+).html', rfcfile)
        if m:
            filenum = int(m[1])
            files.append((filenum, rfcfile, title))

    files.sort()

    mylookup = TemplateLookup(
        directories=["./"],
        input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template('templates/index.html')
    output = mytemplate.render_unicode(ctx={ 'files': files })

    with open(output_file, 'w') as f:
        f.write(output)


if __name__ == '__main__':
    make_index()

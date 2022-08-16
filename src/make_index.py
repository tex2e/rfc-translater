
import os
import re
import glob
# from mako.template import Template
from mako.lookup import TemplateLookup

def make_index() -> None:
    output_file = os.path.normpath('html/index.html')

    files = []
    for filename in glob.glob('html/rfc*.html'):
        rfcfile = re.sub(r'^html[/\\]', '', filename)
        with open(filename, 'r', encoding="utf-8") as f:
            html = f.read()
        m = re.search(r'<title>([^<]*)</title>', html)
        if not m:
            print("not found title: %s" % filename)
            continue
        title = m[1].replace('日本語訳', '').strip()
        m = re.match(r'rfc(\d+).html', rfcfile)
        if m:
            filenum = int(m[1])
            if filenum < 2220:  # RFC 2220 以降を対象とする
                continue
            files.append((filenum, rfcfile, title))

    files.sort(reverse=True)

    mylookup = TemplateLookup(
        directories=["./"],
        input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template('templates/index.html')
    output = mytemplate.render_unicode(ctx={'files': files})

    with open(output_file, 'w', encoding="utf-8", newline="\n") as f:
        f.write(output)


def make_index_draft() -> None:
    output_file = os.path.normpath('html/draft/index.html')
    is_draft = True

    files = []
    for filename in glob.glob('html/draft/draft-*.html'):
        rfcfile = re.sub(r'^html[/\\]draft[/\\]', '', filename)
        with open(filename, 'r', encoding="utf-8") as f:
            html = f.read()
        m = re.search(r'<title>([^<]*)</title>', html)
        if not m:
            print("not found title: %s" % filename)
            continue
        title = m[1].replace('日本語訳', '').strip()
        m = re.match(r'draft-[^-]+-(?P<draftname>.*).html', rfcfile)
        if m:
            filenum = m['draftname']
            files.append((filenum, rfcfile, title))

    files.sort()

    mylookup = TemplateLookup(
        directories=["./"],
        input_encoding='utf-8', output_encoding='utf-8')
    mytemplate = mylookup.get_template('templates/index.html')
    output = mytemplate.render_unicode(ctx={'files': files}, is_draft=is_draft)

    with open(output_file, 'w', encoding="utf-8", newline="\n") as f:
        f.write(output)


if __name__ == '__main__':
    make_index()

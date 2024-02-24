
# Copyright The IETF Trust 2018, All Rights Reserved
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function, division

import sys
import lxml.etree

# https://github.com/ietf-tools/xml2rfc/blob/main/xml2rfc/writers/text.py

################################################################################

import base64
import re
import six
import sys
import textwrap
from collections import OrderedDict
from lxml.etree import _Comment, _ProcessingInstruction

from urllib.request import quote

# ----------------------------------------------------------------------
# Text wrapping

class TextWrapper(textwrap.TextWrapper):
    """ Subclass that overrides a few things in the standard implementation """
    def __init__(self, **kwargs):
        textwrap.TextWrapper.__init__(self, **kwargs)

        # Override wrapping regex, preserve '/' before linebreak
        self.wordsep_re = re.compile(
            u'('
            u'[ \t\n\r\f\v]+|'                                  # any ASCII whitespace
            u'[^\\s-]*\\w+/(?=[A-Za-z]\\w*)|'                   # forward-slash separated words
            u'[^\\s-]*\\w+[^0-9\\s]-(?=\\w+[^0-9\\s])|'         # hyphenated words
            u'\u200b|'                                          # &zwsp; zero-width space is breakable space
            u'''(?<=[\\w\\!"'\\&\\.\\,\\?])-{2,}(?=\\w))'''     # em-dash
            u'(?![\u00A0|\u2060|\uE060])')                      # UNLESS &nbsp; or &wj;

        self.wordsep_re_uni = re.compile(self.wordsep_re.pattern, re.U)

        # Override end of line regex, double space after '].'
        self.sentence_end_re = re.compile(r'[A-Za-z0-9\>\]\)\"\']'  # letter, end parentheses
                            r'[\.\!\?]'     # sentence-ending punct.
                            r'[\"\'\)\]]?'  # optional end-of-quote, end parentheses
                            r'\Z'           # end of chunk
                            )

        # Exceptions which should not be treated like end-of-sentence
        self.not_sentence_end_re = re.compile(
            # start of string or non-alpha character
            r'(^|\s)'
            r'('
            # Single uppercase letter, dot, enclosing parentheses or quotes
            r'\.[\]\)\'"]*'
            # Tla with leading uppercase, and special cases
            # (Note: v1 spelled out Fig, Tbl, Mrs, Drs, Rep, Sen, Gov, Rev, Gen, Col, Maj and Cap,
            #  but those are redundant with the Tla regex.)
            r'|([A-Z][a-z][a-z]|Eq|[Cc]f|vs|resp|viz|ibid|[JS]r|M[rs]|Messrs|Mmes|Dr|Profs?|St|Lt|i\.e)\.'
            r')\Z' # trailing dot, end of group and end of chunk
            )

        # Start of next sentence regex
        self.sentence_start_re = re.compile("^[\"'([]*[A-Z]")

    def _fix_sentence_endings(self, chunks):
        """_fix_sentence_endings(chunks : [string])

        Correct for sentence endings buried in 'chunks'.  Eg. when the
        original text contains "... foo.\nBar ...", munge_whitespace()
        and split() will convert that to [..., "foo.", " ", "Bar", ...]
        which has one too few spaces; this method simply changes the one
        space to two.
        """
        i = 0
        patsearch = self.sentence_end_re.search
        skipsearch = self.not_sentence_end_re.search
        startsearch = self.sentence_start_re.search
        while i < len(chunks)-2:
            if (chunks[i+1] == " " and patsearch(chunks[i])
                                  and skipsearch(chunks[i])==None
                                  and startsearch(chunks[i+2])):
                chunks[i+1] = "  "
                i += 2
            else:
                i += 1

    def wrap(self, text, initial='', subsequent_indent=None, width=None,
        fix_doublespace=True, fix_sentence_endings=True, drop_whitespace=True):
        """ Mirrored implementation of wrap which replaces characters properly
            and also lets you easily specify indentation on the fly
        """
        # Handle U+2028 LINE SEPARATOR by recursing
        if '\u2028' in text:
            parts = text.split('\u2028')
            wrapped = []
            for part in parts:
                part = part.lstrip()
                if part:
                    wrapped += self.wrap(part, initial=initial, subsequent_indent=subsequent_indent,
                                    width=width, fix_doublespace=fix_doublespace,
                                    fix_sentence_endings=fix_sentence_endings,
                                    drop_whitespace=drop_whitespace)
                else:
                    wrapped.append(part)
                initial = ''
            return wrapped

        # Set indentation
        _width = self.width
        if width != None:
            self.width = width
        self.initial_indent = initial
        if subsequent_indent == None:
            self.subsequent_indent = initial
        else:
            self.subsequent_indent = subsequent_indent
        self.fix_sentence_endings = fix_sentence_endings
        self.drop_whitespace = drop_whitespace

        # --- Original implementation ----------------------------------
        text = self._munge_whitespace(text)
        # --- End original implementation ------------------------------

        # Maybe remove double (and more) spaces, except when they might be between sentences
        if fix_doublespace:
            text = re.sub("([^.!?])  +", r"\1 ", text)
            text = re.sub("([.!?])   +", r"\1  ", text)

        # prevent breaking "Section N.N" and "Appendix X.X"
        text = re.sub("(Section|Appendix|Figure|Table) ", u"\\1\u00A0", text)

        # Replace some characters after splitting has occurred
        # --- Original implementation ----------------------------------
        chunks = self._split(text)
        # --- End original implementation ------------------------------

        parts = chunks
        chunks = []
        max_word_len = self.width - len(self.subsequent_indent)
        for chunk in parts:
            # remove zero-width characters before looking at length
            chunk2 = re.sub('[\u200B\u200C\u2060\uE060]', '', chunk)
            if len(chunk2) > max_word_len:
                # No use trying not to break when we have a chunk longer
                # than available horizontal space.  Remove wj and nbsp and
                # try again.
                chunk2 = re.sub('[\u2060\uE060]', '', chunk).replace('\u00A0', ' ')
                bits = self._split(chunk2)
                for bit in bits:
                    chunk3 = re.sub('[\u2060\uE060]', '', bit).replace('\u00A0', ' ')
                    if len(chunk3) > max_word_len:
                        chunks += self._split(chunk3)
                    else:
                        chunks += [ chunk3 ]
            else:
                chunks += [ chunk2 ]

        # --- Original implementation ----------------------------------
        if self.fix_sentence_endings:
            self._fix_sentence_endings(chunks)
        wrapped = self._wrap_chunks(chunks)
        # --- End original implementation ------------------------------

        self.width = _width
        for i, chunk in enumerate(wrapped):
            wrapped[i] = chunk.replace(u'\uE060', '')
        return wrapped

    def fill(self, *args, **kwargs):
        kwargs.pop('fill', None)
        return "\u2028".join(self.wrap(*args, **kwargs))


class TextSplitter(textwrap.TextWrapper):
    """ Subclass that overrides a few things in the standard implementation """
    def __init__(self, **kwargs):
        hyphen_split = kwargs.pop('hyphen_split', False)
        textwrap.TextWrapper.__init__(self, **kwargs)

        # Override wrapping regex, preserve '/' before linebreak
        if hyphen_split:
            self.wordsep_re = re.compile(
                u'('
                u'[ \t\n\r\f\v]+|'                                  # any ASCII whitespace
                u'[^\\s-]*\\w+/(?=[A-Za-z]\\w*)|'                   # forward-slash separated words
                u'\u200b|'                                          # &zwsp; zero-width space is breakable space
                u'\u2028|'                                          # &br; unicode 'line separator'
                u'[^\\s-]*\\w+[^0-9\\s]-(?=\\w+)|'                  # hyphenated words
                u'''(?<=[\\w\\!"'\\&\\.\\,\\?])-{2,}(?=\\w))'''     # em-dash
                u'(?![\u00A0|\u2060|\uE060])')                      # UNLESS &nbsp; or &wj;
        else:
            self.wordsep_re = re.compile(
                u'('
                u'[ \t\n\r\f\v]+|'                                  # any ASCII whitespace
                u'[^\\s-]*\\w+/(?=[A-Za-z]\\w*)|'                   # forward-slash separated words
                u'\u200b|'                                          # &zwsp; zero-width space is breakable space
                u'\u2028|'                                          # &br; unicode 'line separator'
                u'''(?<=[\\w\\!"'\\&\\.\\,\\?])-{2,}(?=\\w))'''     # em-dash
                u'(?![\u00A0|\u2060|\uE060])')                      # UNLESS &nbsp; or &wj;

        self.wordsep_re_uni = re.compile(self.wordsep_re.pattern, re.U)


def justify_inline(left_str, center_str, right_str, width=72):
    """ Takes three string arguments and outputs a single string with the
        arguments left-justified, centered, and right-justified respectively.

        Raises a warning if the combined length of the three strings is
        greater than the width, and trims the longest string
    """
    strings = [left_str.rstrip(), center_str.strip(), right_str.strip()]
    sumwidth = sum( [len(s) for s in strings] )
    if sumwidth > width:
        # Trim longest string
        longest_index = strings.index(max(strings, key=len))
        # xml2rfc.log.warn('The inline string was truncated because it was ' \
        #                  'too long:\n  ' + strings[longest_index])
        strings[longest_index] = strings[longest_index][:-(sumwidth - width)]

    if len(strings[1]) % 2 == 0:
        center = strings[1].center(width)
    else:
        center = strings[1].center(width+1)
    right = strings[2].rjust(width)
    output = list(strings[0].ljust(width))
    for i, char in enumerate(output):
        if center[i] != ' ':
            output[i] = center[i]
        elif right[i] != ' ':
            output[i] = right[i]
    return ''.join(output)

# ----------------------------------------------------------------------
# Other text operations


def ascii_split(text):
    """ We have unicode strings, but we want to split only on the ASCII
        whitespace characters so that nbsp does not get split.
    """

    if isinstance(text, type('')):
        return text.split()
    return re.split("[ \t\n\r\f\v]+", text)


def urlkeep(text, max=72):
    """ Insert word join XML entities on forward slashes and hyphens
        in a URL so that it stays on one line
    """
    wj_char = u'\uE060'
    def replacer(match):
        url = match.group(0)
        if len(url) > max:
            return url
        else:
            return ( url.replace('/', '/' + wj_char)
                        .replace('-', '-' + wj_char)
                        .replace(':', ':' + wj_char)
                    )
    if 'http://' in text:
        text = re.sub(r'http:\S*', replacer, text)
    if 'https://' in text:
        text = re.sub(r'https:\S*', replacer, text)
    return text

# ----------------------------------------------------------------------
# Tree operations

def formatXmlWhitespace(tree):
    """ Traverses an lxml.etree ElementTree and properly formats whitespace

        We replace newlines with single spaces, unless it ends with a
        period then we replace the newline with two spaces.
    """
    for element in tree.iter():
        # Preserve formatting on artwork
        if element.tag != 'artwork':
            if element.text is not None:
                element.text = re.sub(r'\s*\n\s*', ' ', \
                               re.sub(r'\.\s*\n\s*', '.  ', \
                               element.text.lstrip()))

            if element.tail is not None:
                element.tail = re.sub(r'\s*\n\s*', ' ', \
                               re.sub(r'\.\s*\n\s*', '.  ', \
                               element.tail))


def safeReplaceUnicode(tree):
    """ Traverses an lxml.etree ElementTree and replaces unicode characters
        with the proper equivalents specified in rfc2629-xhtml.ent.

        Writers should call this method if the entire RFC document needs to
        be ascii formatted
    """
    for element in tree.iter():
        if element.text:
            try:
                element.text = element.text.encode('ascii')
            except UnicodeEncodeError:
                element.text = _replace_unicode_characters(element.text)
        if element.tail:
            try:
                element.tail = element.tail.encode('ascii')
            except UnicodeEncodeError:
                element.tail = _replace_unicode_characters(element.tail)
        for key in element.attrib.keys():
            try:
                element.attrib[key] = element.attrib[key].encode('ascii')
            except UnicodeEncodeError:
                element.attrib[key] = \
                _replace_unicode_characters(element.attrib[key])


def safeTagSlashedWords(tree):
    """ Traverses an lxml.etree ElementTree and replace words separated
        by slashes if they are on the list
    """
    slashList = {}
    for element in _slash_replacements:
        slashList[element] = re.sub(u'/', u'\uE060/\uE060', element)

    for element in tree.iter():
        if element.tag == 'artwork':
            continue
        if element.text:
            element.text = _replace_slashed_words(element.text, slashList)
        if element.tail:
            element.tail = _replace_slashed_words(element.tail, slashList)
        # I do not know that this makes any sense
        # for key in element.attrib.keys():
        #    element.attrib[key] = \
        #        _replace_slashed_words(element.attrib[key], slashList)


def find_duplicate_ids(schema, tree):
    # get attributes specified with data type "ID"
    id_data = schema.xpath("/x:grammar/x:define/x:element//x:attribute/x:data[@type='ID']", namespaces=namespaces)
    attr = set([ i.getparent().get('name') for i in id_data ])
    # Check them one by one
    return find_duplicate_attr_values(attr, tree)

def find_duplicate_html_ids(tree):
    return find_duplicate_attr_values(['id',], tree)

def find_duplicate_attr_values(attr, tree):
    dups = []
    # Check them one by one
    for a in attr:
        seen = set()
        for e in tree.xpath('.//*[@%s]' % a):
            id = e.get(a)
            if id != None and id in seen:
                dups.append((a, id, e))
            else:
                seen.add(id)
    return dups

# ----------------------------------------------------------------------
# Unicode operations


def _replace_unicode_characters(str):
    """ replace those Unicode characters that we do not use internally
        &wj; &zwsp; &nbsp; &nbhy;
    """
    str = str.replace('\uE060', '\u2060')
    while True:
        match = re.search(u'([^ -\x7e\u2060\u200B\u00A0\u2011\r\n])', str)
        if not match:
            return str
        if match.group(1) in _unicode_replacements:
            str = re.sub(match.group(1), _unicode_replacements[match.group(1)], str)
        else:
            entity = match.group(1).encode('ascii', 'xmlcharrefreplace').decode('ascii')
            str = re.sub(match.group(1), entity, str)
            # xml2rfc.log.warn('Illegal character replaced in string: ' + entity)


# Ascii representations of unicode chars from rfc2629-xhtml.ent
# Auto-generated from comments in rfc2629-xhtml.ent
_unicode_replacements = {
    u'\x09': ' ',
    u'\xa0': ' ',
    u'\xa1': '!',
    u'\xa2': '[cents]',
    u'\xa3': 'GBP',
    u'\xa4': '[currency units]',
    u'\xa5': 'JPY',
    u'\xa6': '|',
    u'\xa7': 'S.',
    u'\xa9': '(C)',
    u'\xaa': 'a',
    u'\xab': '<<',
    u'\xac': '[not]',
    u'\xae': '(R)',
    u'\xaf': '_',
    u'\xb0': 'o',
    u'\xb1': '+/-',
    u'\xb2': '^2',
    u'\xb3': '^3',
    u'\xb4': "'",
    u'\xb5': '[micro]',
    u'\xb6': 'P.',
    u'\xb7': '.',
    u'\xb8': ',',
    u'\xb9': '^1',
    u'\xba': 'o',
    u'\xbb': '>>',
    u'\xbc': '1/4',
    u'\xbd': '1/2',
    u'\xbe': '3/4',
    u'\xbf': '?',
    u'\xc0': 'A',
    u'\xc1': 'A',
    u'\xc2': 'A',
    u'\xc3': 'A',
    u'\xc4': 'Ae',
    u'\xc5': 'Ae',
    u'\xc6': 'AE',
    u'\xc7': 'C',
    u'\xc8': 'E',
    u'\xc9': 'E',
    u'\xca': 'E',
    u'\xcb': 'E',
    u'\xcc': 'I',
    u'\xcd': 'I',
    u'\xce': 'I',
    u'\xcf': 'I',
    u'\xd0': '[ETH]',
    u'\xd1': 'N',
    u'\xd2': 'O',
    u'\xd3': 'O',
    u'\xd4': 'O',
    u'\xd5': 'O',
    u'\xd6': 'Oe',
    u'\xd7': 'x',
    u'\xd8': 'Oe',
    u'\xd9': 'U',
    u'\xda': 'U',
    u'\xdb': 'U',
    u'\xdc': 'Ue',
    u'\xdd': 'Y',
    u'\xde': '[THORN]',
    u'\xdf': 'ss',
    u'\xe0': 'a',
    u'\xe1': 'a',
    u'\xe2': 'a',
    u'\xe3': 'a',
    u'\xe4': 'ae',
    u'\xe5': 'ae',
    u'\xe6': 'ae',
    u'\xe7': 'c',
    u'\xe8': 'e',
    u'\xe9': 'e',
    u'\xea': 'e',
    u'\xeb': 'e',
    u'\xec': 'i',
    u'\xed': 'i',
    u'\xee': 'i',
    u'\xef': 'i',
    u'\xf0': '[eth]',
    u'\xf1': 'n',
    u'\xf2': 'o',
    u'\xf3': 'o',
    u'\xf4': 'o',
    u'\xf5': 'o',
    u'\xf6': 'oe',
    u'\xf7': '/',
    u'\xf8': 'oe',
    u'\xf9': 'u',
    u'\xfa': 'u',
    u'\xfb': 'u',
    u'\xfc': 'ue',
    u'\xfd': 'y',
    u'\xfe': '[thorn]',
    u'\xff': 'y',
    u'\u0152': 'OE',
    u'\u0153': 'oe',
    u'\u0161': 's',
    u'\u0178': 'Y',
    u'\u0192': 'f',
    u'\u02dc': '~',
    u'\u2002': ' ',
    u'\u2003': ' ',
    u'\u2009': ' ',
    u'\u2013': '-',
    u'\u2014': u'-\u002D',
    u'\u2018': "'",
    u'\u2019': "'",
    u'\u201a': "'",
    u'\u201c': '"',
    u'\u201d': '"',
    u'\u201e': '"',
    u'\u2020': '*!*',
    u'\u2021': '*!!*',
    u'\u2022': 'o',
    u'\u2026': '...',
    u'\u2030': '[/1000]',
    u'\u2032': "'",
    u'\u2039': '<',
    u'\u203a': '>',
    u'\u2044': '/',
    u'\u20ac': 'EUR',
    u'\u2122': '[TM]',
    u'\u2190': '<-\u002D',
    u'\u2192': '\u002D->',
    u'\u2194': '<->',
    u'\u21d0': '<==',
    u'\u21d2': '==>',
    u'\u21d4': '<=>',
    u'\u2212': '-',
    u'\u2217': '*',
    u'\u2264': '<=',
    u'\u2265': '>=',
    u'\u2329': '<',
    u'\u232a': '>',

    # rfc2629-other.ent
    u'\u0021': '!',
    u'\u0023': '#',
    u'\u0024': '$',
    u'\u0025': '%',
    u'\u0028': '(',
    u'\u0029': ')',
    u'\u002a': '*',
    u'\u002b': '+',
    u'\u002c': ',',
    u'\u002d': '-',
    u'\u002e': '.',
    u'\u002f': '/',
    u'\u003a': ':',
    u'\u003b': ';',
    u'\u003d': '=',
    u'\u003f': '?',
    u'\u0040': '@',
    u'\u005b': '[',
    u'\u005d': ']',
    u'\u005e': '^',
    u'\u005f': '_',
    u'\u0060': '`',
    u'\u007b': '{',
    u'\u007c': '|',
    u'\u007d': '}',
    u'\u017d': 'Z',
    u'\u017e': 'z',
    u'\u2010': '-',
}

def parse_pi(pi, pis):
    """ Add a processing instruction to the current state

        Will also return the dictionary containing the added instructions
        for use in things like ?include instructions
    """
    if pi.text:
        # Split text in the format 'key="val"'
        chunks = re.split(r'=[\'"]([^\'"]*)[\'"]', pi.text)
        # Create pairs from this flat list, discard last element if odd
        tmp_dict = dict(zip(chunks[::2], chunks[1::2]))
        for key, val in tmp_dict.items():
            # Update main PI state
            pis[key] = val
        # Return the new values added
        return tmp_dict
    return {}


def _replace_slashed_words(str, slashList):
    """ replace slashed separated words the list with
        <word1> &nbsp; / &nbsp; <word 2>
    """
    match = re.findall(r'(\w+(/\w+)+)', str)
    for item in match:
        if item[0] in slashList:
            str = re.sub(item[0], slashList[item[0]], str)
    return str


_slash_replacements = [
    u'PDF/A',
    u'PDF/UA',
    u'PDF/VT',
    u'S/MIME',
    # If you remove me the regression test fails
    u'this/is/a/long/test',
]

def build_dataurl(mime, data, base64enc=False):
    if base64enc:
        data = quote(base64.b64encode(data), safe='/~')
        url = "data:%s;base64,%s" % (mime, data)
    else:
        data = quote(data, safe='/~')
        url = "data:%s,%s" % (mime, data)
    return url

namespaces={
    'x':    'http://relaxng.org/ns/structure/1.0',
    'a':    'http://relaxng.org/ns/compatibility/annotations/1.0',
    'xi':   'http://www.w3.org/2001/XInclude',
    'svg':  'http://www.w3.org/2000/svg',
    'xml':  'http://www.w3.org/XML/1998/namespace',
    'xlink':'http://www.w3.org/1999/xlink',
}


def sdict(d):
    "Create an ordered dict from the given dict, with sorted initial insertion"
    # For python 3.6 and later, lxml obeys dictionary insertion order for
    # attributes, for earlier it sorts initial attributes, so we need to
    # use a regular dict for 3.6 and later
    if sys.version_info.major == 3 and sys.version_info.minor >= 6:
        return dict( (k, d[k]) for k in sorted(list(d.keys())) )
    else:
        if isinstance(d, OrderedDict):
            return d
        return OrderedDict( (k, d[k]) for k in sorted(list(d.keys())) )

# ----------------------------------------------------------------------
# Element operations


def isempty(e):
    "Return True if e has no children and no text content"
    return not (len(e) or (e.text and e.text.strip()) or (e.tail and e.tail.strip()))

def isblock(e):
    "Return True if e is a block level element"
    # from xml2rfc.writers.base import block_tags
    # return e.tag in block_tags
    # block_tags  = element_tags - inline_tags - deprecated_element_tags - set(['t'])
    block_tags  = element_tags - inline_tags - set(['t'])
    return e.tag in block_tags

def iscomment(e):
    "Return True if e is a comment or PI"
    return isinstance(e, (_Comment, _ProcessingInstruction))

def hastext(e, ignore=[]):
    "Return a list of text-level immediate children"
    head = [ e.text ] if e.text and e.text.strip() else []
    ignore = set(ignore + ['t'])
    items = ( head + [ c for c in e.iterchildren() if not (isblock(c) or iscomment(c) or (c.tag in ignore))]
                   + [ c.tail for c in e.iterchildren() if c.tail and c.tail.strip() ] )
    return items

def clean_text(s):
    """Replace internal use code points and various other special code points with plain equivalents"""
    # spaces
    s = re.sub(r'[\u00a0\u2028]', ' ', s)
    # hyphens
    s = s.replace(r'\u2011', '-')
    # zero-width
    s = re.sub(r'[\u200B\u2060\ue060]', '', s)
    return s.strip()

def is_htmlblock(h):
    return h.tag in set([ 'address', 'article', 'aside', 'blockquote', 'div', 'dl', 'figure',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'nav', 'ol', 'p', 'pre', 'script', 'section',
        'table', 'ul', ])

def slugify(s):
    s = s.strip().lower()
    s = re.sub(r'[^\w\s/|@=-]', '', s)
    s = re.sub(r'[-_\s/|@=]+', '_', s)
    s = s.strip('_')
    return s



import os
import lxml.etree
v3_rng_file = os.path.join(os.path.dirname(__file__), 'v3.rng')
v3_schema = lxml.etree.ElementTree(file=v3_rng_file)

def get_element_tags():
    tags = set()
    elements = v3_schema.xpath("/x:grammar/x:define/x:element", namespaces=namespaces)
    for element in elements:
        name = element.get('name')
        if not name in tags:
            tags.add(name)
    return tags

def get_inline_tags():
    "Get tags that can occur within text from the schema"
    tags = set()
    referenced = v3_schema.xpath("/x:grammar/x:define/x:element//x:ref", namespaces=namespaces)
    for ref in referenced:
        name = ref.get('name')
        if not name in tags:
            p = ref.getparent()
            text = p.find('x:text', namespaces=namespaces)
            if text != None:
                tags.add(name)
    return tags

element_tags = get_element_tags()
all_inline_tags = get_inline_tags()
inline_tags = all_inline_tags


################################################################################


from argparse import Namespace
default_options = Namespace()
default_options.__dict__ = {
        'accept_prepped': None,
        'add_xinclude': None,
        'allow_local_file_access': False,
        'basename': None,
        'bom': False,
        'cache': None,
        # 'clear_cache': False,
        # 'css': None,
        # 'config_file': None,
        # 'country_help': False,
        # 'date': None,
        # 'datestring': None,
        'debug': False,
        # 'docfile': False,
        # 'doc_template': None,
        # 'doi_base_url': 'https://doi.org/',
        # 'draft_revisions': False,
        # 'dtd': None,
        # 'expand': False,
        # 'external_css': False,
        # 'external_js': False,
        # 'filename': None,
        # 'first_page_author_org': True,
        # 'html': False,
        # 'id_base_url': 'https://datatracker.ietf.org/doc/html/',
        # 'id_reference_base_url': 'https://datatracker.ietf.org/doc/html/',
        # 'id_is_work_in_progress': True,
        # 'image_svg': False,
        'indent': 2,
        # 'info': False,
        # 'info_base_url': 'https://www.rfc-editor.org/info/',
        # 'inline_version_info': True,
        # 'legacy': False,
        # 'legacy_date_format': False,
        # 'legacy_list_symbols': False,
        # 'list_symbols': ('*', '-', 'o', '+'),
        # 'manpage': False,
        # 'metadata_js_url': 'metadata.min.js',
        # 'no_css': False,
        # 'no_dtd': None,
        'no_network': False,
        'nroff': False,
        'omit_headers': None,
        'orphans': 2,
        # 'output_filename': None,
        # 'output_path': None,
        # 'pagination': True,
        # 'pi_help': False,
        # 'pdf': False,
        # 'pdf_help': False,
        # 'preptool': False,
        # 'quiet': False,
        'remove_pis': False,
        'raw': False,
        'rfc': None,
        'rfc_base_url': 'https://www.rfc-editor.org/rfc/',
        'rfc_local': True,
        'rfc_reference_base_url': 'https://rfc-editor.org/rfc/',
        # 'silence': default_silenced_messages,
        # 'skip_config_files': False,
        'source': None,
        'strict': False,
        'table_hyphen_breaks': False,
        'table_borders': 'full',
        # 'template_dir': os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates'),
        'text': True,
        'unprep': False,
        'utf8': False,
        'values': False,
        'verbose': False,
        'version': False,
        'v2v3': False,
        'v3': True,
        'vocabulary': 'v2',
        'widows': 2,
        'warn_bare_unicode': False,
    }


import six
import inspect
from collections import namedtuple

MAX_WIDTH = 72
SPLITTER_WIDTH = 67

stripspace = " \t\n\r\f\v"

class Line(object):
    def __init__(self, text, elem):
        assert isinstance(text, six.text_type)
        self.text = text
        self.elem = elem
        self.page = None
        self.block = None
        self.keep = False               # keep this line with the previous one

Joiner      = namedtuple('joiner', ['join', 'indent', 'hang', 'overlap', 'do_outdent'])

import copy

# import utils
# wrapper = utils.TextWrapper(width=MAX_WIDTH)
wrapper = TextWrapper(width=MAX_WIDTH)
# splitter = utils.TextSplitter(width=SPLITTER_WIDTH)
splitter = TextSplitter(width=SPLITTER_WIDTH)
# seen = set()

from wcwidth import wcswidth  # pip install wcwidth
def textwidth(u):
    "Length of string, disregarding zero-width code points"
    return wcswidth(u)

def center(text, width, **kwargs):
    "Fold and center the given text"
    # avoid centered text extending all the way to the margins
    kwargs['width'] = width-4
    text = text.replace('\u2028', '\n')
    lines = text.split('\n')
    if max([ len(l) for l in lines ]+[0]) > width:
        # need to reflow
        lines = wrapper.wrap(text, **kwargs)
    for i, l in enumerate(lines):
        lines[i] = l.center(width).rstrip(stripspace)
    text = '\n'.join(lines).replace('\u00A0', ' ')
    return text

def mklines(arg, e):
    if isinstance(arg, six.text_type):
        # \u2028 and \u2029 are eliminated here, through splitlines()
        lines = [ Line(t, e) for t in arg.splitlines() ]
    else:
        lines = arg
    return lines

def mktextblock(arg):
    if isinstance(arg, six.text_type):
        text = arg
    else:
        text = '\u2028'.join([ l.text for l in arg ])
    return text

def align(lines, how, width):
    "Align the given text block left, center, or right, as a block"
    if not lines:
        return lines
    if   how == 'left':
        return lines
    w = max( len(l.text) for l in lines )
    if w >= width:
        return lines
    shift = width - w
    if how == 'center':
        for i, l in enumerate(lines):
            if l.text.strip(stripspace):
                lines[i].text = ' '*(shift//2)+l.text
    elif how == 'right':
        for i, l in enumerate(lines):
            if l.text.strip(stripspace):
                lines[i].text = ' '*(shift)+l.text
    else:
        # XXX TODO: Raise exception, catch in TextWriter, and emit error
        pass
    return lines

def indent(text, indent=3, hang=0):
    lines = []
    text = text.replace('\u2028', '\n')
    for l in text.split('\n'):
        if l.strip(stripspace):
            if lines:
                lines.append(' '*(indent+hang) + l)
            else:
                lines.append(' '*indent + l)
        else:
            lines.append('')
    return '\n'.join(lines)

def mktext(arg):
    if isinstance(arg, six.text_type):
        text = arg
    else:
        text = '\n'.join([ l.text for l in arg ])
    return text

def minwidth(arg):
    text = mktext(arg)
    words = text.split()
    return min([ len(w) for w in words ]+[0])

def fill(text, **kwargs):
    kwargs.pop('joiners', None)
    kwargs.pop('prev', None)
    #
    indent = kwargs.pop('indent', 0)
    hang   = kwargs.pop('hang', 0)
    first  = kwargs.pop('first', 0)
    keep   = kwargs.pop('keep_url', False)
    initial=' '*(first+indent)
    subsequent_indent = ' '*(indent+hang)
    if keep:
        # text = utils.urlkeep(text, max=kwargs['width'])
        text = urlkeep(text, max=kwargs['width'])
    result = wrapper.fill(text, initial=initial, subsequent_indent=subsequent_indent, **kwargs)
    return result

def blankline():
    return [ Line('', None) ]

def lindent(lines, indent=3, hang=0):
    for i, l in enumerate(lines):
        if l.text.strip(stripspace):
            if i == 0:
                lines[i].text = ' '*(indent+hang) + l.text
            else:
                lines[i].text = ' '*(indent) + l.text
    return lines

class TextWriter:

    def __init__(self, options=default_options) -> None:
        self.options = options
        self.errors = []

    def render(self, e, width, **kw):
        if e.tag in (lxml.etree.PI, lxml.etree.Comment):
            return e.tail.lstrip(stripspace) if (e.tail and e.tail.strip(stripspace)) else ''
        kwargs = copy.deepcopy(kw)
        func_name = "render_%s" % (e.tag.lower(),)
        func = getattr(self, func_name, self.default_renderer)
        # if func == self.default_renderer:
        #     # if e.tag in self.__class__.deprecated_element_tags:
        #     #     self.warn(e, "Was asked to render a deprecated element: <%s>" % (e.tag, ))
        #     # elif not e.tag in seen:
        #     if not e.tag in seen:
        #         # self.warn(e, "No renderer for <%s> found" % (e.tag, ))
        #         seen.add(e.tag)
        res = func(e, width, **kwargs)
        return res

    def render_figure(self, e, width, **kwargs):
        kwargs['joiners'].update({
            'name':         Joiner(': ', 0, 0, False, False),
            'artset':       Joiner('', 0, 0, False, False),
            'artwork':      Joiner('', 0, 0, False, True),
            'sourcecode':   Joiner('', 0, 0, False, False),
        })
        #
        pn = e.get('pn')
        num = pn.split('-')[1].capitalize()
        children = e.getchildren()
        title = "Figure %s" % (num, )
        if len(children) and children[0].tag == 'name':
            name = children[0]
            children = children[1:]
            title = self.tjoin(title, name, width, **kwargs)
        lines = []
        for c in children:
            lines = self.ljoin(lines, c, width, **kwargs)
        title = '\n'+center(title, width).rstrip(stripspace)
        lines += mklines(title, e)
        return lines

    def render_artwork(self, e, width, **kwargs):
        # We need this in order to deal with xml comments inside artwork:
        text = (e.text or '') + ''.join([ c.tail for c in e.getchildren() ])
        text = text.strip('\n')
        text = text.strip(stripspace) and text.expandtabs()
        text = '\n'.join( [ l.rstrip(stripspace) for l in text.split('\n') ] )
        #
        lines = [ Line(t, e) for t in text.splitlines() ]
        lines = align(lines, e.get('align', 'left'), width)
        return lines

    def render_t(self, e, width, **kwargs):
        indent = e.get('indent', None) or '0'
        if indent:
            kwargs['indent'] = int(indent)
        text = self.inner_text_renderer(e)
        if kwargs.pop('fill', True):
            text = fill(text, width=width, **kwargs)
            lines = mklines(text, e)
        else:
            if isinstance(text, six.binary_type):
                text = text.decode('utf-8')
            lines = [ Line(text, e) ]
        return lines

    def render_xref(self, e, width, **kwargs):
        format = e.get('format')
        reftext = e.get('derivedContent').strip(stripspace)
        exptext = self.inner_text_renderer(e, width, **kwargs)
        if exptext:
            # for later string formatting convenience, a trailing space if any text:
            exptext += ' '
        content = clean_text(''.join(list(e.itertext())))
        if reftext is None:
            self.die(e, "Found an <xref> without derivedContent: %s" % (lxml.etree.tostring(e),))
        #
        if reftext:
            if format == 'none':
                text = "%s" % exptext
            else:
                if content:
                    text = "%s(%s)" % (exptext, reftext)
                else:
                    text = "%s" % (exptext or reftext)
        else:
            text = exptext.strip(stripspace)
        pageno = e.get('pageno')
        if pageno and pageno.isdigit():
            text += '\u2026' '%04d' % int(pageno)

        # Prevent line breaking on dash
        text = text.replace('-', '\u2011')
        text += (e.tail or '')
        return text

    def render_name(self, e, width, **kwargs):
        hang=kwargs['joiners'][e.tag].hang
        return fill(self.inner_text_renderer(e).strip(stripspace), width=width, hang=hang)

    def render_table(self, e, width, **kwargs):
        kwargs['joiners'].update({
            'name':     Joiner(': ', 0, 0, False, False),
            'dl':       Joiner('\n\n', 0, 0, False, False),
            'ol':       Joiner('\n\n', 0, 0, False, False),
            't':        Joiner('\n\n', 0, 0, False, False),
            'ul':       Joiner('\n\n', 0, 0, False, False),
        })
        #
        pn = e.get('pn')
        num = pn.split('-')[1].capitalize()
        children = e.getchildren()
        title = "Table %s" % (num, )
        if len(children) and children[0].tag == 'name':
            name = children[0]
            children = children[1:]
            title = self.tjoin(title, name, width, **kwargs)
        lines = self.build_table(e, width, **kwargs)
        table_width = min([ width, max( len(l.text) for l in lines ) ])
        min_title_width = min([ 26, len(title) ])
        if table_width < min_title_width:
            table_width = min_title_width
            lines = align(lines, 'center', table_width)
        title = '\n'+center(title, table_width).rstrip(stripspace)
        lines += mklines(title, e)
        lines = align(lines, e.get('align', 'center'), width)
        return lines

    # --- fallback rendering functions ------------------------------------------

    def default_renderer(self, e, width, **kwargs):
        # This is a fallback when a more specific function doesn't exist
        text = "<%s>:%s" % (e.tag, e.text or '')
        for c in e.getchildren():
            ctext = self.render(c, width, **kwargs)
            if isinstance(ctext, list):
                ctext = "\n\n".join(ctext)
            # if ctext is None and debug:
            #     debug.show('e')
            #     debug.show('c')
            text += '\n' + ctext
        text += e.tail or ''
        return text

    def inner_text_renderer(self, e, width=None, **kwargs):
        text = e.text or ''
        for c in e.getchildren():
            try:
                text += self.render(c, width, **kwargs)
            except TypeError:
                # debug.show('c')
                raise
        return text.strip(stripspace)

    def text_or_block_renderer(self, e, width, **kw):
        # This handles the case where the element has two alternative content
        # models, either text or block-level children; deal with them
        # separately.  Return text and whether this was plain text.
        kwargs = copy.deepcopy(kw)
        # if utils.hastext(e):
        if hastext(e):
            _tag = e.tag; e.tag = 't'
            text = mktext(self.ljoin([], e, width, **kwargs))
            e.tag = _tag
            return text, True
        else:
            lines = []
            for c in e.getchildren():
                lines = self.ljoin(lines, c, width, **kwargs)
                kwargs.pop('first', None)
            return lines, False

    def ljoin(self, lines, e, width, **kwargs):
        '''
        Render element e, then format and join it to preceding text using the
        appropriate settings in joiners.
        '''
        assert isinstance(lines, list)
        assert not lines or isinstance(lines[0], Line)
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        width -= j.indent
        kwargs['hang'] = j.hang
        res = mklines(self.render(e, width, **kwargs), e)
        if lines:
            for i in range(j.join.count('\n')-1):
                lines += blankline()
        reswidth = max(len(l.text) for l in res) if res else 0
        indent = j.indent
        residue = 0
        if (hasattr(e, 'outdent') and e.outdent) or (j.do_outdent and reswidth > width):
            outdent = e.outdent if e.outdent else reswidth-width
            residue = max(0, outdent - indent)
            if residue:
                e.getparent().outdent = residue
            indent -= min(indent, outdent)
            self.warn(e, "%s too wide, reducing indentation from %s to %s" % (e.tag.capitalize(), j.indent, indent))
        nlines = lindent(res, indent, j.hang)
        if j.overlap and nlines:
            firstline = nlines[0]
            nlines = nlines[1:]
            if firstline.text.strip(stripspace):
                lines[-1].text += j.join + firstline.text.lstrip(stripspace)
        lines += nlines
        return lines

    def tjoin(self, text, e, width, **kwargs):
        '''
        Render element e, then format and join it to text using the
        appropriate settings in joiners.
        '''
        assert isinstance(text, six.text_type)
        joiners = kwargs['joiners']
        j = joiners[e.tag] if e.tag in joiners else joiners[None]
        width -= j.indent + j.hang
        if width < minwidth(text):
            self.die(e, "Trying to render text in a too narrow column: width: %s, text: '%s'" % (width, text))
        kwargs['hang'] = j.hang
        etext = self.render(e, width, **kwargs)
        itext = indent(etext, j.indent, j.hang)
        if text:
            if '\n' in j.join:
                text += j.join + itext
            elif j.join.strip(stripspace) and not itext.strip(stripspace):
                # don't use non-empty joiners with empty content
                pass
            else:
                text += j.join + itext.lstrip(stripspace)
        else:
            text  = itext
        return text

    def build_table(self, e, width, **kwargs):
        # variations on border characters for table styles
        # style = self.get_relevant_pi(e, 'table_borders') or self.options.table_borders
        style = 'full'
        bchar_sets = {
                'full': { '=': '=',
                          '-': '-',
                          '+': '+',
                          '|': '|',},
                'light':{ '=': '-',
                          '-': None,
                          '+': '+',
                          '|': '|',},
                'min':  { '=': '-',
                          '-': None,
                          '+': ' ',
                          '|': ' ',},
            }
        bchar_sets['minimal'] = bchar_sets['min']
        bchar = bchar_sets[style]
        class Cell(object):
            type    = b'None'
            text    = None
            wrapped = []
            colspan = 1
            rowspan = 1
            width   = None
            minwidth= None
            height  = None
            element = None
            padding = 0
            foldable= True
            top     = ''
            bot     = ''

        # def show(cells, attr='', note=''):
        #     # debug.say('')
        #     # debug.say('%s %s:' % (attr, note))
        #     for i in range(len(cells)):
        #         row = [ (c.type[1], getattr(c, attr)) if attr else c for c in cells[i] ]
        #         # debug.say(str(row).replace('\u2028', '\u00a4'))

        def array(rows, cols, init):
            a = []
            for i in range(rows):
                a.append([])
                for j in range(cols):
                    if inspect.isclass(init):
                        a[i].append(init())
                    else:
                        a[i].append(init)
            return a

        def intattr(e, name):
            attr = e.get(name)
            if attr.isdigit():
                attr = int(attr)
            else:
                attr = 1
            return attr

        def get_dimensions(e):
            cols = 0
            rows = 0
            # Find the dimensions of the table
            for p in e.iterchildren(['thead', 'tbody', 'tfoot']):
                for r in p.iterchildren('tr'):
                    ccols = 0
                    crows = 0
                    extrarows = 0
                    for c in r.iterchildren('td', 'th'):
                        colspan = intattr(c, 'colspan')
                        ccols += colspan
                        rowspan = intattr(c, 'rowspan')
                        crows = max(crows, rowspan)
                    cols = max(cols, ccols)
                    extrarows = max(extrarows, crows)
                    extrarows -=1
                    rows += 1
            if extrarows > 0:
                rows += extrarows
            return rows, cols

        def justify(cell, line, minpad):
            align = cell.element.get('align')
            if align == 'center':
                padding = 0
                width = cell.colwidth
            else:
                padding = cell.colwidth - textwidth(line)
                width = cell.colwidth - min(2, padding)
            if   align == 'left':
                text = line.ljust(width)
            elif align == 'center':
                text = line.center(width)
            elif align == 'right':
                text = line.rjust(width)
            if   align == 'right':
                if padding > 1:
                    text = text + ' ' if minpad > 1 else ' ' + text
                if padding > 0:
                    text = ' ' + text
            elif align == 'left':
                if padding > 1:
                    text = ' ' + text if minpad > 1 else text + ' '
                if padding > 0:
                    text = text + ' '
            else:
                pass
            return text

        def merge_border(c, d):
            border = {
                '=': { '=':'=', '-':'=', '+':'+', },
                '-': { '=':'=', '-':'-', '+':'+', },
                '+': { '=':'+', '-':'+', '+':'+', '|':'+', },
                '|': { '+':'+', '|':'|', },
            }
            if c in border and d in border[c]:
                return border[c][d]
            return c

        def build_line(cells, i, cols, next=True):
            def table(e):
                return list(e.iterancestors('table'))[0]
            line = ''
            e = cells[i][0].element
            for j in range(cols):
                k, l = cells[i][j].origin
                # skip colspan cells
                if k==i and l<j:
                    continue
                cell = cells[k][l]
                part = cell.wrapped[cell.m]
                if next:
                    cell.m += 1
                if line:
                    if bchar['|']:
                        line = line[:-1] + merge_border(line[-1], part[0]) + part[1:]
                    else:
                        line = line + part
                else:
                    line = part
            return Line(line, table(e))

        def find_minwidths(e, cells, hyphen_split=False):
            """
            Find the minimum column widths of regular cells
            """
            i = 0
            # splitter = utils.TextSplitter(width=SPLITTER_WIDTH, hyphen_split=hyphen_split)
            splitter = TextSplitter(width=SPLITTER_WIDTH, hyphen_split=hyphen_split)
            for p in e.iterchildren(['thead', 'tbody', 'tfoot']):
                for r in list(p.iterchildren('tr')):
                    j = 0
                    for c in r.iterchildren('td', 'th'):
                        # skip over cells belonging to an earlier row or column
                        while j < len(cells[i]) and cells[i][j].element != c:
                            j += 1
                        #
                        cell = cells[i][j]
                        if cell.foldable:
                            cell.text = cell.text.strip(stripspace)
                            cell.minwidth = max([0]+[ len(word.strip(stripspace)) for word in splitter._split(cell.text) ]) if cell.text else 0
                        else:
                            cell.minwidth = max([0]+[ len(word.strip(stripspace)) for line in cell.text.splitlines() for word in splitter._split(line) ])
                    i += 1

        def set_colwidths(cells, rows, cols):
            """
            Compute the adjusted cell widths; the same for all rows of each column
            """
            for j in range(cols):
                colmax = 0
                for i in range(rows):
                    cell = cells[i][j]
                    if cell.minwidth:
                        cw = cell.minwidth // cell.colspan
                        if cw > colmax:
                            colmax = cw
                for i in range(rows):
                    cells[i][j].colwidth = colmax

        # ----------------------------------------------------------------------
        rows, cols = get_dimensions(e)
        cells = array(rows, cols, Cell)

        # ----------------------------------------------------------------------
        # Iterate through tr and th/td elements, and annotate the cells array
        # with rowspan, colspan, and owning element and its origin
        i = 0
        for p in e.iterchildren(['thead', 'tbody', 'tfoot']):
            for r in list(p.iterchildren('tr')):
                j = 0
                for c in r.iterchildren('td', 'th'):
                    # skip over cells belonging to an earlier row or column
                    while j < len(cells[i]) and cells[i][j].element != None:
                        j += 1
                    #
                    cell = cells[i][j]
                    cell.colspan = intattr(c, 'colspan')
                    cell.rowspan = intattr(c, 'rowspan')
                    if len(c) == 1 and c[0].tag == 't':
                        cell.text, cell.foldable = self.text_or_block_renderer(c[0], width, fill=False, **kwargs) or ('', True)
                    else:
                        cell.text, cell.foldable = self.text_or_block_renderer(c, width, fill=False, **kwargs) or ('', True)
                    cell.text = mktextblock(cell.text)
                    if cell.foldable:
                        cell.text = cell.text.strip(stripspace)
                        cell.minwidth = max([0]+[ len(word) for word in splitter._split(cell.text) ]) if cell.text else 0
                    else:
                        cell.minwidth = max([0]+[ len(word) for line in cell.text.splitlines() for word in splitter._split(line) ])
                    cell.type = p.tag
                    if c.tag == 'th':
                        cell.top = bchar['=']
                        cell.bot = bchar['=']
                    else:
                        cell.top = bchar['-'] if not cell.top else cell.top
                        cell.bot = bchar['-'] if not cell.bot else cell.bot
                    for k in range(i, i+cell.rowspan):
                        for l in range(j, j+cell.colspan):
                            cells[k][l].element = c
                            cells[k][l].origin  = (i, j)
                i += 1
        # Ensure we have top and bottom borders
        for j in range(len(cells[0])):
            if hasattr(cells[0][j], 'origin'):
                k, l = cells[0][j].origin
                if not cells[k][l].top:
                    cells[k][l].top = bchar['=']
        for j in range(len(cells[-1])):
            if hasattr(cells[-1][j], 'origin'):
                k, l = cells[-1][j].origin
                if not cells[k][l].bot:
                    cells[k][l].bot = bchar['=']
        #show(cells, 'origin')

        # ----------------------------------------------------------------------
        # Find the minimum column widths of regular cells, and total width
        # per row.
        find_minwidths(e, cells, hyphen_split=self.options.table_hyphen_breaks)
        #show(cells, 'minwidth')
        #debug.pprint('totwidth')

        # ----------------------------------------------------------------------
        # Compute the adjusted cell widths; the same for all rows of each column
        set_colwidths(cells, rows, cols)
        reqwidth = sum([ c.colwidth for c in cells[0] ]) + cols + 1
        if reqwidth > width:
            # Try again, splitting cell content on hyphens this time
            find_minwidths(e, cells, hyphen_split=True)
            set_colwidths(cells, rows, cols)
        #show(cells, 'colwidth', 'after aligned cell widths')

        # ----------------------------------------------------------------------
        # Add padding if possible. Pad widest first.
        reqwidth = sum([ c.colwidth for c in cells[0] ]) + (cols + 1)*len(bchar['|'])
        if reqwidth > width:
            self.warn(e, "Total table width (%s) exceeds available width (%s)" % (reqwidth, width))
        excess = width - reqwidth
        #
        if excess > 0:
            widths = [ (c.colwidth, ic) for ic, c in enumerate(cells[0]) ]
            widths.sort()
            widths.reverse()
            for j in [ k for w, k in widths ]:
                if excess > 2:
                    pad = min(2, excess)
                    excess -= pad
                    for i in range(rows):
                        cells[i][j].colwidth += pad
                        cells[i][j].padding   = pad
        #show(cells, 'colwidth', 'after padding')

        # ----------------------------------------------------------------------
        # Set up initial cell.wrapped values
        for i in range(rows):
            for j in range(cols):
                cell = cells[i][j]
                if cell.text:
                    if cell.foldable:
                        cell.wrapped = fill(cell.text, width=cell.colwidth, fix_sentence_endings=True).splitlines()
                    else:
                        cell.wrapped = cell.text.splitlines()

        # ----------------------------------------------------------------------
        # Make columns wider, if possible
        while excess > 0:
            maxpos = (None, None)
            maxrows = 0
            for i in range(rows):
                for j in range(cols):
                    cell = cells[i][j]
                    if hasattr(cell, 'origin'):
                        if cell.origin == (i,j):
                            w = sum([ cells[i][k].colwidth for k in range(j, j+cell.colspan)])+ cell.colspan-1 - cell.padding
                            r = cell.rowspan
                            # this is simplified, and doesn't always account for the
                            # extra line from the missing border line in a rowspan cell:
                            if cell.text:
                                if cell.foldable:
                                    cell.wrapped = fill(cell.text, width=w, fix_sentence_endings=True).splitlines()
                                else:
                                    cell.wrapped = [ l.text for l in self.text_or_block_renderer(cell.element, width=w, fill=True, **kwargs)[0] ]
                                cell.height = len(cell.wrapped)
                                if maxrows < cell.height and cell.height > 1:
                                    maxrows = cell.height
                                    maxpos = (i, j)
                    else:
                        self.die(e, "Inconsistent table width: Found different row lengths in this table")

            # calculate a better width for the cell with the largest number
            # of text rows
            if maxpos != (None, None):
                i, j = maxpos
                cell = cells[i][j]
                w = sum([ cells[i][k].colwidth for k in range(j, j+cell.colspan)])+ cell.colspan-1 - cell.padding
                r = cell.rowspan
                h = cell.height
                for l in range(1, excess+1):
                    lines = fill(cell.text, width=w+l, fix_sentence_endings=True).splitlines()
                    if len(lines) < h:
                        cell.height = lines
                        excess -= l
                        c = h//r
                        for k in range(rows):
                            cells[k][j].colwidth += l
                        break
                else:
                    break
            else:
                break

        #show(cells, 'colwidth', 'after widening wide cells and re-wrapping lines')
        #show(cells, 'height')
        #show(cells, 'origin')

        # ----------------------------------------------------------------------
        # Normalize cell height and lines lists
        #show(cells, 'wrapped', 'before height normalization')
        #show(cells, 'rowspan', 'before height normalization')
        for i in range(rows):
            minspan = sys.maxsize
            for j in range(cols):
                cell = cells[i][j]
                k, l = cell.origin
                hspan = cell.rowspan+k-i if cell.rowspan else minspan
                if hspan > 0 and hspan < minspan:
                    minspan = hspan
            maxlines = 0
            for j in range(cols):
                cell = cells[i][j]
                k, l = cell.origin
                hspan = cell.rowspan+k-i if cell.rowspan else minspan
                lines = len(cell.wrapped) if cell.wrapped else 0
                if hspan == minspan and lines > maxlines:
                    maxlines = lines
            for j in range(cols):
                cells[i][j].lines = maxlines

        # ----------------------------------------------------------------------
        # Calculate total height for rowspan cells
        for i in range(rows):
            for j in range(cols):
                cells[i][j].m = None
                cells[i][j].height = None
                k, l = cells[i][j].origin
                cell = cells[k][l]
                if cell.m is None:
                    cell.m = 0
                    cell.height = sum([ cells[n][l].lines for n in range(k, k+cell.rowspan)]) + cell.rowspan-1

        # ----------------------------------------------------------------------
        # Calculate total width for colspan cells
        for i in range(rows):
            for j in range(cols):
                k, l = cells[i][j].origin
                cell = cells[k][l]
                if cell.origin == (i,j):
                    cell.colwidth = sum([ cells[i][n].colwidth for n in range(j, j+cell.colspan)]) + cell.colspan-1

        # ----------------------------------------------------------------------
        # Calculate minimum padding per table column
        minpad = [width,]*cols
        for i in range(rows):
            for j in range(cols):
                cell = cells[i][j]
                if cell.origin == (i, j):
                    padding = min([width] + [(cell.colwidth - textwidth(line)) for line in cell.wrapped])
                    if padding < minpad[j]:
                        minpad[j] = padding

        # ----------------------------------------------------------------------
        # Add cell borders
        x = bchar['+']
        l = bchar['|']
        for i in range(rows):
            for j in range(cols):
                cell = cells[i][j]
                if cell.origin == (i, j):
                    wrapped = (cell.wrapped + ['']*cell.height)[:cell.height]
                    lines = (  ([ x + cell.top*cell.colwidth + x ] if cell.top else [])
                             + ([ l + justify(cell, line, minpad[j]) + l for line in wrapped ])
                             + ([ x + cell.bot*cell.colwidth + x ] if cell.bot else []) )
                    cell.wrapped = lines

        #show(cells, 'lines', 'before assembly')
        # ----------------------------------------------------------------------
        # Emit combined cell content, line by line
        lines = []
        prev_bottom_border_line = None
        for i in range(rows):
            # For each table row, render the top cell border (if any) and content.  The bottom
            # border will be merged with the next row's top border when processing that row.
            has_top_border = any( c.top for c in cells[i] if c.wrapped)
            has_bot_border = any( c.bot for c in cells[i] if c.wrapped)
            for n in range(min(len(c.wrapped) for c in cells[i] if c.wrapped)-int(has_bot_border) ):
                line = build_line(cells, i, cols)
                lines.append(line)
                if prev_bottom_border_line:
                    if has_top_border:
                        line = lines[-1]
                        lines[-1] = Line(''.join(merge_border(prev_bottom_border_line.text[c], line.text[c]) for c in range(len(line.text))), line.elem)
                    else:
                        line = lines[-1]
                        lines[-1] = prev_bottom_border_line
                        lines.append(line)
                prev_bottom_border_line = None
            # Get the next line, which will contain the bottom border for completed cells,
            # without incrementing the line count (we might have rowspan cells which might
            # not have been completely consumed yet):
            prev_bottom_border_line = build_line(cells, i, cols, next=False) if has_bot_border else None
        lines.append(prev_bottom_border_line)
        return lines

    def msg(self, e, label, text):
        if e != None:
            lnum = getattr(e, 'sourceline', None)
            file = getattr(e, 'base', None)
            if lnum:
                # msg = "%s(%s): %s %s" % (file or self.xmlrfc.source, lnum, label, text, )
                msg = "%s(%s): %s %s" % (file or "[dummy!]", lnum, label, text, )
            else:
                msg = "(No source line available): %s %s" % (label, text, )
        else:
            msg = "%s %s" % (label, text)
        return msg

    def silenced(self, e, text):
        # text = text.strip()
        # pis = self.get_relevant_pis(e)
        # silenced = filter(None, self.options.silence[:] + [ pi.get('silence') for pi in pis ])
        # for s in silenced:
        #     for label in ['Note: ', 'Warning: ']:
        #         if s.startswith(label):
        #             s = s[len(label):]
        #     if text.startswith(s):
        #         return True
        #     try:
        #         if re.match(s, text):
        #             return True
        #     except re.error:
        #         pass
        # return False
        return True

    def note(self, e, text, label='Note:'):
        if self.options.verbose:
            if not self.silenced(e, text):
                self.log(self.msg(e, label, text))

    def warn(self, e, text, label='Warning:'):
        if self.options.verbose or not self.silenced(e, text):
            self.log(self.msg(e, label, text))

    def err(self, e, text, trace=False):
        msg = self.msg(e, 'Error:', text)
        self.errors.append(msg)
        if trace or self.options.debug:
            raise RuntimeError(msg)
        else:
            self.log(msg)

    def die(self, e, text, trace=False):
        msg = self.msg(e, 'Error:', text)
        self.errors.append(msg)
        # raise RfcWriterError(msg)
        raise Exception(msg)

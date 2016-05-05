# ---------------------------
# Imports
# ---------------------------

from .base import Element
from .elements import *

import os
import re
import sys
import json
import yaml
import shlex
from shutil import which
from subprocess import Popen, PIPE, call
from functools import partial


# ---------------------------
# Constants
# ---------------------------

Spaces = (Space, LineBreak, SoftBreak)

VerticalSpaces = (Para, )


# ---------------------------
# Functions
# ---------------------------

def stringify(element):
    """
    Return the raw text version of an elements (and its children element).

    Example:

        >>> from panflute import *
        >>> e1 = Emph(Str('Hello'), Space, Str('world!'))
        >>> e2 = Strong(Str('Bye!'))
        >>> para = Para(e1, e2)
        >>> stringify(para)
        'Hello world! Bye!'
    """

    def attach_str(e, doc, partial_str):
        if type(e) == Citation:
            ans = ''
        if hasattr(e, 'text'):
            ans = e.text
        elif isinstance(e, Spaces):
            ans = ' '
        elif isinstance(e, VerticalSpaces):
            ans = '\n\n'
        else:
            ans = ''
        partial_str.append(ans)

    partial_str = []
    partial_attach_str = partial(attach_str, partial_str=partial_str)
    element.walk(partial_attach_str)
    return ''.join(partial_str)


def replace_keyword(doc, keyword, replacement):
    """
    ...
    .. note:: may not be robust to corner cases (handling spaces, etc.)
    """

    def filter_kwd(e, d):
        if type(e) == Str and e.text == keyword:
            if isinstance(replacement, Inline):
                doc.replacement_ok = True
                return replacement
        elif type(e) == Para and len(e.items) == 1:
            ee = e.items[0]
            if type(ee) == Str and ee.text == keyword:
                doc.replacement_ok = True
                return replacement

    doc = doc.walk(filter_kwd, doc)


def debug(*args, **kwargs):
    """
    ...
    """
    print(*args, **kwargs, file=sys.stderr)


def convert_text(text, input_format='markdown', output_format='json'):
    """
    Pandoc Wrapper; based on pyandoc by Kenneth Reitz

    Returns a list of items
    """

    pandoc_path = which('pandoc')
    if not os.path.exists(pandoc_path):
        raise OSError("Path to pandoc executable does not exists")
    out_fmt = 'json' if output_format == 'doc' else output_format

    from_arg = '--from={}'.format(input_format)
    to_arg = '--to={}'.format(out_fmt)
    args = [pandoc_path, from_arg, to_arg]
    proc = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    out, err = proc.communicate(input=text.encode('utf-8'))
    exitcode = proc.returncode
    if exitcode != 0:
        raise IOError(err)

    out = out.decode('utf-8')

    if output_format == 'json':
        out = json.loads(out, object_pairs_hook=from_json)[1]

    elif output_format == 'doc':  # Entire document including metadata
        metadata, items = json.loads(out, object_pairs_hook=from_json)
        out = Doc(*items, metadata=metadata)

    else:
        out = "\n".join(out.splitlines())  # Replace \r\n with \n

    return out


def yaml_filter(element, doc, tag=None, function=None, tags=None):
    """
    ...
    """

    # Allow for either tag+function or a dict {tag: function}
    assert (tag is None) + (tags is None) == 1  # XOR
    if tags is None:
        tags = {tag: function}

    if type(element) == CodeBlock:
        for tag in tags:
            if tag in element.classes:
                function = tags[tag]
                # Split yaml and data parts (separated by ... or ---)
                raw = re.split("^([.]{3,}|[-]{3,})$",
                               element.text, 1, re.MULTILINE)
                data = raw[2] if len(raw) > 2 else ''
                raw = raw[0]
                options = yaml.load(raw)
                return function(options=options, data=data,
                                element=element, doc=doc)


def shell(args, wait=True, msg=None):
    """
    Execute the external command and get its exitcode, stdout and stderr.
    """

    # Fix Windows error if passed a string
    if isinstance(args, str):
        args = shlex.split(args, posix=(os.name != "nt"))
        args = [arg.replace('/', '\\') for arg in args]

    if wait:
        proc = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate(input=msg)
        exitcode = proc.returncode
        if exitcode != 0:
            raise IOError(err)
        return out
    else:
        DETACHED_PROCESS = 0x00000008
        proc = Popen(args, creationflags=DETACHED_PROCESS)

#def get_exe_path():
#    reg = winreg.ConnectRegistry(None,winreg.HKEY_CLASSES_ROOT)
#
#    # Fetch verb linked to the dta extension
#    path = '.dta'
#    key = winreg.OpenKey(reg, path)
#    verb = winreg.QueryValue(key, None) # Alternatives: .dta .do
#    
#    # Fetch command linked to that verb
#    path = '{}\shell\open\command'.format(verb)
#    key = winreg.OpenKey(reg, path)
#    cmd = winreg.QueryValue(key, None)
#    fn = cmd.strip('"').split('"')[0]
#    #raise(Exception(fn))
#    return fn
#
#def check_correct_executable(fn):
#    return os.path.isfile(fn) and 'stata' in fn.lower()

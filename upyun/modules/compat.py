# -*- coding: utf-8 -*-

import sys

PY3 = sys.version_info[0] == 3

if PY3:
    from urllib.parse import quote, urlencode

    def b(s):
        if isinstance(s, str):
            return s.encode('utf-8')
        return s

    builtin_str = str
    str = str
    bytes = bytes
else:
    from urllib import quote, urlencode

    def b(s):
        return s

    builtin_str = str
    str = unicode  # noqa
    bytes = str

__all__ = [
    'quote', 'urlencode'
]

#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys

PY3 = sys.version_info[0] == 3

if PY3:
    import http.client as httplib
    from urllib.parse import quote

    def b(s):
        return s.encode("utf-8")

    builtin_str = str
    str = str
    bytes = bytes
else:
    import httplib
    from urllib import quote

    def b(s):
        return s

    builtin_str = str
    str = unicode
    bytes = str

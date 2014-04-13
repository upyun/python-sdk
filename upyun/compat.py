#! /usr/bin/env python
# -*- coding: utf-8 -*-

import sys

PY3 = sys.version_info[0] == 3

if PY3:
    from urllib.parse import quote
    quote = quote

    import http.client
    httplib = http.client

    def s(s):
        return s.decode("utf-8")

    def b(s):
        return s.encode("utf-8")

    unicode = str

else:
    from urllib import quote
    quote = quote

    import httplib
    httplib = httplib

    def s(s):
        return s

    def b(s):
        return s

    unicode = unicode

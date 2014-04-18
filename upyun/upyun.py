#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import socket
import urllib
import hashlib
import datetime

HTTP_EXTEND = None

try:
    import requests
    HTTP_EXTEND = True
except ImportError:
    pass

from . import __version__
from .compat import b, str, bytes, quote, httplib, PY3, builtin_str

ED_LIST = ['v%d.api.upyun.com' % ed for ed in range(4)]
ED_AUTO, ED_TELECOM, ED_CNC, ED_CTT = ED_LIST


# wsgiref.handlers.format_date_time

def httpdate_rfc1123(dt):
    """Return a string representation of a date according to RFC 1123
    (HTTP/1.1).

    The supplied date must be in UTC.

    """
    weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
    month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
             "Oct", "Nov", "Dec"][dt.month - 1]
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % \
        (weekday, dt.day, month, dt.year, dt.hour, dt.minute, dt.second)


class UpYunServiceException(Exception):
    def __init__(self, status, msg, err):
        self.args = (status, msg, err)
        self.status = status
        self.msg = msg
        self.err = err


class UpYunClientException(Exception):
    def __init__(self, msg):
        self.args = (msg)
        self.msg = msg


class UpYun:

    def __init__(self, bucket, username, password,
                 timeout=None, endpoint=None):
        self.bucket = bucket
        self.username = username
        self.password = hashlib.md5(b(password)).hexdigest()
        self.timeout = timeout or 60
        self.endpoint = endpoint or ED_AUTO
        self.user_agent = None

        if HTTP_EXTEND:
            self.session = requests.Session()

    # --- public API

    def usage(self, key='/'):
        return self.__do_http_request('GET', key, args='?usage')

    def put(self, key, value, checksum=False, headers=None):
        """
        >>> with open('foo.png', 'rb') as f:
        >>>    res = up.put('/path/to/bar.png', f, checksum=False,
        >>>                 headers={"x-gmkerl-rotate": "180"}})
        """
        if headers is None:
            headers = {}
        headers['Mkdir'] = 'true'
        if isinstance(value, str):
            value = b(value)
        if checksum is True:
            headers['Content-MD5'] = self.__make_content_md5(value)
        h = self.__do_http_request('PUT', key, value, headers)

        return self.__get_meta_headers(h)

    def get(self, key, value=None):
        """
        >>> with open('bar.png', 'wb') as f:
        >>>    up.get('/path/to/bar.png', f)
        """
        return self.__do_http_request('GET', key, of=value, stream=True)

    def delete(self, key):
        self.__do_http_request('DELETE', key)

    def mkdir(self, key):
        headers = {'Folder': 'true'}
        self.__do_http_request('POST', key, headers=headers)

    def getlist(self, key='/'):
        content = self.__do_http_request('GET', key)
        if content == "":
            return []
        items = content.split('\n')
        return [dict(zip(['name', 'type', 'size', 'time'],
                x.split('\t'))) for x in items]

    def getinfo(self, key):
        h = self.__do_http_request('HEAD', key)
        return self.__get_meta_headers(h)

    # --- private API

    def __do_http_request(self, method, key,
                          value=None, headers=None, of=None, args='',
                          stream=False):

        uri = '/' + self.bucket + (lambda x: x[0] == '/' and x or '/'+x)(key)
        if isinstance(uri, str):
            uri = uri.encode('utf-8')

        uri = quote(uri, safe="~/") + args

        if headers is None:
            headers = {}

        length = 0
        if hasattr(value, 'fileno'):
            length = os.fstat(value.fileno()).st_size
        elif isinstance(value, bytes) or (not PY3 and
                                          isinstance(value, builtin_str)):
            length = len(value)
            headers['Content-Length'] = length
        elif value is not None:
            raise UpYunClientException("object type error")

        # Date Format: RFC 1123
        dt = httpdate_rfc1123(datetime.datetime.utcnow())
        signature = self.__make_signature(method, uri, dt, length)

        headers['Date'] = dt
        headers['Authorization'] = signature
        if self.user_agent:
            headers['User-Agent'] = self.user_agent
        else:
            headers['User-Agent'] = self.__make_user_agent()

        if HTTP_EXTEND:
            return self.__do_http_extend(method, uri, value, headers, of,
                                         stream)
        else:
            return self.__do_http_basic(method, uri, value, headers, of)

    def __make_signature(self, method, uri, date, length):
        signstr = '&'.join([method, uri, date, str(length), self.password])
        signature = hashlib.md5(b(signstr)).hexdigest()
        return 'UpYun ' + self.username + ':' + signature

    def __make_user_agent(self):
        default = "upyun-python-sdk/" + __version__

        if HTTP_EXTEND:
            return "%s %s" % (default, requests.utils.default_user_agent())
        else:
            return default

    def __make_content_md5(self, value):
        if hasattr(value, 'fileno'):
            md5 = hashlib.md5()
            for chunk in iter(lambda: value.read(8192), b''):
                md5.update(chunk)
            value.seek(0)
            return md5.hexdigest()
        elif isinstance(value, bytes) or (not PY3 and
                                          isinstance(value, builtin_str)):
            return hashlib.md5(value).hexdigest()
        else:
            raise UpYunClientException("object type error")

    def __get_meta_headers(self, headers):
        return dict(iter([(k[8:].lower(), v) for k, v in headers
                    if k[:8].lower() == 'x-upyun-']))

    # http://docs.python.org/2/library/httplib.html

    def __do_http_basic(self, method, uri,
                        value=None, headers=None, of=None):

        content, msg, err, status = None, None, None, None
        try:
            connection = httplib.HTTPConnection(self.endpoint,
                                                timeout=self.timeout)
            # connection.set_debuglevel(1)
            connection.request(method, uri, value, headers)
            response = connection.getresponse()

            status = response.status
            if status / 100 == 2:
                if method == "GET" and of:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        of.write(chunk)
                if method == "GET" and of is None:
                    content = response.read()
                    if isinstance(content, bytes):
                        content = content.decode("utf-8")
                if method == "PUT" or method == "HEAD":
                    content = response.getheaders()
            else:
                msg = response.reason
                err = response.read()
                if isinstance(err, bytes):
                    err = err.decode("utf-8")

        except (httplib.HTTPException, socket.error, socket.timeout) as e:
            raise UpYunClientException(str(e))
        except Exception as e:
            raise UpYunClientException(str(e))
        finally:
            if connection:
                connection.close()

        if msg:
            raise UpYunServiceException(status, msg, err)

        return content

    # http://docs.python-requests.org/

    def __do_http_extend(self, method, uri,
                         value=None, headers=None, of=None, stream=False):

        content, msg, err, status = None, None, None, None
        URL = "http://" + self.endpoint + uri
        requests.adapters.DEFAULT_RETRIES = 5

        try:
            response = self.session.request(method, URL, data=value,
                                            headers=headers, stream=stream,
                                            timeout=self.timeout)
            response.encoding = 'utf-8'
            status = response.status_code
            if status / 100 == 2:
                if method == "GET" and of:
                    for chunk in response.iter_content(8192):
                        if not chunk:
                            break
                        of.write(chunk)
                elif method == "GET" and of is None:
                    content = response.text
                elif method == "PUT" or method == "HEAD":
                    content = response.headers.items()
            else:
                msg = response.reason
                err = response.text

        except requests.exceptions.ConnectionError as e:
            raise UpYunClientException(str(e))
        except requests.exceptions.RequestException as e:
            raise UpYunClientException(str(e))
        except Exception as e:
            raise UpYunClientException(str(e))

        if msg:
            raise UpYunServiceException(status, msg, err)

        return content

if __name__ == '__main__':
    pass

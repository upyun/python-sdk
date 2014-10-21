#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import socket
import hashlib
import datetime

HUMAN_MODE = False

try:
    import requests
    HUMAN_MODE = True
except ImportError:
    pass

from . import __version__
from .compat import b, str, bytes, quote, urlencode, httplib, PY3, builtin_str

ED_LIST = ("v%d.api.upyun.com" % ed for ed in range(4))
ED_AUTO, ED_TELECOM, ED_CNC, ED_CTT = ED_LIST

DEFAULT_CHUNKSIZE = 8192


def get_fileobj_size(fileobj):
    try:
        if hasattr(fileobj, 'fileno'):
            return os.fstat(fileobj.fileno()).st_size
    except IOError:
        pass

    return len(fileobj.getvalue())


# wsgiref.handlers.format_date_time

def httpdate_rfc1123(dt):
    """Return a string representation of a date according to RFC 1123
    (HTTP/1.1).

    The supplied date must be in UTC.

    """
    weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][dt.weekday()]
    month = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
             'Oct', 'Nov', 'Dec'][dt.month - 1]
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % \
        (weekday, dt.day, month, dt.year, dt.hour, dt.minute, dt.second)


class UpYunServiceException(Exception):
    def __init__(self, request_id, status, msg, err):
        self.args = (request_id, status, msg, err)
        self.request_id = request_id
        self.status = status
        self.msg = msg
        self.err = err


class UpYunClientException(Exception):
    def __init__(self, msg):
        self.msg = msg
        super(UpYunClientException, self).__init__(msg)


class UploadObject(object):
    def __init__(self, fileobj, chunksize=None, handler=None, params=None):
        self.fileobj = fileobj
        self.chunksize = chunksize or DEFAULT_CHUNKSIZE
        self.totalsize = get_fileobj_size(fileobj)
        self.readsofar = 0
        if handler:
            self.hdr = handler(self.totalsize, params)

    def __next__(self):
        chunk = self.fileobj.read(self.chunksize)
        if chunk and self.hdr:
            self.readsofar += len(chunk)
            if self.readsofar != self.totalsize:
                self.hdr.update(self.readsofar)
            else:
                self.hdr.finish()
        return chunk

    def __len__(self):
        return self.totalsize

    def read(self, size=-1):
        return self.__next__()


class UpYun(object):

    def __init__(self, bucket, username, password,
                 timeout=None, endpoint=None, chunksize=None, human=True):
        self.bucket = bucket
        self.username = username
        self.password = hashlib.md5(b(password)).hexdigest()
        self.timeout = timeout or 60
        self.endpoint = endpoint or ED_AUTO
        self.user_agent = None
        self.chunksize = chunksize or DEFAULT_CHUNKSIZE
        self.human_mode = HUMAN_MODE
        if not human:
            self.human_mode = False

        if self.human_mode:
            self.session = requests.Session()

    # --- public API

    def usage(self, key='/'):
        res = self.__do_http_request('GET', key, args='?usage')
        return str(int(res))

    def put(self, key, value, checksum=False, headers=None,
            handler=None, params=None, secret=None):
        """
        >>> with open('foo.png', 'rb') as f:
        >>>    res = up.put('/path/to/bar.png', f, checksum=False,
        >>>                 headers={'x-gmkerl-rotate': '180'}})
        """
        if headers is None:
            headers = {}
        headers['Mkdir'] = 'true'
        if isinstance(value, str):
            value = b(value)

        if checksum is True:
            headers['Content-MD5'] = self.__make_content_md5(value)

        if secret:
            headers['Content-Secret'] = secret

        if handler and hasattr(value, 'fileno'):
            value = UploadObject(value, chunksize=self.chunksize,
                                 handler=handler, params=params)

        h = self.__do_http_request('PUT', key, value, headers)

        return self.__get_meta_headers(h)

    def get(self, key, value=None, handler=None, params=None):
        """
        >>> with open('bar.png', 'wb') as f:
        >>>    up.get('/path/to/bar.png', f)
        """
        return self.__do_http_request('GET', key, of=value, stream=True,
                                      handler=handler, params=params)

    def delete(self, key):
        self.__do_http_request('DELETE', key)

    def mkdir(self, key):
        headers = {'Folder': 'true'}
        self.__do_http_request('POST', key, headers=headers)

    def getlist(self, key='/'):
        content = self.__do_http_request('GET', key)
        if content == '':
            return []
        items = content.split('\n')
        return [dict(zip(['name', 'type', 'size', 'time'],
                x.split('\t'))) for x in items]

    def getinfo(self, key):
        h = self.__do_http_request('HEAD', key)
        return self.__get_meta_headers(h)

    def purge(self, keys, domain=None):
        domain = domain or '%s.b0.upaiyun.com' % (self.bucket)
        if isinstance(keys, builtin_str):
            keys = [keys]
        if isinstance(keys, list):
            urlfmt = 'http://%s/%s'
            urlstr = '\n'.join([urlfmt % (domain, k if k[0] != '/' else k[1:])
                                for k in keys]) + '\n'
        else:
            raise UpYunClientException('keys type error')

        api = ['purge.upyun.com', '/purge/']
        params = urlencode({"purge": urlstr})
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'Accept': 'application/json'}
        self.__set_auth_headers(urlstr, headers=headers)

        content, msg, err, status = None, None, None, None

        try:
            if self.human_mode:
                resp = self.session.post('http://' + ''.join(api), data=params,
                                         timeout=self.timeout, headers=headers)
                resp.encoding = 'utf-8'
                status = resp.status_code
                if status / 100 == 2:
                    content = resp.json()
                else:
                    msg = resp.reason
                    err = resp.text
            else:
                conn = httplib.HTTPConnection(api[0], timeout=self.timeout)
                conn.request('POST', '/purge/', params, headers=headers)
                resp = conn.getresponse()
                status = resp.status
                if status / 100 == 2:
                    content = json.loads(self.__decode_msg(resp.read()))
                else:
                    msg = resp.reason
                    err = self.__decode_msg(resp.read())

        except Exception as e:
            raise UpYunClientException(str(e))
        finally:
            if not self.human_mode and conn:
                conn.close()

        if msg:
            raise UpYunServiceException(None, status, msg, err)

        invalid_urls = content['invalid_domain_of_url']
        return [k[7 + len(domain):] for k in invalid_urls]

    # --- private API

    def __do_http_request(self, method, key,
                          value=None, headers=None, of=None, args='',
                          stream=False, handler=None, params=None):

        _uri = "/%s/%s" % (self.bucket, key if key[0] != '/' else key[1:])
        uri = "%s%s" % (quote(self.__encode_msg(_uri), safe='~/'), args)

        if headers is None:
            headers = {}

        length = 0
        if hasattr(value, '__len__'):
            length = len(value)
            headers['Content-Length'] = length
        elif hasattr(value, 'fileno'):
            length = get_fileobj_size(value)
            headers['Content-Length'] = length
        elif value is not None:
            raise UpYunClientException('object type error')

        self.__set_auth_headers(uri, method, length, headers)

        if self.human_mode:
            return self.__do_http_human(method, uri, value, headers, of,
                                        stream, handler, params)
        else:
            return self.__do_http_basic(method, uri, value, headers, of,
                                        handler, params)

    def __make_signature(self, method, uri, date, length):
        signstr = '&'.join([method, uri, date, str(length), self.password])
        signature = hashlib.md5(b(signstr)).hexdigest()
        return "UpYun %s:%s" % (self.username, signature)

    def __make_purge_signature(self, urlstr, date):
        signstr = '&'.join([urlstr, self.bucket, date, self.password])
        signature = hashlib.md5(b(signstr)).hexdigest()
        return "UpYun %s:%s:%s" % (self.bucket, self.username, signature)

    def __make_user_agent(self):
        default = "upyun-python-sdk/%s" % __version__

        if self.human_mode:
            return "%s %s" % (default, requests.utils.default_user_agent())
        else:
            return default

    def __make_content_md5(self, value):
        if hasattr(value, 'fileno'):
            md5 = hashlib.md5()
            for chunk in iter(lambda: value.read(self.chunksize), b''):
                md5.update(chunk)
            value.seek(0)
            return md5.hexdigest()
        elif isinstance(value, bytes) or (not PY3 and
                                          isinstance(value, builtin_str)):
            return hashlib.md5(value).hexdigest()
        else:
            raise UpYunClientException('object type error')

    def __get_meta_headers(self, headers):
        return dict((k[8:].lower(), v) for k, v in headers
                    if k[:8].lower() == 'x-upyun-')

    def __set_auth_headers(self, playload,
                           method=None, length=0, headers=None):
        if headers is None:
            headers = []
        # Date Format: RFC 1123
        dt = httpdate_rfc1123(datetime.datetime.utcnow())
        if method:
            signature = self.__make_signature(method, playload, dt, length)
        else:
            signature = self.__make_purge_signature(playload, dt)

        headers['Date'] = dt
        headers['Authorization'] = signature
        if self.user_agent:
            headers['User-Agent'] = self.user_agent
        else:
            headers['User-Agent'] = self.__make_user_agent()
        return headers

    def __decode_msg(self, msg):
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8')
        return msg

    def __encode_msg(self, msg):
        if isinstance(msg, str):
            msg = msg.encode('utf-8')
        return msg

    # http://docs.python.org/2/library/httplib.html

    def __do_http_basic(self, method, uri,
                        value=None, headers=None, of=None,
                        handler=None, params=None):

        request_id, content, msg, err, status = None, None, None, None, None
        try:
            conn = httplib.HTTPConnection(self.endpoint, timeout=self.timeout)
            # conn.set_debuglevel(1)
            conn.request(method, uri, value, headers)
            resp = conn.getresponse()
            request_id = resp.getheader("X-Request-Id", "Unknown")

            status = resp.status
            if status / 100 == 2:
                if method == 'GET' and of:
                    readsofar = 0
                    totalsize = resp.getheader('content-length')
                    totalsize = totalsize and int(totalsize) or 0

                    hdr = None
                    if handler and totalsize > 0:
                        hdr = handler(totalsize, params)

                    while True:
                        chunk = resp.read(self.chunksize)
                        if chunk and hdr:
                            readsofar += len(chunk)
                            if readsofar != totalsize:
                                hdr.update(readsofar)
                            else:
                                hdr.finish()
                        if not chunk:
                            break
                        of.write(chunk)
                if method == 'GET' and of is None:
                    content = self.__decode_msg(resp.read())
                if method == 'PUT' or method == 'HEAD':
                    content = resp.getheaders()
            else:
                msg = resp.reason
                err = self.__decode_msg(resp.read())

        except (httplib.HTTPException, socket.error, socket.timeout) as e:
            raise UpYunClientException(str(e))
        except Exception as e:
            raise UpYunClientException(str(e))
        finally:
            if conn:
                conn.close()

        if msg:
            raise UpYunServiceException(request_id, status, msg, err)

        return content

    # http://docs.python-requests.org/

    def __do_http_human(self, method, uri,
                        value=None, headers=None, of=None, stream=False,
                        handler=None, params=None):

        request_id, content, msg, err, status = None, None, None, None, None
        URL = "http://%s%s" % (self.endpoint, uri)
        requests.adapters.DEFAULT_RETRIES = 5

        try:
            resp = self.session.request(method, URL, data=value,
                                        headers=headers, stream=stream,
                                        timeout=self.timeout)
            resp.encoding = 'utf-8'
            try:
                request_id = resp.headers["X-Request-Id"]
            except KeyError:
                request_id = "Unknown"
            status = resp.status_code
            if status / 100 == 2:
                if method == 'GET' and of:
                    readsofar = 0
                    try:
                        totalsize = int(resp.headers['content-length'])
                    except (KeyError, TypeError):
                        totalsize = 0

                    hdr = None
                    if handler and totalsize > 0:
                        hdr = handler(totalsize, params)

                    for chunk in resp.iter_content(self.chunksize):
                        if chunk and hdr:
                            readsofar += len(chunk)
                            if readsofar != totalsize:
                                hdr.update(readsofar)
                            else:
                                hdr.finish()
                        if not chunk:
                            break
                        of.write(chunk)
                elif method == 'GET' and of is None:
                    content = resp.text
                elif method == 'PUT' or method == 'HEAD':
                    content = resp.headers.items()
            else:
                msg = resp.reason
                err = resp.text

        except requests.exceptions.ConnectionError as e:
            raise UpYunClientException(str(e))
        except requests.exceptions.RequestException as e:
            raise UpYunClientException(str(e))
        except Exception as e:
            raise UpYunClientException(str(e))

        if msg:
            raise UpYunServiceException(request_id, status, msg, err)

        return content

if __name__ == '__main__':
    pass

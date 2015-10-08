# -*- coding: utf-8 -*-

#######NOTICE HTTP METHOD
#######NOTICE AV CLASS

import os
import json
import hashlib
import datetime
import sys
from coding import encode_msg

from exception import UpYunServiceException, UpYunClientException
from compat import b, str, bytes, quote, urlencode, httplib, PY3, builtin_str
from httpipe import httpPipe
from Multipart import *
from AvPretreatment import *

__version__ = '2.2.5'

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
    def __init__(self, bucket, username, password, timeout=None,
                 endpoint=None, chunksize=None, human=True,
                 secret=None, multipart=False):
        self.password = None
        self.check(username, password, secret, multipart)
        self.password = hashlib.md5(b(self.password)).hexdigest()
        self.multipart = multipart
        self.bucket = bucket
        self.username = username
        self.timeout = timeout or 60
        self.endpoint = endpoint or ED_AUTO
        self.user_agent = None
        self.chunksize = chunksize or DEFAULT_CHUNKSIZE
        self.secret = secret
        self.av = None
        self.hp = httpPipe(human, self.timeout, self.chunksize)

    def check(self, username, password, secret, multipart):
        if multipart:
            if not secret:
                raise UpYunClientException('You have to specify form-secret')
        else:
            if not username or not password:
                raise UpYunClientException('Not enough account information')
        if not password:
            self.password = ''
        else:
            self.password = password

    # --- public API
    def open_multipart(self):
        self.multipart = True
        if not self.secret:
            raise UpYunClientException('You have to specify form-secret')

    def close_multipart(self):
        self.multipart = False

    def usage(self, key='/'):
        res = self.__do_http_request('GET', key, args='?usage')
        return str(int(res))

    def put(self, key, value, checksum=False, headers=None,
            handler=None, params=None, secret=None, block_size=(1024 *1024)):
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

        if self.multipart and hasattr(value, 'fileno'):
            mp = Multipart(key, value, self.bucket, self.secret, self.timeout, block_size)
            ret, h = mp.multipart_upload()
            if (ret / 100000) == 4:
                raise UpYunClientException(h)
            elif (ret / 100000) == 5:
                x_request_id = mp.get_x_request_id()
                status_code = mp.get_status_code()
                raise UpYunServiceException(x_request_id, status_code, h, None)
            else:
                return self.__get_multi_meta_headers(h)
        else:
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

        method = 'POST'
        host = 'purge.upyun.com'
        uri = '/purge/'
        params = urlencode({"purge": urlstr})
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'Accept': 'application/json'}
        self.__set_auth_headers(urlstr, headers=headers)

        content = self.hp.do_http_pipe(method, host, uri, 
                                        value=params, headers=headers)

        invalid_urls = content['invalid_domain_of_url']
        return [k[7 + len(domain):] for k in invalid_urls]

    # --- video pretreatment API

    def pretreat(self, tasks, source, notify_url=""):
        self.av = AvPretreatment(self.username, self.password, self.bucket, self.timeout, 
                                    notify_url=notify_url, tasks=tasks, source=source)
        ids = self.av.run()
        # means something error happend
        if type(ids) != list:
            status_code = self.av.get_status_code()
            x_request_id = self.av.get_x_request_id()
            raise UpYunServiceException(x_request_id, status_code, ids, None)
        return ids

    def status(self, taskids=None):
        if taskids:
            self.av = AvPretreatment(self.username, self.password, self.bucket,
                                        self.timeout, taskids=taskids)
            tasks = self.av.get_tasks_status()
        else:
            if self.av:
                tasks = self.av.get_tasks_status()
            else:
                raise UpYunClientException('You should specify taskid')

        if type(tasks) == dict:
            return tasks
        else:
            status_code = self.av.get_status_code()
            x_request_id = self.av.get_x_request_id()
            raise UpYunServiceException(x_request_id, status_code, tasks, None)

    def verify_sign(self, callback_dict):
        av = AvPretreatment(self.username, self.password, self.bucket)
        cv = CallbackValidation(callback_dict, av)
        if cv.verify_sign():
            print "signature verify success"
            return True
        else:
            print "signature verify failed"
            return False

    # --- private API

    def __do_http_request(self, method, key,
                          value=None, headers=None, of=None, args='',
                          stream=False, handler=None, params=None):

        _uri = "/%s/%s" % (self.bucket, key if key[0] != '/' else key[1:])
        uri = "%s%s" % (quote(encode_msg(_uri), safe='~/'), args)

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

        return self.hp.do_http_pipe(method, self.endpoint, uri, value, headers, of,
                                stream, handler, params)

    def __make_user_agent(self):
        default = "upyun-python-sdk/%s" % __version__

        return self.hp.do_user_agent(default)

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

    def __get_multi_meta_headers(self, headers):
        sys_headers = ['last_modified', 'signature', 'bucket_name', 'path']
        for item in sys_headers:
            if item in headers.keys():
                del headers[item]
        return headers

    def __set_auth_headers(self, playload,
                           method=None, length=0, headers=None):
        if headers is None:
            headers = []
        # Date Format: RFC 1123
        dt = httpdate_rfc1123(datetime.datetime.utcnow())
        signature = self.hp.make_signature(self.bucket, self.username, self.password,
                                                method, playload, dt, length)

        headers['Date'] = dt
        headers['Authorization'] = signature
        if self.user_agent:
            headers['User-Agent'] = self.user_agent
        else:
            headers['User-Agent'] = self.__make_user_agent()
        return headers

if __name__ == '__main__':
    pass

# -*- coding: utf-8 -*-
import os

from .modules.sign import make_rest_signature,\
    make_content_md5, encode_msg
from .modules.exception import UpYunClientException
from .modules.compat import b, str, quote, urlencode, builtin_str
from .modules.httpipe import cur_dt


def get_fileobj_size(fileobj):
    try:
        if hasattr(fileobj, 'fileno'):
            return os.fstat(fileobj.fileno()).st_size
    except IOError:
        pass

    return len(fileobj.getvalue())


class UploadObject(object):
    def __init__(self, fileobj, chunksize=None, handler=None, params=None):
        self.fileobj = fileobj
        self.chunksize = chunksize
        self.totalsize = get_fileobj_size(fileobj)
        self.readsofar = 0
        if handler:
            self.hdr = handler(self.totalsize, params)

    def __iter__(self):
        return self

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


class UpYunRest(object):
    def __init__(self, bucket, username, password,
                 endpoint, chunksize, hp):
        self.bucket = bucket
        self.username = username
        self.password = password
        self.chunksize = chunksize
        self.endpoint = endpoint
        self.hp = hp

    # --- public API
    def usage(self, key):
        res = self.__do_http_request('GET', key, args='?usage')
        return str(int(res))

    def put(self, key, value, checksum, headers, handler, params, secret):
        '''
        >>> with open('foo.png', 'rb') as f:
        >>>    res = up.put('/path/to/bar.png', f, checksum=False,
        >>>                 headers={'x-gmkerl-rotate': '180'}})
        '''
        if headers is None:
            headers = {}

        if isinstance(value, str):
            value = b(value)

        if checksum is True:
            headers['Content-MD5'] = make_content_md5(value, self.chunksize)

        if secret:
            headers['Content-Secret'] = secret

        if handler and hasattr(value, 'fileno'):
            value = UploadObject(value, chunksize=self.chunksize,
                                 handler=handler, params=params)

        h = self.__do_http_request('PUT', key, value, headers)
        return self.__get_meta_headers(h)

    def get(self, key, value, handler, params):
        '''
        >>> with open('bar.png', 'wb') as f:
        >>>    up.get('/path/to/bar.png', f)
        '''
        return self.__do_http_request('GET', key, of=value, stream=True,
                                      handler=handler, params=params)

    def delete(self, key):
        self.__do_http_request('DELETE', key)

    def mkdir(self, key):
        headers = {'Folder': 'true'}
        self.__do_http_request('POST', key, headers=headers)

    def getlist(self, key):
        content = self.__do_http_request('GET', key)
        if content == '':
            return []
        items = content.split('\n')
        return [dict(zip(['name', 'type', 'size', 'time'],
                x.split('\t'))) for x in items]

    def getinfo(self, key):
        h = self.__do_http_request('HEAD', key)
        return self.__get_meta_headers(h)

    def purge(self, keys, domain):
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
        params = urlencode({'purge': urlstr})
        headers = {'Content-Type': 'application/x-www-form-urlencoded',
                   'Accept': 'application/json'}
        self.__set_auth_headers(urlstr, headers=headers)

        resp = self.hp.do_http_pipe(method, host, uri,
                                    value=params, headers=headers)
        content = self.__handle_resp(resp, method, uri=uri)
        invalid_urls = content['invalid_domain_of_url']
        return [k[7 + len(domain):] for k in invalid_urls if k]

    # --- private API
    def __do_http_request(self, method, key,
                          value=None, headers=None, of=None, args='',
                          stream=False, handler=None, params=None):
        _uri = '/%s/%s' % (self.bucket, key if key[0] != '/' else key[1:])
        uri = '%s%s' % (quote(encode_msg(_uri), safe='~/'), args)

        if headers is None:
            headers = {}

        length = 0
        if hasattr(value, '__len__'):
            length = len(value)
            headers['Content-Length'] = length
        elif hasattr(value, 'fileno'):
            length = get_fileobj_size(value)
            headers['Content-Length'] = length
            # [ugly]:compatible with newest requests feature
            # force the stream upload with empty file to normal upload
            if not length:
                value = ''
        elif value is not None:
            raise UpYunClientException('object type error')

        self.__set_auth_headers(uri, method, length, headers)

        resp = self.hp.do_http_pipe(method, self.endpoint, uri,
                                    value, headers, stream)
        return self.__handle_resp(resp, method, of, handler, params)

    def __handle_resp(self, resp, method=None, of=None,
                      handler=None, params=None, uri=None):
        content = None
        try:
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
            elif method == 'GET':
                content = resp.text
            elif method == 'PUT' or method == 'HEAD':
                content = resp.headers.items()
            elif method == 'POST' and uri == '/purge/':
                content = resp.json()
        except Exception as e:
            raise UpYunClientException(e)
        return content

    def __get_meta_headers(self, headers):
        return dict((k[8:].lower(), v) for k, v in headers
                    if k[:8].lower() == 'x-upyun-' and
                    k[8:].lower() != 'uuid' and
                    k[8:].lower() != 'cluster')

    def __set_auth_headers(self, playload,
                           method=None, length=0, headers=None):
        if headers is None:
            headers = []

        dt = cur_dt()
        signature = make_rest_signature(self.bucket, self.username,
                                        self.password, method, playload,
                                        dt, length)

        headers['Authorization'] = signature
        return headers

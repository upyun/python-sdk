#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import stat
import socket
import httplib
import hashlib
import datetime


__version__ = "2.0"


ED_LIST = ['v%d.api.upyun.com' % ed for ed in range(4)]
ED_AUTO, ED_TELECOM, ED_CNC, ED_CTT = ED_LIST


class UpYunServiceException(Exception):
    def __init__(self, status, msg):
        self.args = (status, msg)
        self.status = status
        self.msg = msg


class UpYunClientException(Exception):
    def __init__(self, msg):
        self.args = (msg)
        self.msg = msg


class UpYun:

    def __init__(self, bucket, username, password,
                 timeout=None, endpoint=None):
        self.bucket = bucket
        self.username = username
        self.password = hashlib.md5(password).hexdigest()
        self.timeout = timeout or 60
        self.endpoint = endpoint or ED_AUTO

    @property
    def endpoint(self):
        return self.endpoint

    @endpoint.setter
    def endpoint(self, endpoint):
        self.endpoint = endpoint

    def usage(self, key='/'):
        return self.__do_http_request('GET', key + '?usage')

    def put(self, key, value, checksum=False, headers=None):
        if headers is None:
            headers = {}
        headers['Mkdir'] = 'true'
        if checksum is True:
            headers['Content-MD5'] = self.__make_content_md5(value)
        h = self.__do_http_request('PUT', key, value, headers)

        return self.__get_meta_headers(h)

    def get(self, key, value=None):
        return self.__do_http_request('GET', key, of=value)

    def delete(self, key):
        self.__do_http_request('DELETE', key)

    def mkdir(self, key):
        headers = {'Folder': 'true'}
        self.__do_http_request('POST', key, headers=headers)

    def getlist(self, key='/'):
        content = self.__do_http_request('GET', key)
        items = content.split('\n')
        return [dict(zip(['name', 'type', 'size', 'time'],
                x.split('\t'))) for x in items]

    def getinfo(self, key):
        h = self.__do_http_request('HEAD', key)
        return self.__get_meta_headers(h)

    def __do_http_request(self, method, key,
                          value=None, headers=None, of=None):
        if key[0] != '/':
            key = '/' + key
        uri = '/' + self.bucket + key

        try:
            connection = httplib.HTTPConnection(self.endpoint, 80,
                                                timeout=self.timeout)
        except (httplib.HTTPException, socket.error) as e:
            raise UpYunClientException(str(e))

        if headers is None:
            headers = {}

        length = 0
        if isinstance(value, file):
            length = os.fstat(value.fileno())[stat.ST_SIZE]
        elif isinstance(value, str):
            length = len(value)
            headers['Content-Length'] = length
        elif value is not None:
            raise UpYunClientException("TypeError")

        # Date Format: RFC 1123
        dt = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        signature = self.__make_signature(method, uri, dt, length)

        headers['Date'] = dt
        headers['Authorization'] = signature
        headers['Connection'] = "close"

        try:
            connection.request(method, uri, value, headers)
            response = connection.getresponse()
        except (httplib.HTTPException, socket.error) as e:
            raise UpYunClientException(str(e))

        res = None
        status = response.status
        if status == 200:
            if method == "GET":
                if of is None:
                    res = response.read()
                else:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        of.write(chunk)
            elif method == "PUT" or method == "HEAD":
                res = response.getheaders()
        else:
            err = response.read()
            raise UpYunServiceException(status, err)

        if connection:
            connection.close()
        return res

    def __make_signature(self, method, uri, date, length):
        signstr = '&'.join([method, uri, date, str(length), self.password])
        signature = hashlib.md5(signstr).hexdigest()
        return 'UpYun ' + self.username + ':' + signature

    def __make_content_md5(self, value):
        if isinstance(value, file):
            md5 = hashlib.md5()
            for chunk in iter(lambda: value.read(8192), b''):
                md5.update(chunk)
            value.seek(0)
            return md5.hexdigest()
        elif isinstance(value, str):
            return hashlib.md5(value).hexdigest()
        else:
            raise UpYunClientException("TypeError")

    def __get_meta_headers(self, headers):
        return dict(iter([(k[8:].lower(), v) for k, v in headers
                    if k[:8].lower() == 'x-upyun-']))

if __name__ == '__main__':
    pass

# -*- coding: utf-8 -*-

import httplib
import json
import socket

from compat import b
from exception import UpYunServiceException, UpYunClientException
from sign import decode_msg

HUMAN_MODE = False

try:
    import requests
    HUMAN_MODE = True
except ImportError:
    pass

class UpYunHttp(object):
    def __init__(self, human, timeout, chunksize):
        self.human_mode = HUMAN_MODE
        self.timeout = timeout
        if not human:
            self.human_mode = False
        if self.human_mode:
            self.session = requests.Session()
        self.chunksize = chunksize

    def do_http_pipe(self, method, host, uri,
                            value=None, headers=None, of=None, stream=False,
                            handler=None, params=None):
        # http://docs.python-requests.org/
        if self.human_mode:
            request_id, content, msg, err, status = None, None, None, None, None
            URL = "http://%s%s" % (host, uri)
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
                    elif method == 'POST' and uri == '/purge/':
                        content = resp.json()
                    elif method == 'POST' and host == 'm0.api.upyun.com':
                        content = resp.json()
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

        else:
        # http://docs.python.org/2/library/httplib.html

            request_id, content, msg, err, status = None, None, None, None, None
            try:
                conn = httplib.HTTPConnection(host, timeout=self.timeout)
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
                    elif method == 'GET' and of is None:
                        content = decode_msg(resp.read())
                    elif method == 'PUT' or method == 'HEAD':
                        content = resp.getheaders()
                    elif method == 'POST'and uri == '/purge/':
                        content = json.loads(decode_msg(resp.read()))
                else:
                    msg = resp.reason
                    err = decode_msg(resp.read())

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

    def do_user_agent(self, default):
        if self.human_mode:
            return (default, requests.utils.default_user_agent())
        else:
            return default


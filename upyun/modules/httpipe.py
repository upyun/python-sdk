# -*- coding: utf-8 -*-

import json
import socket
import uuid
import mimetypes

from .compat import httplib, b
from .exception import UpYunServiceException, UpYunClientException
from .sign import decode_msg

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
                            handler=None, params=None, kind=None):
        if self.human_mode:
            return self.do_http_human(method, host, uri, value, headers, 
                                            of, stream,handler, params, kind)
        else:
            return self.do_http_basic(method, host, uri, value, headers, 
                                            of, stream,handler, params, kind)


    # http://docs.python-requests.org/
    def do_http_human(self, method, host, uri,
                            value, headers, of, stream,
                            handler, params, kind):
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
                elif kind == 'rest':
                    if method == 'GET':
                        content = resp.text
                    elif method == 'PUT' or method == 'HEAD':
                        content = resp.headers.items()
                    elif method == 'POST' and uri == '/purge/':
                        content = resp.json()

                elif kind == 'av':
                    if method == 'GET':
                        content = resp.json()
                    elif method == 'POST':
                        content = resp.text

                elif kind == 'multi':
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

    # http://docs.python.org/2/library/httplib.html
    def do_http_basic(self, method, host, uri,
                            value, headers, of, stream,
                            handler, params, kind):
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
                elif kind == 'rest':
                    if method == 'GET':
                        content = decode_msg(resp.read())
                    elif method == 'PUT' or method == 'HEAD':
                        content = resp.getheaders()
                    elif method == 'POST' and uri == '/purge/':
                        content = json.loads(decode_msg(resp.read()))

                elif kind == 'av':
                    if method == 'GET':
                        content = json.loads(decode_msg(resp.read()))
                    elif method == 'POST':
                        content = decode_msg(resp.read())

                elif kind == 'multi':
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

    def do_http_multipart(self, host, uri, value, filename):
        kind = 'multi'
        file_type = mimetypes.guess_type(decode_msg(filename))[0]
        if not file_type:
            file_type = "text/plain; charset=utf-8"
        #start construct multipart request
        delimiter = '-------------' + str(uuid.uuid1())
        data = []
        for k, v in value.items():
            data.append("--{0}".format(delimiter))
            if type(v) == dict:
                s = 'Content-Disposition: form-data; name="{0}"; filename="{1}"'\
                                .format(k, filename)
                data.append(s)
                s = 'Content-Type: {0}\r\n'.format(file_type)
                data.append(s)
                data.append(v['data'])
            else:
                s = 'Content-Disposition: form-data; name="{0}"\r\n'.format(k)
                data.append(s)
                data.append(v)
        data.append("--{0}--".format(delimiter))

        #change data item from str to bytes
        data = [b(k) for k in data]

        value = b("\r\n").join(data)
        #end construct multipart request

        headers = {'Content-Type': 'multipart/form-data; boundary={0}'.format(delimiter),
                            'Content-Length': len(value)}

        return self.do_http_pipe('POST', host, uri, headers=headers, value=value, kind=kind)

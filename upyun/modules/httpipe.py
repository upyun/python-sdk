# -*- coding: utf-8 -*-

import uuid
import requests

from .compat import b
from .exception import UpYunServiceException, UpYunClientException
from .sign import decode_msg

class UpYunHttp(object):
    def __init__(self, timeout):
        self.timeout = timeout
        self.session = requests.Session()

    # http://docs.python-requests.org/
    def do_http_pipe(self, method, host, uri,
                           value=None, headers=None, stream=False, files=None):
        request_id, msg, err, status = [None] * 4
        url = "http://%s%s" % (host, uri)
        requests.adapters.DEFAULT_RETRIES = 5
        try:
            resp = self.session.request(method, url, data=value,
                                        headers=headers, stream=stream,
                                        timeout=self.timeout, files=files)
            resp.encoding = 'utf-8'
            try:
                request_id = resp.headers["X-Request-Id"]
            except KeyError:
                request_id = "Unknown"
            status = resp.status_code

            if status / 100 != 2:
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

        return resp  

# -*- coding: utf-8 -*-
import os
import time

from .modules.exception import UpYunClientException
from .modules.sign import make_content_md5, make_policy
from .modules.compat import b


class FormUpload(object):
    def __init__(self, bucket, secret, endpoint, hp):
        self.bucket = bucket
        self.secret = secret
        self.hp = hp
        self.host = endpoint
        self.uri = '/%s/' % bucket

    def upload(self, key, value, expiration, **kwargs):
        expiration = expiration or 1800
        expiration += int(time.time())

        data = {'bucket': self.bucket,
                'expiration': expiration,
                'save-key': key,
                }
        data.update(kwargs)
        policy = make_policy(data)
        signature = make_content_md5(policy + b('&') + b(self.secret))
        postdata = {'policy': policy,
                    'signature': signature,
                    'file': (os.path.basename(value.name), value),
                    }
        resp = self.hp.do_http_pipe('POST', self.host, self.uri,
                                    files=postdata)
        return self.__handle_resp(resp)

    def __handle_resp(self, resp):
        content = None
        try:
            content = resp.json()
        except Exception as e:
            raise UpYunClientException(e)
        return content

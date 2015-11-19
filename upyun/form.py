# -*- coding: utf-8 -*-

import time

from .modules.exception import UpYunClientException
from .modules.sign import make_content_md5, make_policy, decode_msg, encode_msg
from .modules.compat import b, str

class FormUpload(object):
    def __init__(self, bucket, secret, hp, endpoint):
        self.bucket = bucket
        self.secret = secret
        self.hp = hp
        self.host = endpoint
        self.uri = "/%s/" % bucket

    def upload(self, key, value, expiration):
        expiration = expiration or 1800
        expiration += int(time.time())

        #check value type
        if hasattr(value, 'fileno'):
            value = value.read()
        elif type(value) != "str":
            raise UpYunClientException("Unrecognize type of value to be uploaded")

        data = {"bucket": self.bucket,
                "expiration": expiration,
                "save-key": key,
                }
        policy = make_policy(data)
        signature = make_content_md5(policy + b("&") + b(self.secret))

        postdata = {'policy': policy,
                    'signature': signature,
                    'file': value,
                    }
        resp = self.hp.do_http_pipe('POST', self.host, self.uri, files=postdata)
        return self.__handle_resp(resp)

    def __handle_resp(self, resp):
        try:
            content = resp.json()
        except Exception as e:
            raise UpYunClientException(str(e))
        return content

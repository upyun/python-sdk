# -*- coding: utf-8 -*-

import json
import time
import base64
import os

from .modules.exception import UpYunClientException
from .modules.sign import make_content_md5, make_policy, decode_msg, encode_msg
from .modules.compat import b, str

class FormUpload(object):
    def __init__(self, bucket, secret, hp, endpoint):
        self.bucket = bucket
        self.secret = secret
        self.hp = hp
        self.host = endpoint

    def upload(self, key, value, expiration):
        expiration = int(expiration or 1800)
        expiration += int(time.time())
        filename = encode_msg(os.path.basename(value.name))
        value = self.__check_value(value)
        data = {"bucket": self.bucket, "expiration": expiration,
                            "save-key": key}
        policy = make_policy(data)
        signature = self.__create_signature(policy)
        postdata = {'policy': policy, 'signature': signature,
                                            'file': {'data': value}}
        return self.__do_http_request(postdata, filename)

    def __check_value(self, value):
        if hasattr(value, 'fileno'):
            return value.read()
        if type(value) == "str":
            return value
        else:
            raise UpYunClientException("Unrecognize type of value to be uploaded")

    def __create_signature(self, policy):
        signature = policy + b("&") + b(self.secret)
        return make_content_md5(signature)

    def __do_http_request(self, value, filename):
        resp, human, conn = None, None, None
        uri = "/%s/" % self.bucket
        resp, human, conn = self.hp.do_http_multipart(self.host, uri, value, filename)
        return self.__handle_resp(resp, human, conn)

    def __handle_resp(self, resp, human, conn):
        content = None
        try:
            if human:
                content = resp.json()
            else:
                content = json.loads(decode_msg(resp.read()))
        except Exception as e:
            raise UpYunClientException(str(e))
        finally:
            if conn:
                conn.close()
        return content

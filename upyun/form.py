# -*- coding: utf-8 -*-

import json
import time
import base64
import os

from modules.exception import UpYunClientException
from modules.sign import make_content_md5, make_policy

class FormUpload(object):
    def __init__(self, bucket, secret, hp, endpoint):
        self.bucket = bucket
        self.secret = secret
        self.hp = hp
        self.host = endpoint
        self.filename = None

    def upload(self, key, value, expiration):
        self.filename = os.path.basename(value.name).encode('utf-8')
        expiration += (int)(time.time())
        value = self.__check_value(value)
        data = {"bucket": self.bucket, "expiration": expiration,
                            "save-key": key}
        policy = make_policy(data)
        signature = self.__create_signature(policy)
        postdata = {'policy': policy, 'signature': signature,
                                            'file': {'data': value}}
        return self.__do_http_request(postdata)

    def __check_value(self, value):
        if hasattr(value, 'fileno'):
            return value.read()
        if type(value) == "str":
            return value
        else:
            raise UpYunClientException("Unrecognize type of value to be uploaded")

    def __create_signature(self, policy):
        signature = policy + "&" + self.secret
        return make_content_md5(signature)

    def __do_http_request(self, value):
        uri = "/%s/" % self.bucket
        return self.hp.do_http_multipart(self.host, uri, value, self.filename)

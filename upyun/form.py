# -*- coding: utf-8 -*-

from cStringIO import StringIO
import json
import time
import base64

from modules.exception import UpYunServiceException, UpYunClientException
from modules.sign import make_content_md5

class FormUpload(object):
    def __init__(self, key, value, bucket, secret, hp):
        self.remote_path = key
        self.value = value
        self.bucket = bucket
        self.secret = secret
        self.hp = hp
        self.host = "v0.api.upyun.com"
        self.expiration = (int)(time.time()) + 3600

    def upload(self):
        value = self.__check_value(self.value)
        data = {"bucket": self.bucket, "expiration": self.expiration, 
                            "save-key": self.remote_path}
        policy = self.__create_policy(data)
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

    def __create_policy(self, data):
        if type(data) == dict:
            policy = json.dumps(data)
            return base64.b64encode(policy)
        else:
            return None

    def __create_signature(self, policy):
        signature = policy + "&" + self.secret
        return make_content_md5(signature)

    def __do_http_request(self, value):
        uri = "/%s/" % self.bucket
        return self.hp.do_http_multipart(self.host, uri, value)

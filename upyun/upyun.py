# -*- coding: utf-8 -*-

#######NOTICE AV CLASS

import hashlib

from exception import UpYunServiceException, UpYunClientException
from compat import b
from av import *
from rest import UpYunRest
from av import AvPretreatment, CallbackValidation

__version__ = '2.3.0'

ED_LIST = ("v%d.api.upyun.com" % ed for ed in range(4))
ED_AUTO, ED_TELECOM, ED_CNC, ED_CTT = ED_LIST

DEFAULT_CHUNKSIZE = 8192
DEFAULT_BLOCKSIZE = 1024*1024

class UpYun(object):
    def __init__(self, bucket, username, password,
                    timeout=None, endpoint=None, chunksize=None, human=True):
        super(UpYun, self).__init__()
        self.bucket = bucket
        self.username = username
        self.password = hashlib.md5(b(password)).hexdigest()
        self.timeout = timeout or 60
        self.endpoint = endpoint or ED_AUTO
        self.chunksize = chunksize or DEFAULT_CHUNKSIZE
        self.human = human
        self.up_rest = UpYunRest(self.bucket, self.username, self.password,
                                            self.timeout, self.endpoint, 
                                            self.chunksize, self.human)

    # --- public rest API
    def usage(self, key='/'):
        return self.up_rest.usage(key)

    def put(self, key, value, checksum=False, headers=None,
                handler=None, params=None, multipart=False, 
                secret=None, block_size=DEFAULT_BLOCKSIZE):
        if multipart and not secret:
            raise UpYunClientException("You have to specify form secret with\
                                        multipart upload method")

        return self.up_rest.put(key, value, checksum, headers,
                                    handler, params, multipart,
                                    secret, block_size)

    def get(self, key, value=None, handler=None, params=None):
        return self.up_rest.get(key, value, handler, params)

    def delete(self, key):
        self.up_rest.delete(key)

    def mkdir(self, key):
        self.up_rest.mkdir(key)

    def getlist(self, key='/'):
        return self.up_rest.getlist(key)

    def getinfo(self, key):
        return self.up_rest.getinfo(key)

    def purge(self, keys, domain=None):
        return self.up_rest.purge(keys, domain)

    # --- video pretreatment API

    def pretreat(self, tasks, source, notify_url=""):
        av = AvPretreatment(self.username, self.password, self.bucket, 
                                    self.chunksize, self.human, self.timeout)

        return av.pretreat(tasks, source, notify_url)

    def status(self, taskids):
        av = AvPretreatment(self.username, self.password, self.bucket, 
                                    self.chunksize, self.human, self.timeout)
        return av.status(taskids)

    def verify_sign(self, callback_dict):
        av = AvPretreatment(self.username, self.password, self.bucket, 
                                    self.chunksize, self.human, self.timeout)
        cv = CallbackValidation(callback_dict, av)
        return cv.verify_sign()

if __name__ == '__main__':
    pass

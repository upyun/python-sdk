# -*- coding: utf-8 -*-

import hashlib

from .rest import UpYunRest
from .av import AvPretreatment, CallbackValidation

from .modules.exception import UpYunClientException
from .modules.compat import b

__version__ = '2.3.0'

ED_LIST = ("v%d.api.upyun.com" % ed for ed in range(4))
ED_AUTO, ED_TELECOM, ED_CNC, ED_CTT = ED_LIST

DEFAULT_CHUNKSIZE = 8192

class UpYun(object):
    def __init__(self, bucket, username, password,
                    secret=None, timeout=None, endpoint=None,
                    chunksize=None, mp_endpoint=None):
        super(UpYun, self).__init__()
        self.bucket = bucket
        self.username = username
        self.password = hashlib.md5(b(password)).hexdigest()
        self.timeout = timeout or 60
        self.endpoint = endpoint or ED_AUTO
        self.chunksize = chunksize or DEFAULT_CHUNKSIZE
        self.secret = secret
        self.up_rest = UpYunRest(self.bucket, self.username, self.password,
                                        self.secret, self.timeout, self.endpoint,
                                        self.chunksize, mp_endpoint)
        self.av = AvPretreatment(self.bucket, self.username, self.password,
                                        self.chunksize, self.timeout)

    # --- public rest API
    def usage(self, key='/'):
        return self.up_rest.usage(key)

    def put(self, key, value, checksum=False, headers=None,
                handler=None, params=None, multipart=False,
                block_size=None, form=False, expiration=None,
                secret=None, retry=None):
        if (multipart or form) and not self.secret:
            raise UpYunClientException("You have to specify form secret with " +
                                        "multipart upload method")

        #rest > form > multipart
        if multipart and form:
            multipart = False

        return self.up_rest.put(key, value, checksum, headers,
                                    handler, params, multipart,
                                    block_size, form, expiration, secret)

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
        return self.av.pretreat(tasks, source, notify_url)

    def status(self, taskids):
        return self.av.status(taskids)

    # --- no use yet, need developing

    def verify_sign(self, callback_dict):
        cv = CallbackValidation(callback_dict, self.av)
        return cv.verify_sign()

if __name__ == '__main__':
    pass

# -*- coding: utf-8 -*-

#######NOTICE AV CLASS

import hashlib

from exception import UpYunServiceException, UpYunClientException
from AvPretreatment import *
from rest import UpYunRest

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
        self.av = AvPretreatment(self.username, self.password, self.bucket, self.timeout, 
                                    notify_url=notify_url, tasks=tasks, source=source)
        ids = self.av.run()
        # means something error happend
        if type(ids) != list:
            status_code = self.av.get_status_code()
            x_request_id = self.av.get_x_request_id()
            raise UpYunServiceException(x_request_id, status_code, ids, None)
        return ids

    def status(self, taskids=None):
        if taskids:
            self.av = AvPretreatment(self.username, self.password, self.bucket,
                                        self.timeout, taskids=taskids)
            tasks = self.av.get_tasks_status()
        else:
            if self.av:
                tasks = self.av.get_tasks_status()
            else:
                raise UpYunClientException('You should specify taskid')

        if type(tasks) == dict:
            return tasks
        else:
            status_code = self.av.get_status_code()
            x_request_id = self.av.get_x_request_id()
            raise UpYunServiceException(x_request_id, status_code, tasks, None)

    def verify_sign(self, callback_dict):
        av = AvPretreatment(self.username, self.password, self.bucket)
        cv = CallbackValidation(callback_dict, av)
        if cv.verify_sign():
            print "signature verify success"
            return True
        else:
            print "signature verify failed"
            return False

if __name__ == '__main__':
    pass

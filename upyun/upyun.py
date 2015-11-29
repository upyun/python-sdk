# -*- coding: utf-8 -*-
import hashlib
import json

from .rest import UpYunRest
from .form import FormUpload
from .multi import Multipart
from .av import AvPretreatment, CallbackValidation

from .modules.exception import UpYunClientException
from .modules.compat import b
from .modules.sign import make_content_md5, encode_msg

__version__ = '2.3.0'

ED_LIST = ('v%d.api.upyun.com' % ed for ed in range(4))
ED_AUTO, ED_TELECOM, ED_CNC, ED_CTT = ED_LIST

DEFAULT_CHUNKSIZE = 8192

class UpYun(object):
    def __init__(self, bucket, username, password, secret=None,
                    timeout=None, endpoint=None, chunksize=None):
        super(UpYun, self).__init__()
        self.bucket = bucket
        self.username = username
        self.password = hashlib.md5(b(password)).hexdigest()
        self.endpoint = endpoint or ED_AUTO
        self.chunksize = chunksize or DEFAULT_CHUNKSIZE
        self.secret = secret
        self.timeout = timeout or 60
        self.up_rest = UpYunRest(self.bucket, self.username,
                                        self.password, self.timeout,
                                        self.endpoint, self.chunksize)
        self.av = AvPretreatment(self.bucket, self.username, self.password,
                                        self.chunksize, self.timeout)
        if self.secret:
            self.up_multi = Multipart(self.bucket, self.secret,
                                        self.timeout, self.endpoint)
            self.up_form = FormUpload(self.bucket, self.secret,
                                        self.timeout, self.endpoint)

    # --- public rest API
    def usage(self, key='/'):
        return self.up_rest.usage(key)

    def put(self, key, value, checksum=False, headers=None,
                  handler=None, params=None,secret=None,
                  multipart=False, block_size=None, form=False,
                  expiration=None, kwargs={}):
        if (multipart or form) and not self.secret:
            raise UpYunClientException('You have to specify form secret with '
                                       'multipart upload method')

        #priority: rest > form > multipart
        if form and hasattr(value, 'fileno'):
            return self.up_form.upload(key, value, expiration, kwargs)
        if multipart and hasattr(value, 'fileno'):
            return self.up_multi.upload(key, value,
                                        block_size, expiration, kwargs)
        return self.up_rest.put(key, value, checksum,
                                     headers, handler, params, secret)

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
    def pretreat(self, tasks, source, notify_url=''):
        return self.av.pretreat(tasks, source, notify_url)

    def status(self, taskids):
        return self.av.status(taskids)

# --- no use yet, need developing
def verify_put_sign(value, secret):
    keys = ['code', 'message', 'url', 'time',
            'form_api_secret', 'ext-param',]
    data = []

    if not isinstance(value, dict):
        value = json.loads(value)
    if 'no-sign' in value:
        value['form_api_secret'] = ''
        sign = value['no-sign']
    else:
        value['form_api_secret'] = secret
        sign = value['sign']
    for k in keys:
        if k == 'url':
            data.append(encode_msg(value[k]))
        elif k in value:
            data.append(str(value[k]))
    signature = '&'.join(data)
    return sign == make_content_md5(b(signature))

    #cv = CallbackValidation(callback_dict, self.av)
    #return cv.verify_sign()

if __name__ == '__main__':
    pass

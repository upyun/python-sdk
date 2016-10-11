# -*- coding: utf-8 -*-
import hashlib
import json
import os

from .rest import UpYunRest
from .form import FormUpload
from .multi import Multipart
from .av import AvPretreatment

from .modules.httpipe import UpYunHttp
from .modules.exception import UpYunClientException
from .modules.compat import b, builtin_str
from .modules.sign import make_content_md5, encode_msg
from .modules.check import has_object

__version__ = '2.4.1'

ED_LIST = ('v%d.api.upyun.com' % ed for ed in range(4))
ED_AUTO, ED_TELECOM, ED_CNC, ED_CTT = ED_LIST

DEFAULT_CHUNKSIZE = 8192


class UpYun(object):
    def __init__(self, bucket, username=None, password=None, secret=None,
                 timeout=None, endpoint=None, chunksize=None, debug=False,
                 read_timeout=None):
        super(UpYun, self).__init__()
        self.bucket = bucket or os.getenv('UPYUN_BUCKET')
        self.username = username or os.getenv('UPYUN_USERNAME')
        password = password or os.getenv('UPYUN_PASSWORD')
        self.password = (hashlib.md5(b(password)).hexdigest()
                         if password else None)
        self.endpoint = endpoint or ED_AUTO
        self.chunksize = chunksize or DEFAULT_CHUNKSIZE
        self.secret = secret or os.getenv('UPYUN_SECRET')
        self.timeout = timeout or 60
        if read_timeout is not None:
            self.requests_timeout = (self.timeout, read_timeout)
        else:
            self.requests_timeout = self.timeout
        self.hp = UpYunHttp(self.requests_timeout, debug)

        if self.username and self.password:
            self.up_rest = UpYunRest(self.bucket, self.username,
                                     self.password, self.endpoint,
                                     self.chunksize, self.hp)
            self.av = AvPretreatment(self.bucket, self.username,
                                     self.password, self.chunksize,
                                     self.hp)
        if self.secret:
            self.up_multi = Multipart(self.bucket, self.secret,
                                      self.endpoint, self.hp)
            self.up_form = FormUpload(self.bucket, self.secret,
                                      self.endpoint, self.hp)

        if debug:
            self.__init_debug_log(bucket=bucket, username=username,
                                  password=password, secret=secret,
                                  timeout=timeout, endpoint=endpoint,
                                  chunksize=chunksize, debug=debug)

    def __init_debug_log(self, **kwargs):
        with open('debug.log', 'w') as f:
            f.write('### Running in debug mode ###\n\n\n')
            f.write('## Initial params ##\n\n')
            f.write('\n'.join(map(lambda kv: '%s: %s'
                              % (kv[0], kv[1]), kwargs.items())))

    @has_object('up_rest')
    def set_endpoint(self, endpoint, host=None):
        self.up_rest.endpoint = endpoint
        self.up_rest.host = host or ED_AUTO

    # --- public rest API
    @has_object('up_rest')
    def usage(self, key='/'):
        return self.up_rest.usage(key)

    def put(self, key, value, checksum=False, headers=None,
            handler=None, params=None, secret=None,
            need_resume=True, store=None, reporter=None,
            multipart=False, block_size=None, form=False,
            expiration=None, **kwargs):
        if (multipart or form) and not self.secret:
            raise UpYunClientException('You have to specify form secret with '
                                       'multipart upload method')

        # - priority: rest > form > multipart
        if form and hasattr(value, 'fileno'):
            return self.up_form.upload(key, value, expiration, **kwargs)
        if multipart and hasattr(value, 'fileno'):
            return self.up_multi.upload(key, value,
                                        block_size, expiration, **kwargs)
        return self.up_rest.put(
            key, value, checksum, headers, handler,
            params, secret, need_resume, store, reporter)

    @has_object('up_rest')
    def get(self, key, value=None, handler=None, params=None):
        return self.up_rest.get(key, value, handler, params)

    @has_object('up_rest')
    def delete(self, key):
        self.up_rest.delete(key)

    @has_object('up_rest')
    def mkdir(self, key):
        self.up_rest.mkdir(key)

    @has_object('up_rest')
    def getlist(self, key='/'):
        return self.up_rest.getlist(key)

    @has_object('up_rest')
    def getinfo(self, key):
        return self.up_rest.getinfo(key)

    @has_object('up_rest')
    def purge(self, keys, domain=None):
        return self.up_rest.purge(keys, domain)

    # --- video pretreatment API
    @has_object('av')
    def pretreat(self, tasks, source, notify_url=''):
        return self.av.pretreat(tasks, source, notify_url)

    @has_object('av')
    def status(self, taskids):
        return self.av.status(taskids)

    @has_object('av')
    def verify_tasks(self, value):
        return self.av.verify_tasks(value)

    # --- depress task
    @has_object('av')
    def depress(self, tasks, notify_url):
        for task in tasks:
            save_as = task.get('save_as')
            sources = task.get('sources')
            for key in (sources, save_as):
                if type(key) != str or key == '':
                    raise UpYunClientException('Given not correct %s '
                                               'in task' % key)
        return self.av.pretreat(tasks, 'upyun', notify_url, 'depress')

    # --- compress task
    @has_object('av')
    def compress(self, tasks, notify_url):
        for task in tasks:
            save_as = task.get('save_as')
            sources = task.get('sources')
            if type(save_as) != str or save_as == '':
                raise UpYunClientException('Given not correct save_as in task')
            if type(sources) != list or len(sources) == 0:
                raise UpYunClientException('Given not correct sources in task')
        return self.av.pretreat(tasks, 'upyun', notify_url, 'compress')

    @has_object('av')
    def put_tasks(self, tasks, notify_url, app_name):
        return self.av.pretreat(tasks, '', notify_url, app_name)


# --- no use yet, need developing
def verify_put_sign(value, secret):
    KEYS = ['code', 'message', 'url', 'time',
            'form_api_secret', 'ext-param', ]
    data = []

    if not isinstance(value, dict):
        value = json.loads(value)
    if 'no-sign' in value:
        value['form_api_secret'] = ''
        sign = value['no-sign']
    else:
        value['form_api_secret'] = secret
        sign = value['sign']
    for k in KEYS:
        if k == 'url':
            data.append(encode_msg(value[k]))
        elif k in value:
            data.append(b(builtin_str(value[k])))
    signature = b'&'.join(data)
    return sign == make_content_md5(signature)

if __name__ == '__main__':
    pass

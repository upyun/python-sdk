# -*- coding: utf-8 -*-

import json
import base64

from .modules.compat import urlencode, b
from .modules.exception import UpYunClientException, UpYunServiceException
from .modules.sign import make_av_signature, decode_msg


class AvPretreatment(object):
    HOST = 'p0.api.upyun.com'
    PRETREAT = '/pretreatment/'
    STATUS = '/status/'
    KEYS = ['bucket_name',
            'status_code',
            'path',
            'description',
            'task_id',
            'info',
            'signature',
            ]

    def __init__(self, bucket, operator, password,
                 chunksize, hp):
        self.bucket = bucket
        self.operator = operator
        self.password = password
        self.chunksize = chunksize
        self.hp = hp

    # --- public API
    def pretreat(self, tasks, source, notify_url, app_name=None):
        data = {'bucket_name': self.bucket, 'source': source,
                'notify_url': notify_url, 'tasks': tasks,
                'app_name': app_name}
        if not app_name:
            data.pop('app_name')
        return self.__requests_pretreatment(data)

    def status(self, taskids):
        data = {}
        if type(taskids) == 'str':
            taskids = taskids.split(',')
        if type(taskids) == list and len(taskids) <= 20:
            taskids = ','.join(taskids)
        else:
            raise UpYunClientException('length of taskids should less than 20')

        data['bucket_name'] = self.bucket
        data['task_ids'] = taskids
        content = self.__requests_status(data)
        if type(content) == dict and 'tasks' in content:
            return content['tasks']
        raise UpYunServiceException(None, 500,
                                    'Servers except respond tasks list',
                                    'Service Error')

    # --- Signature not correct right now
    def verify_tasks(self, data):
        assert isinstance(data, dict)
        data = self.__set_params_by_post(data)
        if 'signature' in data:
            signature = data['signature']
            del data['signature']
            return signature == make_av_signature(data,
                                                  self.operator, self.password)
        return False

    # --- private API
    def __requests_pretreatment(self, data):
        method = 'POST'
        tasks = data['tasks']
        assert isinstance(tasks, list)
        data['tasks'] = decode_msg(base64.b64encode(b(json.dumps(tasks))))

        uri = self.PRETREAT
        signature = make_av_signature(data, self.operator, self.password)
        auth = 'UPYUN %s:%s' % (self.operator, signature)
        headers = {'Authorization': auth,
                   'Content-Type': 'application/x-www-form-urlencoded'}
        value = urlencode(data)
        resp = self.hp.do_http_pipe(method, self.HOST, uri,
                                    headers=headers, value=value)
        return self.__handle_resp(resp)

    def __requests_status(self, data):
        method = 'GET'
        signature = make_av_signature(data, self.operator, self.password)
        data = urlencode(data)
        uri = '%s?%s' % (self.STATUS, data)
        auth = 'UPYUN %s:%s' % (self.operator, signature)
        headers = {'Authorization': auth}
        resp = self.hp.do_http_pipe(method, self.HOST, uri, headers=headers)
        return self.__handle_resp(resp)

    def __handle_resp(self, resp):
        content = None
        try:
            content = resp.json()
        except Exception as e:
            raise UpYunClientException(e)
        return content

    def __set_params_by_post(self, value):
        data = {}
        for k, v in value.items():
            if k in self.KEYS:
                data[k] = ''.join(v) if isinstance(v, list) else v
        return data

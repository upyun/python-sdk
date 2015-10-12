# -*- coding: utf-8 -*-

import json
import base64
import urllib
import ast

from modules.httpipe import UpYunHttp
from modules.compat import urlencode
from modules.exception import UpYunClientException
from modules.sign import make_content_md5

class AvPretreatment(object):
    def __init__(self, operator, password, bucket, chunksize, human, timeout):
        self.host = "p0.api.upyun.com"
        self.api = {"pretreatment": "/pretreatment/", "status": "/status/"}
        self.operator = operator
        self.password = password
        self.bucket = bucket
        self.chunksize = chunksize
        self.human = human
        self.timeout = timeout
        self.tasks = []
        self.taskids = None
        self.signature = None
        self.hp = UpYunHttp(self.human, self.timeout, self.chunksize)

    # --- public API

    def pretreat(self, tasks, source, notify_url):
        data = {'bucket_name': self.bucket, 'source': source,
                'notify_url': notify_url, 'tasks': tasks}
        content = self.__requests_pretreatment(data)
        try:
            content = ast.literal_eval(content)
        except Exception as e:
            raise UpYunClientException(str(e))
        return content

    def status(self, taskids):
        data = {}
        if type(taskids) == str:
            taskids = taskids.split(',')
        if type(taskids) == list and len(taskids) <= 20:
            taskids = ','.join(taskids)
        else:
            raise UpYunClientException("length of taskids should less than 20")

        data['bucket_name'] = self.bucket
        data['task_ids'] = taskids
        content = self.__requests_status(data)
        if type(content)  == dict and 'tasks' in content:
            return content['tasks']
        return None

    def add_task(self, task):
        self.tasks = self.tasks.append(task)

    def add_tasks(self, tasks):
        if type(tasks) != list:
            raise UpYunClientException("You should give a list of params")
        self.tasks += tasks

    def reset_tasks(self):
        self.tasks = []
        self.taskids = []

    # --- private API

    def __requests_pretreatment(self, data):
        data['tasks'] = self.__process_tasksdata(data['tasks'])
        uri = self.api['pretreatment']
        self.signature = self.__create_signature(data)
        headers = {'Authorization': 'UPYUN ' + self.operator + ":" + self.signature,
                    'Content-Type': 'application/x-www-form-urlencoded'}
        value = urlencode(data)
        return self.hp.do_http_pipe('POST', self.host, uri, headers=headers, value=value)

    def __requests_status(self, data):
        self.signature = self.__create_signature(data)
        data = urllib.urlencode(data)
        uri = self.api['status'] + '?' + data
        headers = {'Authorization': 'UPYUN ' + self.operator + ":" + self.signature}
        return self.hp.do_http_pipe('GET', self.host, uri, headers=headers)

    def __create_signature(self, metadata):
        if type(metadata) == dict:
            signature = ''
            list_meta = sorted(metadata.iteritems(), key=lambda d:d[0])
            for k, v in list_meta:
                if type(v) == list:
                    v = "".join(v)
                signature = signature + k + str(v)
            signature = self.operator + signature + self.password
            return make_content_md5(signature)
        else:
            return None

    def __process_tasksdata(self, tasks):
        if (type(tasks) == list):
            return base64.b64encode(json.dumps(tasks))
        return None

# --- Signature not correct right now
class CallbackValidation(object):
    def __init__(self, dict_callback, av):
        self.params = dict_callback
        self.av = av
        self.keys = ['bucket_name',
                    'status_code',
                    'path',
                    'description',
                    'task_id',
                    'info',
                    'signature',]

    def set_params_by_post(self, dict_callback):
        data = {}
        for key in self.keys:
            if dict_callback.has_key(key):
                value = dict_callback[key]
                if type(value) == list:
                    value = " ".join(value)
                data[key] = value
        return data

    def verify_sign(self):
        self.params = self.set_params_by_post(self.params)
        data = self.params
        if data.has_key('signature'):
            value = data['signature']
            del data['signature']
            if value == self.av.create_signature(data):
                print "signature verify success"
                return True
        print "signature verify failed"
        return False

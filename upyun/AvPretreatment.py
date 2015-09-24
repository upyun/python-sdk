#!/usr/bin/env python
# -*- coding: utf-8 -*-

#容错需要补上, 以及回调函数验证
#明天问一下 info 参数是否需要加入 signature 计算

import requests
import hashlib
import json
import base64
import sys
import urllib

from error import *

class AvPretreatment(object):
    def __init__(self, operator, password, bucket=None, notify_url=None, source=None, tasks=None):
        super(AvPretreatment, self).__init__()
        self.bucket = bucket
        self.notify_url = notify_url
        self.source = source
        self.process = Pocess(operator, password)
        self.tasks = tasks
        self.taskids = []

    def add_task(self, task):
        self.tasks = self.tasks.append(task)

    def add_tasks(self, tasks):
        self.tasks += tasks

    def reset_tasks(self):
        self.tasks = []
        self.taskids = []

    def run(self):
        data = {'bucket_name': self.bucket, 'source': self.source,
                'notify_url': self.notify_url, 'tasks': self.tasks}
        result = self.process.requests_pretreatment(data)

        if type(result) == list:
            self.taskids = result
        return result

    def get_tasks_status(self):
        #change taskid list to string
        data = {}
        if type(self.taskids) == str:
            self.taskids = self.taskids.split(',')
        if type(self.taskids) == list and len(self.taskids) <= 20:
            taskids = ','.join(self.taskids)
        else:
            return "length of taskids should less than 20"

        data['bucket_name'] = self.bucket
        data['task_ids'] = taskids
        result = self.process.requests_status(data)
        if type(result)  == dict and result.has_key('tasks'):
            return result['tasks']
        return result

# the class that actually do things
class Pocess(object):
    def __init__(self, operator, password):
        super(Pocess, self).__init__()
        self.api_url = {"pretreatment": "http://p0.api.upyun.com/pretreatment/", 
            "status": "http://p0.api.upyun.com/status/",}
        self.operator = operator
        self.password = password
        self.taskid = None
        self.signature = None

    def requests_pretreatment(self, data):
        data['tasks'] = self.process_tasksdata(data['tasks'])
        url = self.api_url["pretreatment"]
        self.signature = self.create_signature(data)
        return self.do_requests(data, url, 'POST')

    def requests_status(self, data):
        self.signature = self.create_signature(data)
        data = urllib.urlencode(data)
        url = self.api_url['status'] + '?' + data
        return self.do_requests(data, url, 'GET')

    def do_requests(self, data, url, method, retry_times = 3):
        headers = {'Authorization': 'UPYUN ' + self.operator + ":" + self.signature}
        try:
            for i in range(retry_times):
                if method == 'GET':
                    r = requests.request(method, url, headers=headers)
                elif method == 'POST':
                    r = requests.request(method, url, headers=headers, data=data)
        except Exception, e:
            return e.message
        return self.parse_result(r)

    def parse_result(self, r):
        if r.status_code >= 200 and r.status_code <= 299:
            try:
                return r.json()
            except Exception, e:
                return e.message
        else:
            return 'request failed!HTTP_CODE: ' + str(r.status_code) + ', ' + str(r.text)

    def create_signature(self, metadata):
        if type(metadata) == dict:
            signature = ''
            list_meta = sorted(metadata.iteritems(), key=lambda d:d[0])
            for x in list_meta:
                signature = signature + x[0] + str(x[1])
            signature = self.operator + signature + self.md5(self.password)
            return self.md5(signature)
        else:
            return False

    def process_tasksdata(self, tasks):
        if (type(tasks) == list):
            return base64.b64encode(json.dumps(tasks))
        return False

    def md5(self, value, chunksize=8192):
        try:
            md5 = hashlib.md5()
            md5.update(value)
            return md5.hexdigest()
        except:
            return None


class CallbackValidation(object):
    def __init__(self, dict_callback, av):
        #self.params = self.change_str_to_dict(string)
        #print self.params
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
                    value = "".join(value)
                data[key] = value
        return data

    def verify_sign(self):
        self.params = self.set_params_by_post(self.params)
        data = self.params
        if data.has_key('signature'):
            value = data['signature']
            del data['signature']
            return value == self.av.process.create_signature(data)

        return False

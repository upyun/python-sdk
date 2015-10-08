# -*- coding: utf-8 -*-

import hashlib
import json
import base64
import sys
import urllib
import httplib

try:
    import requests
except ImportError:
    pass

from error import *
from exception import UpYunServiceException, UpYunClientException

class AvPretreatment(object):
    def __init__(self, operator, password, bucket, human_mode, timeout,
                    taskids=None):
        self.host = "p0.api.upyun.com"
        self.func_url = {"pretreatment": "/pretreatment/", "status": "/status/"}
        self.operator = operator
        self.password = password
        self.bucket = bucket
        self.tasks = []
        self.taskids = taskids
        self.status_code = None
        self.x_request_id = None
        self.signature = None
        self.human_mode = human_mode
        self.timeout = timeout

    # --- public API

    def get_status_code(self):
        return self.status_code

    def get_x_request_id(self):
        return self.x_request_id

    def add_task(self, task):
        self.tasks = self.tasks.append(task)

    def add_tasks(self, tasks):
        if type(tasks) != list:
            print "You should give a list of params"
        self.tasks += tasks

    def reset_tasks(self):
        self.tasks = []
        self.taskids = []

    def run(self, source, notify_url=None):
        data = {'bucket_name': self.bucket, 'source': source,
                'notify_url': notify_url, 'tasks': self.tasks}
        ret, result = self.__requests_pretreatment(data)

        if ret == 200 and type(result) == list:
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
        ret, result = self.__requests_status(data)
        if ret == 200 and type(result)  == dict and result.has_key('tasks'):
            return result['tasks']
        return result

    # --- private API

    def __requests_pretreatment(self, data):
        data['tasks'] = self.__process_tasksdata(data['tasks'])
        uri = self.func_url['pretreatment']
        self.signature = self.__create_signature(data)
        headers = {'Authorization': 'UPYUN ' + self.operator + ":" + self.signature,
                    'Content-Type': 'application/x-www-form-urlencoded'}
        if self.human_mode:
            return self.__do_http_human('POST', uri, headers=headers, value=data)
        else:
            return self.__do_http_basic('POST', uri, headers=headers, value=data)

    def __requests_status(self, data):
        self.signature = self.__create_signature(data)
        data = urllib.urlencode(data)
        uri = self.func_url['status'] + '?' + data
        headers = {'Authorization': 'UPYUN ' + self.operator + ":" + self.signature}
        if self.human_mode:
            return self.__do_http_human('GET', uri, headers=headers)
        else:
            return self.__do_http_basic('GET', uri, headers=headers)

    def __do_http_basic(self, method, uri,
                        value=None, headers=None, params=None):
        content, err, status = None, None, None
        try:
            conn = httplib.HTTPConnection(self.host, timeout=self.timeout)
            if 'Content-Type' in headers.keys() and \
                        headers['Content-Type'] == 'application/x-www-form-urlencoded':
                value = urllib.urlencode(value)
            # conn.set_debuglevel(1)
            conn.request(method, uri, value, headers)
            resp = conn.getresponse()
            self.x_request_id = resp.getheader("X-Request-Id", "Unknown")

            status = resp.status
            if status / 100 == 2:
                content = self.__decode_msg(resp.read())
                content = json.loads(content)
            else:
                err = self.__decode_msg(resp.read())
                return (POST_DATA_FAILED, err)
        except Exception, e:
            return (POST_DATA_FAILED, e.message)
        else:
            return (HTTP_OK, content)

    # http://docs.python-requests.org/

    def __do_http_human(self, method, uri,
                        value=None, headers=None, params=None):
        content, err, status = None, None, None
        requests.adapters.DEFAULT_RETRIES = 5

        url = "http://%s%s" % (self.host , uri)
        try:
            resp = requests.request(method, url, headers=headers,
                                data=value, timeout=self.timeout)
            resp.encoding = 'utf-8'
            status = resp.status_code
            if status / 100 == 2:
                content = resp.json()
                self.x_request_id = 'X-Request-Id' in resp.headers \
                    and resp.headers['X-Request-Id'] or "Unknown"
            else:
                err = resp.text
                return (POST_DATA_FAILED, err)
        except Exception, e:
            return (POST_DATA_FAILED, e.message)
        else:
            return (HTTP_OK, content)


    def __create_signature(self, metadata):
        if type(metadata) == dict:
            signature = ''
            list_meta = sorted(metadata.iteritems(), key=lambda d:d[0])
            for k, v in list_meta:
                if type(v) == list:
                    v = "".join(v)
                signature = signature + k + str(v)
            signature = self.operator + signature + self.password
            return self.__md5(signature)
        else:
            return False

    def __process_tasksdata(self, tasks):
        if (type(tasks) == list):
            return base64.b64encode(json.dumps(tasks))
        return False

    def __md5(self, value, chunksize=8192):
        try:
            md5 = hashlib.md5()
            md5.update(value)
            return md5.hexdigest()
        except:
            return None

    def __decode_msg(self, msg):
        if isinstance(msg, str):
            msg = msg.decode('utf-8')
        return msg

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
            return value == self.av.create_signature(data)

        return False

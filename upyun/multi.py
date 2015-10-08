# -*- coding: utf-8 -*-

import httplib
import requests
import os
import hashlib
import time
import json
import base64
import sys
import uuid
import urllib

try:
    import requests
except ImportError:
    pass

from error import *

class Multipart(object):
    def __init__(self, key, value, bucket, secret, timeout,
                        human_mode, block_size=(1024 *1024)):
        self.file = value
        #size: 文件大小
        self.size = self.__getsize(value)
        #api: 分块上传接口url地址
        self.host = "m0.api.upyun.com"
        #expiration: 文件存储时间
        self.expiration = 0
        #blocks: 文件分块的总个数
        self.blocks = 0
        #save_token: 初始化上传后返回的save_token值，替换表单api
        self.save_token = None
        #token_secret: 初始化上传后返回的token_secret值
        self.token_secret = None
        #status: 每一分块数据上传的成功与否情况
        self.status = []
        #bucket: 表单名称
        self.bucket = bucket
        #secret: 表单api值
        self.secret = secret
        #remote_path: 远端上传地址,必须包换文件夹名及文件名，如/upload/a.jpg
        self.remote_path = key
        #block_size: 分块大小
        if block_size > 50 *1024 * 1024:
            block_size = 50 *1024 * 1024
        self.block_size = block_size
        self.x_request_id = None
        self.status_code = None
        self.human_mode = human_mode
        self.timeout = timeout

    # --- public API
    def get_x_request_id(self):
        return self.x_request_id

    def get_status_code(self):
        return self.status_code

    ##
    #分块上传文件的封装函数
    #@return mix result: 表明上传成功，具体返回数据参考http://docs.upyun.com/api/multipart_upload/#signature
    #@return 1: 表明上传失败
    ##
    def multipart_upload(self):
        ret, result = self.__check_size()
        if ret > 0:
            return(ret, result)
        self.blocks = int(self.size / self.block_size) + 1

        ret, result = self.__init_upload()
        if ret != 200:
            result = "Init upload failed: " + str(result)
            return (ret, result)

        ret, result = self.__update_status(result['status'])
        if ret != 0:
            return (ret,result)

        times = 0
        while (not self.__upload_success()) and (times < 3):
            for block_index in range(self.blocks):
                if not self.status[block_index]:
                    ret, result  = self.__block_upload(block_index, self.file)
                    if ret != 200:
                        continue
                    if self.__update_status(result['status']) < 0:
                        return UPDATE_STATUS_FAILED
            times += 1
        if self.__upload_success:
            ret, result = self.__end_upload()
            if ret != 200:
                return (ret, result)
            else:
                return (OK, result)
        else:
            return CHUNK_UPLOAD_FAILED


    # --- private API

    ##
    #检查文件大小，若文件过大则直接返回
    ##
    def __check_size(self):
        if int(self.size) > 1024*1024*1024:
            return FILESIZE_TOO_LARGE
        return (OK, None)

    ##
    #初始化上传
    #@return mixed result: 第一步接口返回数据
    ##
    def __init_upload(self):
        self.expiration = (int)(time.time()) + 2600000

        self.metadata = {'expiration': self.expiration, 'file_blocks': self.blocks, 
                'file_hash': self.__md5(self.file), 'file_size': self.size, 
                'path': self.remote_path}
        self.policy = self.__create_policy(self.metadata)
        self.signature = self.__create_signature(self.metadata, True)
        postdata = {'policy': self.policy, 'signature': self.signature}
        ret, result = self.__do_http_request(postdata)
        if ret == 200:
            try:
                self.save_token = result['save_token']
                self.token_secret = result['token_secret']
            except:
                return INCORRECT_INIT_UPLOAD_RESULT
            else:
                return (ret, result)
        else:
            return (ret, result)

    ##
    #返回base64编码的metadata值，生成policy
    #@parms dict metadata: 包含expiration, file_hash等值的字典
    #@return mixed policy(encode in base64)
    ##
    def __create_policy(self, metadata):
        if type(metadata) == dict:
            policy = json.dumps(metadata)
            return base64.b64encode(policy)
        else:
            return False

    ##
    #将metadata排序后，生成算法所要求的md5格式值
    #@parms dict metadata: 包含expiration, file_hash等值的字典
    #@return mixed signature(encode in md5)
    ##
    def __create_signature(self, metadata, from_api=True):
        if type(metadata) == dict:
            signature = ''
            list_meta = sorted(metadata.iteritems(), key=lambda d:d[0])
            for k, v in list_meta:
                signature = signature + k + str(v)
            if not from_api:
                signature += self.token_secret
            else:
                signature += self.secret
            return self.__md5(signature)
        else:
            return False


    ##
    #@parms dict postdata: post包中的data参数
    #@return json r_json: 接口返回的json格式的值
    ##
    def __do_http_request(self, postdata):
        uri = "/%s/" % self.bucket
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        if self.human_mode:
            return self.__do_http_human('POST', uri, headers=headers, value=postdata)
        else:
            return self.__do_http_basic('POST', uri, headers=headers, value=postdata)

    # http://docs.python.org/2/library/httplib.html

    def __do_http_basic(self, method, uri,
                        value=None, headers=None, params=None):
        content, err, status = None, None, None
        try:
            conn = httplib.HTTPConnection(self.host, timeout=self.timeout)
            # conn.set_debuglevel(1)
            if headers['Content-Type'] == 'application/x-www-form-urlencoded':
                value = urllib.urlencode(value)

            conn.request(method, uri, value, headers)
            resp = conn.getresponse()
            self.x_request_id = resp.getheader("X-Request-Id", "Unknown")

            status = resp.status
            if status / 100 == 2:
                if method == 'POST':
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
                if method == 'POST':
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


    ##
    #@parms list status: 各分块上传情况1
    #将status更新到实例中
    ##
    def __update_status(self, status):
        if type(status) == list:
            self.status = status
            return (OK, None)
        else:
            return UPDATE_STATUS_FAILED

    ##
    #@parms int index: 分块在文件中的序号, 0为第一块
    #@parms file f
    #@return json result: 第二步接口返回参数
    ##
    def __block_upload(self, index, f):
        start_position = int(index * self.block_size)
        if index >= self.blocks - 1:
            end_position = int(self.size)
        else:
            end_position = int(start_position + self.block_size)
        file_block = self.__read_block(f, start_position, end_position)
        block_hash = self.__md5(file_block)

        self.metadata = {'expiration': self.expiration, 'block_index': index, 
                    'block_hash': block_hash, 'save_token': self.save_token}
        policy = self.__create_policy(self.metadata)
        signature = self.__create_signature(self.metadata, False)
        postdata = {'policy': policy, 'signature': signature, 'file': {'data': file_block}}
        ret, result = self.__multipart_post(postdata)
        return (ret, result)

    ##
    #构造multipart/form-data格式的post包，并发送
    #@parms dict postdate
    #@return json r_json: json格式接口返回值
    ##
    def __multipart_post(self, postdata):
        delimiter = '-------------' + str(uuid.uuid1())
        data = ''
        uri = "/%s/" % self.bucket

        for name, content in postdata.iteritems():
            if type(content) == dict:
                data += "--" + delimiter + "\r\n"
                filename = name
                data += 'Content-Disposition: form-data; name="' \
                    + name + '"; filename="' + filename + "\" \r\n"
                b_type = 'application/octet-stream'
                data += 'Content-Type: ' + b_type + "\r\n\r\n"
                data += content['data'] + "\r\n"
            else:
                data += "--" + delimiter + "\r\n"
                data += 'Content-Disposition: form-data; name="' + name + '"'
                data += "\r\n\r\n" + content + "\r\n"

        data += "--" + delimiter + "--"
        headers = {'Content-Type': 'multipart/form-data; boundary=' \
            + delimiter, 'Content-Length': len(data)}

        if self.human_mode:
            return self.__do_http_human('POST', uri, headers=headers, value=data)
        else:
            return self.__do_http_basic('POST', uri, headers=headers, value=data)

    ##
    #检测所有分块是否上传成功
    #@return int True成功 False失败
    ##
    def __upload_success(self):
        sum_status = 0
        for i in self.status:
            sum_status += i
        return len(self.status) == sum_status

    ##
    #将所有分块合并
    #@return json result: 第三步接口返回值
    ##
    def __end_upload(self):
        self.metadata = {'expiration': self.expiration, 'save_token': self.save_token}
        policy = self.__create_policy(self.metadata)
        signature = self.__create_signature(self.metadata, False)
        postdata = {'policy': policy, 'signature': signature}
        ret, result = self.__do_http_request(postdata)
        return (ret, result)

    ##
    #@parms handler fileobj
    #@return string 文件大小
    ##
    def __getsize(self, fileobj):
        try:
            if hasattr(fileobj, 'fileno'):
               return os.fstat(fileobj.fileno()).st_size
        except IOError:
            pass

        return len(fileobj.getvalue())


    ##
    #@parms int current_position: 文件起始位置
    #@parms int end_positon: 文件结束位置
    #@parms int length: 每次读取的长度
    #@return string data: 读取的二进制数据
    ##
    def __read_block(self, f, current_position, end_position, length = 3*8192):
        data = ''
        while current_position < end_position:
            if (current_position + length) > end_position:
                length = end_position - current_position
            f.seek(current_position, 0)
            data += f.read(length)
            current_position += length
        return data


    def __decode_msg(self, msg):
        if isinstance(msg, bytes):
            msg = msg.decode('utf-8')
        return msg

    def __encode_msg(self, msg):
        if isinstance(msg, str):
            msg = msg.encode('utf-8')
        return msg

    ##
    #@parms string/file
    #@return 返回字符串md5值
    ##
    def __md5(self, value, chunksize=8192):
        if hasattr(value, "fileno"):
            md5 = hashlib.md5()
            for chunk in iter(lambda: value.read(chunksize), b''):
                md5.update(chunk)
            value.seek(0)
            return md5.hexdigest()
        else:
            try:
                md5 = hashlib.md5()
                md5.update(value)
                return md5.hexdigest()
            except:
                return False


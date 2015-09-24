#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import os
import hashlib
import time
import json
import base64
import requests
import sys
import uuid
import urllib

from error import *

class Multipart(object):
    def __init__(self, key, value, bucket, bucket_api, block_size=(1024 *1024)):
        super(Multipart, self).__init__()
        self.file = value
        #size: 文件大小
        self.size = self.getsize(value)
        #api: 分块上传接口url地址
        self.api = "http://m0.api.upyun.com/"
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
        #bucket: 表单api值
        self.bucket_api = bucket_api
        #remote_path: 远端上传地址,必须包换文件夹名及文件名，如/upload/a.jpg
        self.remote_path = key
        #block_size: 分块大小
        if block_size > 50 *1024 * 1024:
            block_size = 50 *1024 * 1024
        self.block_size = block_size

    ##
    #分块上传文件的封装函数
    #@return mix result: 表明上传成功，具体返回数据参考http://docs.upyun.com/api/multipart_upload/#signature
    #@return 1: 表明上传失败
    ##
    def multipart_upload(self):
        ret, result = self.check_size()
        if ret > 0:
            return(ret, result)
        self.blocks = int(self.size / self.block_size) + 1

        ret, result = self.init_upload()
        if ret != 200:
            result = "Init upload failed: " + str(result)
            return (ret, result)

        ret, result = self.update_status(result['status'])
        if ret != 0:
            return (ret,result)

        times = 0
        while (not self.upload_success()) and (times < 3):
            for block_index in range(self.blocks):
                if not self.status[block_index]:
                    ret, result  = self.block_upload(block_index, self.file)
                    if ret != 200:
                        continue
                    if self.update_status(result['status']) < 0:
                        return UPDATE_STATUS_FAILED
            times += 1
        if self.upload_success:
            ret, result = self.end_upload()
            if ret != 200:
                return (ret, result)
            else:
                return (OK, result)
        else:        
            return CHUNK_UPLOAD_FAILED

    ##
    #检查文件大小，若文件过大则直接返回
    ##
    def check_size(self):
        if int(self.size) > 1024*1024*1024:
            return FILESIZE_TOO_LARGE
        return (OK, None)
            
    ##
    #初始化上传
    #@return mixed result: 第一步接口返回数据
    ##
    def init_upload(self):
        self.expiration = (int)(time.time()) + 2600000

        self.metadata = {'expiration': self.expiration, 'file_blocks': self.blocks, 
                'file_hash': self.md5(self.file), 'file_size': self.size, 
                'path': self.remote_path}
        self.policy = self.create_policy(self.metadata)
        self.signature = self.create_signature(self.metadata, True)
        postdata = {'policy': self.policy, 'signature': self.signature}
        ret, result = self.post_data(postdata)
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
    def create_policy(self, metadata):
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
    def create_signature(self, metadata, from_api=True):
        if type(metadata) == dict:
            signature = ''
            list_meta = sorted(metadata.iteritems(), key=lambda d:d[0])
            for x in list_meta:
                signature = signature + x[0] + str(x[1])
            if not from_api:
                signature += self.token_secret
            else:
                signature += self.bucket_api
            return self.md5(signature)
        else:
            return False

    ##
    #@parms dict postdata: post包中的data参数
    #@return json r_json: 接口返回的json格式的值
    ##
    def post_data(self, postdata):
        url = self.api + self.bucket + '/'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        try:
            r = requests.post(url, data=postdata, headers=headers)
            r_json = r.json()
            if r_json.has_key('error_code'):
                raise AssertionError(r.text)
        except AssertionError as e:
            return (POST_DATA_FAILED, e.message)
        except Exception, e:
            return (POST_DATA_FAILED, e)
        else:
            return (HTTP_OK, r_json)

    ##
    #@parms list status: 各分块上传情况1
    #将status更新到实例中
    ##
    def update_status(self, status):
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
    def block_upload(self, index, f):
        start_position = int(index * self.block_size)
        if index >= self.blocks - 1:
            end_position = int(self.size)
        else:
            end_position = int(start_position + self.block_size)
        file_block = self.read_block(f, start_position, end_position)
        block_hash = self.md5(file_block)

        self.metadata = {'expiration': self.expiration, 'block_index': index, 
                    'block_hash': block_hash, 'save_token': self.save_token}
        policy = self.create_policy(self.metadata)
        signature = self.create_signature(self.metadata, False)
        postdata = {'policy': policy, 'signature': signature, 'file': {'data': file_block}}
        ret, result = self.multipart_post(postdata)
        return (ret, result)

    ##
    #构造multipart/form-data格式的post包，并发送
    #@parms dict postdate
    #@return json r_json: json格式接口返回值
    ##
    def multipart_post(self, postdata):
        delimiter = '-------------' + str(uuid.uuid1())
        data = ''
        url = self.api + self.bucket + '/'

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
        r_json = {}
        headers = {'Content-Type': 'multipart/form-data; boundary=' \
            + delimiter, 'Content-Length': len(data)}
        try:
            r = requests.post(url, data=data, headers=headers)
            r_json = r.json()
            if r_json.has_key('error_code'):
                raise AssertionError(r.text)
        except AssertionError as e:
            return (MULTIPART_POST_FAILED, e)
        else:
            return (HTTP_OK, r_json)

    ##
    #检测所有分块是否上传成功
    #@return int True成功 False失败
    ##
    def upload_success(self):
        sum_status = 0
        for i in self.status:
            sum_status += i
        return len(self.status) == sum_status

    ##
    #将所有分块合并
    #@return json result: 第三步接口返回值
    ##
    def end_upload(self):
        self.metadata = {'expiration': self.expiration, 'save_token': self.save_token}
        policy = self.create_policy(self.metadata)
        signature = self.create_signature(self.metadata, False)
        postdata = {'policy': policy, 'signature': signature}
        ret, result = self.post_data(postdata)
        return (ret, result)

    ##
    #@parms string/file
    #@return 返回字符串md5值
    ##
    def md5(self, value, chunksize=8192):
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

    ##
    #@parms handler fileobj
    #@return string 文件大小
    ##
    def getsize(self, fileobj):
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
    def read_block(self, f, current_position, end_position, length = 3*8192):
        data = ''
        while current_position < end_position:
            if (current_position + length) > end_position:
                length = end_position - current_position
            f.seek(current_position, 0)
            data += f.read(length)
            current_position += length
        return data

# -*- coding: utf-8 -*-

import os
import time

from modules.compat import urlencode
from modules.exception import UpYunServiceException, UpYunClientException
from modules.sign import make_policy, make_signature, make_content_md5

class Multipart(object):
    def __init__(self, bucket, secret, hp):
        #size: 文件大小
        self.size = 0
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
        #secret: 表单秘钥值
        self.secret = secret
        #hp: 带有 session 值的 http 接口
        self.hp = hp
        #filename: 原始文件名
        self.filename = None
        #block_size: 分块大小
        self.block_size = None
        self.kind = 'multi'

    # --- public API

    ##
    #分块上传文件的封装函数
    #@return mix result: 表明上传成功，具体返回数据参考http://docs.upyun.com/api/multipart_upload/#signature
    #@return 1: 表明上传失败
    ##
    def upload(self, key, value, expiration, block_size):
        self.remote_path = key
        self.file = value
        self.size = self.__get_size(value)
        self.filename = os.path.basename(value.name).encode('utf-8')
        self.expiration = (int)(time.time()) + expiration

        self.__check_size(block_size)
        self.blocks = int(self.size / self.block_size) + 1

        #init upload
        content = self.__init_upload()
        self.__update_status(content)

        #block item upload
        for block_index in range(self.blocks):
            if not self.status[block_index]:
                content  = self.__block_upload(block_index, value)
                self.__update_status(content)

        if self.__upload_success:
            return self.__end_upload()


    # --- private API

    ##
    #检查文件大小，若文件过大则直接返回
    ##
    def __check_size(self, block_size):
        if int(self.size) > 1024 * 1024 * 1024:
            raise UpYunClientException("File size is too large(larger than 1G)")

        if block_size > 50 * 1024 * 1024:
            block_size = 50 * 1024 * 1024
        if block_size < 5 * 1024 * 1024:
            block_size = 5 * 1024 * 1024
        self.block_size = block_size

    ##
    #初始化上传
    #@return mixed result: 第一步接口返回数据
    ##
    def __init_upload(self):
        data = {'expiration':self.expiration, 'file_blocks': self.blocks,
                'file_hash':  make_content_md5(self.file), 'file_size': self.size,
                'path': self.remote_path}
        self.policy = make_policy(data)
        self.signature = make_signature(data, self.secret)
        postdata = {'policy': self.policy, 'signature': self.signature}
        content = self.__do_http_request(postdata)
        if 'save_token' in content.keys() and 'token_secret' in content.keys():
            self.save_token = content['save_token']
            self.token_secret = content['token_secret']
        else:
            raise UpYunServiceException(None, 503, 'Service unavailable',
                                            'Not enough response from api')
        return content

    ##
    #@parms dict value: post包中的data参数
    #@return json r_json: 接口返回的json格式的值
    ##
    def __do_http_request(self, value):
        uri = "/%s/" % self.bucket
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        value = urlencode(value)
        return self.hp.do_http_pipe('POST', self.host, uri, headers=headers,
                                            value=value, kind=self.kind)

    ##
    #@parms list status: 各分块上传情况
    #将status更新到实例中
    ##
    def __update_status(self, content):
        if 'status' in content and type(content['status']) == list:
            self.status = content['status']
        else:
            raise UpYunServiceException(None, 503, 'Service unavailable',
                                            'Update status failed')

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
        block_hash = make_content_md5(file_block)

        data = {'expiration': self.expiration, 'block_index': index,
                    'block_hash': block_hash, 'save_token': self.save_token}
        policy = make_policy(data)
        signature = make_signature(data, self.token_secret)
        postdata = {'policy': policy, 'signature': signature, 'file': {'data': file_block}}
        return self.__multipart_post(postdata)

    ##
    #构造multipart/form-data格式的post包，并发送
    #@parms dict postdate
    #@return json r_json: json格式接口返回值
    ##
    def __multipart_post(self, value):
        uri = "/%s/" % self.bucket

        return self.hp.do_http_multipart(self.host, uri, value, self.filename)

    ##
    #检测所有分块是否上传成功
    #@return int True成功 False失败
    ##
    def __upload_success(self):
        return len(self.status) == sum(self.status)

    ##
    #将所有分块合并
    #@return json result: 第三步接口返回值
    ##
    def __end_upload(self):
        data = {'expiration': self.expiration, 'save_token': self.save_token}
        policy = make_policy(data)
        signature = make_signature(data, self.token_secret)
        postdata = {'policy': policy, 'signature': signature}
        content = self.__do_http_request(postdata)
        return content

    ##
    #@parms handler fileobj
    #@return string 文件大小
    ##
    def __get_size(self, fileobj):
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

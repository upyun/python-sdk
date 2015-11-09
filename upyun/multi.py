# -*- coding: utf-8 -*-

import os
import time
import json
import itertools
from multiprocessing.dummy import Pool as ThreadPool

from .modules.compat import urlencode, str, b
from .modules.exception import UpYunServiceException, UpYunClientException
from .modules.sign import make_policy, make_signature, \
                            make_content_md5, decode_msg, encode_msg

class Multipart(object):
    ED_LIST = ("m%d.api.upyun.com" % ed for ed in range(4))
    ED_AUTO, ED_TELECOM, ED_CNC, ED_CTT = ED_LIST

    def __init__(self, bucket, secret, hp, endpoint):
        self.bucket = bucket
        self.secret = secret
        self.hp = hp
        self.endpoint = endpoint or self.ED_AUTO

    # --- public API

    ##
    #分块上传文件的封装函数
    #@return mix result: 表明上传成功，具体返回数据参考http://docs.upyun.com/api/multipart_upload/#signature
    #@return 1: 表明上传失败
    ##
    def upload(self, key, value, block_size, expiration):
        expiration = expiration or 1800
        expiration = int(expiration + time.time())
        status = []
        file_size, file_name, blocks, save_token, token_secret, content \
                                        = None, None, None, None, None, None
        file_size = int(self.__get_size(value))
        file_name = encode_msg(os.path.basename(value.name))

        block_size = self.__check_size(file_size, block_size)
        blocks = int(file_size / block_size) + 1

        #init upload
        content, save_token, token_secret = self.__init_upload(
                                    key, value, file_size, blocks, expiration)
        status = self.__update_status(content)

        #block item upload
        retry = 0
        pool = ThreadPool(4)
        while not self.__upload_success(status) and retry < 5:
            status_list = pool.map(self.__block_upload_hub, zip(range(blocks),
                                itertools.repeat((status, value, file_size, block_size,
                                expiration, save_token, token_secret, file_name))))
            status = self.__find_max_status(status_list)
            retry += 1

        pool.close()
        pool.join()
        if self.__upload_success(status):
            return self.__end_upload(expiration, save_token, token_secret)
        else:
            UpYunServiceException(None, 500, 'Upload failed',
                                    'Failed to upload the whole file within retry times')

    # --- private API

    ##
    #初始化上传
    #@return mixed result: 第一步接口返回数据
    ##
    def __init_upload(self, key, value, file_size, blocks, expiration):
        data = {'expiration': expiration, 'file_blocks': blocks,
                'file_hash':  make_content_md5(value), 'file_size': file_size,
                'path': key}
        policy = make_policy(data)
        signature = make_signature(data, self.secret)
        postdata = {'policy': policy, 'signature': signature}
        content = self.__do_http_request(postdata)
        if 'save_token' in content and 'token_secret' in content:
            save_token = content['save_token']
            token_secret = content['token_secret']
        else:
            raise UpYunServiceException(None, 503, 'Service unavailable',
                                            'Not enough response datas from api')
        return content, save_token, token_secret


    def __block_upload_hub(self, index):
        #Convert `f([1,2])` to `f(1,2)` call
        return self.__block_upload(*index)


    ##
    #@parms int index: 分块在文件中的序号, 0为第一块
    #@parms file f
    #@return json result: 第二步接口返回参数
    ##
    def __block_upload(self, index, parms):
        status, value, file_size, block_size, expiration, save_token, \
                                                token_secret, file_name = parms
        if status[index]:
            return status
        content = None
        start_position = index * block_size
        if index >= len(status) - 1:
            end_position = file_size
        else:
            end_position = start_position + block_size

        file_block = self.__read_block(value, start_position, end_position)
        block_hash = make_content_md5(file_block)

        data = {'expiration': expiration, 'block_index': index,
                    'block_hash': block_hash, 'save_token': save_token}
        policy = make_policy(data)
        signature = make_signature(data, token_secret)
        postdata = {'policy': policy, 'signature': signature, 'file': {'data': file_block}}
        content = self.__do_multipart_request(postdata, file_name)
        return self.__update_status(content)


    ##
    #将所有分块合并
    #@return json result: 第三步接口返回值
    ##
    def __end_upload(self, expiration, save_token, token_secret):
        data = {'expiration': expiration, 'save_token': save_token}
        policy = make_policy(data)
        signature = make_signature(data, token_secret)
        postdata = {'policy': policy, 'signature': signature}
        content = self.__do_http_request(postdata)
        return content


    def __find_max_status(self, status_list):
        max_item = 0
        max_status = status_list[0]
        for status in status_list:
            if sum(status) > max_item:
                max_status = status
        return max_status

    ##
    #@parms list status: 各分块上传情况
    #将status更新到实例中
    ##
    def __update_status(self, content):
        if 'status' in content and type(content['status']) == list:
            return content['status']
        else:
            raise UpYunServiceException(None, 503, 'Service unavailable',
                                            'Update status failed')


    ##
    #@parms dict value: post包中的data参数
    #@return json r_json: 接口返回的json格式的值
    ##
    def __do_http_request(self, value):
        resp, human, conn = None, None, None
        uri = "/%s/" % self.bucket
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        value = urlencode(value)
        resp, human, conn = self.hp.do_http_pipe('POST', self.endpoint, uri, headers=headers,
                                            value=value)
        return self.__handle_resp(resp, conn, human)


    def __do_multipart_request(self, value, file_name):
        uri = "/%s/" % self.bucket

        resp, human, conn = self.hp.do_http_multipart(self.endpoint, uri, value, file_name)
        return self.__handle_resp(resp, conn, human)


    def __handle_resp(self, resp, conn, human):
        content = None
        try:
            if human:
                content = resp.json()
            else:
                content = json.loads(decode_msg(resp.read()))
        except Exception as e:
            raise UpYunClientException(str(e))
        finally:
            if conn:
                conn.close()
        return content

    ##
    #检测所有分块是否上传成功
    #@return int True成功 False失败
    ##
    def __upload_success(self, status):
        return len(status) == sum(status)


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
    #检查文件大小，若文件过大则直接返回
    ##
    def __check_size(self, size, block_size):
        if int(size) > 1024 * 1024 * 1024:
            raise UpYunClientException("File size is too large(larger than 1G)")

        block_size = int(block_size)
        if block_size > 50 * 1024 * 1024:
            block_size = 50 * 1024 * 1024
        if block_size < 1024 * 1024:
            block_size = 1024 * 1024
        return block_size

    ##
    #@parms int current_position: 文件起始位置
    #@parms int end_positon: 文件结束位置
    #@parms int length: 每次读取的长度
    #@return string data: 读取的二进制数据
    ##
    def __read_block(self, f, current_position, end_position, length = 3*8192):
        data = []
        while current_position < end_position:
            if (current_position + length) > end_position:
                length = end_position - current_position
            f.seek(current_position, 0)
            data.append(f.read(length))
            current_position += length
        return b('').join(b(data))

# -*- coding: utf-8 -*-
import os
import time
import math
import itertools
import threading
from multiprocessing.dummy import Pool as ThreadPool

from .modules.compat import urlencode, b
from .modules.exception import UpYunServiceException, UpYunClientException
from .modules.sign import make_policy, make_multi_signature, make_content_md5


class Multipart(object):
    def __init__(self, bucket, secret, endpoint, hp):
        self.bucket = bucket
        self.secret = secret
        self.hp = hp
        self.host = 'm0.api.upyun.com'
        self.uri = '/%s/' % bucket

    # --- public API
    def upload(self, key, value, block_size, expiration, **kwargs):
        lock = threading.Lock()
        expiration = expiration or 1800
        expiration = int(expiration + time.time())
        block_size = block_size or 1024*1024
        file_size = int(self.__get_size(value))
        block_size = self.__check_size(block_size)
        blocks = int(math.ceil(file_size * 1.0 / block_size)) or 1

        # - init upload
        content = self.__init_upload(key, value,
                                     file_size, blocks, expiration, **kwargs)
        if 'save_token' in content and 'token_secret' in content:
            save_token = content['save_token']
            token_secret = content['token_secret']
        else:
            raise UpYunServiceException(None, 503, 'Service unavailable',
                                        'Not enough response datas from api')
        status = self.__get_status(content)

        # - block item upload
        retry = 0
        pool = ThreadPool(4)
        while not self.__upload_success(status) and retry < 5:
            status_list = pool.map(lambda parms: self.__block_upload(*parms),
                                   zip(range(blocks), itertools.repeat(
                                       (status, value, file_size,
                                        block_size, expiration,
                                        save_token, token_secret, lock))
                                       ))
            status = self.__find_max_status(status_list)
            retry += 1
        pool.close()
        pool.join()

        # - end upload
        if self.__upload_success(status):
            return self.__end_upload(expiration, save_token, token_secret)
        else:
            UpYunServiceException(None, 500, 'Upload failed',
                                  'Failed to upload the whole '
                                  'file within retry times')

    # --- private API
    def __init_upload(self, key, value, file_size,
                      blocks, expiration, **kwargs):
        data = {'expiration': expiration,
                'file_blocks': blocks,
                'file_hash': make_content_md5(value),
                'file_size': file_size,
                'path': key,
                }

        data.update(kwargs)
        policy = make_policy(data)
        signature = make_multi_signature(data, self.secret)
        postdata = {'policy': policy, 'signature': signature}
        return self.__do_http_request(postdata)

    def __block_upload(self, index, parms):
        status, value, file_size, block_size, expiration,\
            save_token, token_secret, lock = parms
        # - if status[index] is already 1, skip it
        if status[index]:
            return status
        start_position = index * block_size
        if index == len(status) - 1:
            end_position = file_size
        else:
            end_position = start_position + block_size

        file_block = self.__read_block(value, start_position,
                                       end_position, lock)
        block_hash = make_content_md5(file_block)

        data = {'expiration': expiration, 'block_index': index,
                'block_hash': block_hash, 'save_token': save_token,
                }
        policy = make_policy(data)
        signature = make_multi_signature(data, token_secret)
        postdata = {'policy': policy,
                    'signature': signature,
                    'file': file_block,
                    }
        resp = self.hp.do_http_pipe('POST', self.host, self.uri,
                                    files=postdata)
        content = self.__handle_resp(resp)
        return self.__get_status(content)

    def __end_upload(self, expiration, save_token, token_secret):
        data = {'expiration': expiration, 'save_token': save_token}
        policy = make_policy(data)
        signature = make_multi_signature(data, token_secret)
        postdata = {'policy': policy, 'signature': signature}
        return self.__do_http_request(postdata)

    def __find_max_status(self, status_list):
        max_item = 0
        max_status = status_list[0]
        for status in status_list:
            if sum(status) > max_item:
                max_item = sum(status)
                max_status = status
        return max_status

    def __get_status(self, content):
        if 'status' in content and type(content['status']) == list:
            return content['status']
        else:
            raise UpYunServiceException(None, 503, 'Service unavailable',
                                        'Update status failed')

    def __do_http_request(self, value):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        value = urlencode(value)
        resp = self.hp.do_http_pipe('POST', self.host, self.uri,
                                    headers=headers, value=value)
        return self.__handle_resp(resp)

    def __handle_resp(self, resp):
        try:
            content = resp.json()
        except Exception as e:
            raise UpYunClientException(e)
        return content

    def __upload_success(self, status):
        return len(status) == sum(status)

    def __get_size(self, fileobj):
        try:
            if hasattr(fileobj, 'fileno'):
                return os.fstat(fileobj.fileno()).st_size
        except IOError:
            pass
        return len(fileobj.getvalue())

    def __check_size(self, block_size):
        if block_size > 5 * 1024 * 1024:
            block_size = 5 * 1024 * 1024
        if block_size < 100 * 1024:
            block_size = 100 * 1024
        return int(block_size)

    def __read_block(self, f, current_position, end_position, lock,
                     length=3*8192):
        data = []
        lock.acquire()
        while current_position < end_position:
            if (current_position + length) > end_position:
                length = end_position - current_position
            f.seek(current_position, 0)
            data.append(f.read(length))
            current_position += length
        lock.release()
        return b('').join(b(data))

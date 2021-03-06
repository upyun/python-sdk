# -*- coding: utf-8 -*-
from .modules.exception import UpYunClientException
import json


class UpYunMultiUploader(object):
    """断点续传
    :param rest: upyun rest 实例
    :param key: upyun 文件名
    :param part_size: 分块上传大小
    :param part_file: 文件大小
    :param headers: 传给 `initiate_upload` 的 HTTP 头部
    """

    def __init__(self, rest, key, headers=None,
                 part_size=None, file_size=None, upload_id=None):
        if part_size and part_size % (1024*1024) != 0:
            raise UpYunClientException('part size wrong')

        self.key = key
        self.rest = rest
        self.part_size = part_size
        self.file_size = file_size
        self.headers = headers or {}
        if upload_id:
            if not isinstance(upload_id, str) or len(upload_id) != 36:
                raise UpYunClientException('the format of upload_id wrong')
            self.upload_id = upload_id
        else:
            self._init()

    def _init(self):
        headers = self.headers
        if self.part_size:
            headers["X-Upyun-Multi-Part-Size"] = str(self.part_size)
        if self.file_size:
            headers["X-Upyun-Multi-Length"] = str(self.file_size)
        headers["X-Upyun-Multi-Stage"] = "initiate"
        headers["X-Upyun-Multi-Disorder"] = "true"
        h = self.rest.do_http_request(
            key=self.key, method="PUT", headers=headers)
        res_headers = self.rest.get_meta_headers(h)
        self.upload_id = res_headers['multi-uuid']

    def upload(self, part_id, data):
        headers = {
            "X-Upyun-Multi-Stage": "upload",
            "X-Upyun-Multi-Uuid": self.upload_id,
            "X-Upyun-Part-Id": str(part_id),
        }
        self.rest.do_http_request(
            key=self.key, value=data, method="PUT", headers=headers)

    def complete(self, multi_md5=None):
        headers = {
            "X-Upyun-Multi-Stage": "complete",
            "X-Upyun-Multi-Uuid": self.upload_id,
        }
        if multi_md5:
            headers["X-Upyun-Multi-Md5"] = multi_md5

        h = self.rest.do_http_request(
            key=self.key, method="PUT", headers=headers)
        res_headers = self.rest.get_meta_headers(h)
        return res_headers

    def cancel(self):
        headers = {
            "X-Upyun-Multi-Uuid": self.upload_id,
        }
        self.rest.do_http_request(
            key=self.key, method="DELETE", headers=headers)

    def list_uploaded_parts(self):
        headers = {
            "X-Upyun-Multi-Uuid": self.upload_id,
        }

        datas = self.rest.do_http_request(
            key=self.key, method="GET", headers=headers)
        return json.loads(datas)["parts"]

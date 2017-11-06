# -*- coding: utf-8 -*-

import upyun
import hashlib

# 需要填写自己的服务名，操作员名，密码
service = ""
username = ""
password = ""

# 需要填写上传文件的本地路径和云存储路径
local_file = ""
remote_file = ""

up = upyun.UpYun(service, username=username, password=password)


def rest_upload():
    """
    rest文件上传
    """
    with open(local_file, "rb") as f:
        # headers 可选，见rest上传参数
        headers = None
        up.put(remote_file, f, headers=headers)


def rest_resume_upload():
    """
    文件断点续传
    """
    with open(local_file, "rb") as f:
        # headers 可选，见rest上传参数
        headers = None
        res = up.put(remote_file, f, checksum=True,
                     need_resume=True, headers=headers)
        print(res)


def form_upload():
    """
    form文件上传
    """
    # kwargs 可选，见form上传参数
    kwargs = None
    with open(local_file, 'rb') as f:
        res = up.put(remote_file, f, checksum=True, form=True)
        print(res)

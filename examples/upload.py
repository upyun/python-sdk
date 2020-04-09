# -*- coding: utf-8 -*-

import upyun
import hashlib
import os

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

def rest_multi_upload():
    """
    文件并发上传
    """
    uploader = up.init_multi_uploader(remote_file)
    uploader.upload(1, os.urandom(20))
    uploader.upload(0, os.urandom(1024 * 1024))
    res = uploader.complete()
    upload_id = uploader.upload_id
    print(res)


    """
    一次上传没有完成, 可以把uploader.upload_id的值保存下来, 下次继续上传
    """
    uploader = up.init_multi_uploader(remote_file, upload_id=upload_id)
    """
    如果有需要，可以列出来已经上传成功的parts, 返回一个json结构的数组
    [{
        "id": 0,
        "suze": 1048576,
        "etag": "cf97350abc2b45804d09a829b55eeeaf",
    }]
    """
    datas = uploader.list_uploaded_parts() 
    print(datas)
    

    

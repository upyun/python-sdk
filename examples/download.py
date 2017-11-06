# -*- coding: utf-8 -*-

import upyun
import hashlib

# 需要填写自己的服务名，操作员名，密码
service = ""
username = ""
password = ""

# 需要填写上传文件的本地路径和云存储路径，目录
local_file = ""
remote_file = ""
remote_dir = ""

up = upyun.UpYun(service, username=username, password=password)


def rest_download():
    """
    文件下载
    """
    with open(local_file, 'wb') as f:
        up.get(remote_file, f)


def rest_delete():
    """
    文件或目录删除
    """
    up.delete(remote_file)


def rest_mkdir():
    """
    目录创建
    """
    up.mkdir(remote_dir)


def rest_list():
    """
    列目录
    """
    # limit,order,begin 见列目录参数x-list-limit， x-list-order， x-list-iter说明
    up.getlist(remote_dir)


def rest_info():
    """
    获取文件信息
    """
    up.getinfo(remote_file)


def rest_purge():
    """
    缓存刷新
    """
    up.purge(remote_file)

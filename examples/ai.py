# -*- coding: utf-8 -*-

import upyun
import hashlib

# 需要填写自己的服务名，操作员名，密码，通知URL
service = ""
username = ""
password = ""
notify_url = ""

# 需要填写本地路劲，云存储路径
# 待上传文件
local_file = ""
# 云存储图片文件
image_file = ""
# 云存储视频文件
video_file = ""
# 另存为文件
save_as = ""

up = upyun.UpYun(service, username=username, password=password)


def image_form():
    """
    内容识别-图片上传预处理
    """
    kwargs = {"apps": [{"name": "imgaudit", "notify_url": notify_url}]}
    with open(local_file, 'rb') as f:
        res = up.put(image_file, f, checksum=True, form=True, **kwargs)
        print(res)


def image_pretreatment():
    '''
    内容识别-云存储中的图片处理
    '''
    # tasks见文档说明
    tasks = [{"source": image_file}]
    res = up.put_tasks(tasks, notify_url, "imgaudit")
    print(res)


def video_form():
    """
    内容识别-视频点播上传预处理
    """
    kwargs = {"apps": [{"name": "videoaudit", "notify_url": notify_url}]}
    with open(local_file, 'rb') as f:
        res = up.put(video_file, f, checksum=True, form=True, **kwargs)
        print(res)


def video_pretreatment():
    '''
    内容识别-云存储中的视频点播处理
    '''
    # tasks见文档说明
    tasks = [{"source": video_file, "save_as": save_as}]
    res = up.put_tasks(tasks, notify_url, "videoaudit")
    print(res)

# -*- coding: utf-8 -*-

import upyun
import hashlib

# 需要填写自己的服务名，操作员名，密码，通知URL
service = ""
username = ""
password = ""
notify_url = ""

# 按需要填写自己的信息
# 待上传文件
local_file = ""
# 云存储图片文件
image_file = ""
# 云存储视频文件
video_file = ""
# 云存储音频文件
audio_file = ""
# 云存储压缩文件
compress_file = ""
# 云存储解压缩目录
compress_dir = ""
# 云存储文档文件
doc_file = ""
# 另存为文件
save_as = ""
# 文件拉取URL
url = ""
# 图片拼接的二维数组
image_matrix = [[]]

up = upyun.UpYun(service, username=username, password=password)


def image_async_process():
    """
    图片处理-异步上传预处理
    """
    # 处理参数详见文档说明
    kwargs = {"apps": [
        {"name": "thumb", "x-gmkerl-thumb": "/format/png", "save_as": save_as}]}
    with open(local_file, 'rb') as f:
        res = up.put(image_file, f, checksum=True, form=True, **kwargs)
        print(res)


def image_sync_process():
    """
    图片处理-同步上传预处理
    """
    # 处理参数详见文档说明
    kwargs = {"x-gmkerl-thumb": "/format/png"}
    with open(local_file, 'rb') as f:
        res = up.put(image_file, f, checksum=True, form=True, **kwargs)
        print(res)


def image_async_joint():
    """
    异步图片拼接-云存储中的图片拼接
    """
    # tasks见文档说明
    tasks = [{"image_matrix": image_matrix, "save_as": save_as}]
    res = up.put_tasks(tasks, notify_url, "jigsaw")
    print(res)


def video_form_process():
    """
    异步音视频处理-上传预处理
    """
    # 处理参数详见文档说明
    kwargs = {"apps": [
        {"name": "naga", "type": "video", "avopts": "/s/128x96", "notify_url": notify_url}]}
    with open(local_file, 'rb') as f:
        res = up.put(video_file, f, checksum=True, form=True, **kwargs)
        print(res)


def video_async_process():
    """
    异步音视频处理-云存储中的音视频文件
    """
    # tasks见文档说明
    tasks = [{"type": "video", "avopts": "/s/128x96"}]
    res = up.pretreat(tasks, video_file, notify_url)
    print(res)


def audio_sync_process():
    """
    同步音频处理
    """
    # 处理参数详见文档说明
    kwargs = {"x-audio-avopts": "/ab/48/ac/5/f/ogg"}
    with open(local_file, 'rb') as f:
        res = up.put(audio_file, f, checksum=True, form=True, **kwargs)
        print(res)


def compress():
    """
    压缩
    """
    # tasks见文档说明
    tasks = [{"sources": [image_file, video_file], "save_as": compress_file}]
    res = up.compress(tasks, notify_url)
    print(res)


def depress():
    """
    解压缩
    """
    # tasks见文档说明
    tasks = [{"sources": compress_file, "save_as": compress_dir}]
    res = up.depress(tasks, notify_url)
    print(res)


def spiderman():
    """
    文件拉取
    """
    # tasks见文档说明
    tasks = [{"url": url, "random": False,
              "overwrite": True, "save_as": save_as}]
    res = up.put_tasks(tasks, notify_url, "spiderman")
    print(res)


def file_form_convert():
    """
    文档转换-上传预处理
    """
    # 处理参数详见文档说明
    kwargs = {"apps": [
        {"name": "uconvert", "save_as": save_as, "notify_url": notify_url}]}
    with open(local_file, 'rb') as f:
        res = up.put(doc_file, f, checksum=True, form=True, **kwargs)
        print(res)


def file_convert():
    """
    文档转换-云存储中文档的转换
    """
    # tasks见文档说明
    tasks = [{"source": doc_file, "save_as": save_as}]
    res = up.put_tasks(tasks, notify_url, "uconvert")
    print(res)

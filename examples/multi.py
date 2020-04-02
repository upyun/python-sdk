# -*- coding: utf-8 -*-

import os
from concurrent import futures

import upyun
from upyun import resume


# 需要填写自己的服务名，操作员名，密码
service = ""
username = ""
password = ""

# 需要填写上传文件的本地路径和云存储路径
local_file = ""
remote_file = ""

# 并发配置
max_num_threads = 5
part_size = 1024 * 1024

up = upyun.UpYun(service, username=username, password=password)


def upload(loader, part_id, file_size):
    with open(local_file, 'rb') as f:
        start = part_id*part_size
        end = start + part_size
        if end > file_size:
            end = file_size
        value = resume.SizedFile(f, start, end)
        value.reset()
        loader.upload(part_id, value)
        return part_id


if __name__ == "__main__":
    uploader = up.init_multi_uploader(remote_file, part_size=part_size)
    executor = futures.ThreadPoolExecutor(max_workers=max_num_threads)
    file_size = os.path.getsize(local_file)
    count = (file_size + part_size - 1) // part_size
    f = (executor.submit(upload, uploader, i, file_size) for i in range(count))
    for future in futures.as_completed(f):
        part_id = future.result()
        print('upload:', part_id)
    resp = uploader.complete()
    print(resp)

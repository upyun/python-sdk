# -*- coding: utf-8 -*-
import os
import sys
import uuid

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)
import upyun


BUCKET = os.getenv('UPYUN_BUCKET')
USERNAME = os.getenv('UPYUN_USERNAME')
PASSWORD = os.getenv('UPYUN_PASSWORD')


def rootpath():
    return '/pysdk-%s/' % uuid.uuid4().hex


if __name__ == '__main__':
    up = upyun.UpYun(BUCKET, USERNAME, PASSWORD,
                     timeout=100, endpoint=upyun.ED_AUTO)
    root = rootpath()
    with open('/tmp/test.mp4', 'rb') as f:
        res = up.put(root + 'test.mp4', f, checksum=False)

    tasks = [{'type': 'probe', }, {'type': 'video', }]
    source = root + 'test.mp4'
    notify_url = 'http://httpbin.org/post'
    ids = up.pretreat(tasks, source, notify_url)
    print up.status(ids)

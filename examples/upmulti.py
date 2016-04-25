# -*- coding: utf-8 -*-
import os
import sys
import uuid

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)
import upyun


BUCKET = os.getenv('UPYUN_BUCKET')
SECRET = os.getenv('UPYUN_SECRET')


def rootpath():
    return '/pysdk-%s/' % uuid.uuid4().hex


if __name__ == '__main__':
    up = upyun.UpYun(BUCKET, secret=SECRET,
                     timeout=100, endpoint=upyun.ED_AUTO)
    root = rootpath()
    with open('tests/test.png', 'rb') as f:
        up.put(root + 'test.png', f, multipart=True)
    print up.getinfo(root + 'test.png')
    up.delete(root + 'test.png')

    up.delete(root)

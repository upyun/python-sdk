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
    # - put directly examples
    root = rootpath()
    up.put(root + 'test.txt', 'abcdefghijklmnopqrstuvwxyz\n')
    print up.getinfo(root + 'test.txt')
    up.delete(root + 'test.txt')

    # - put normallu examples
    with open('tests/test.png', 'rb') as f:
        up.put(root + 'test.png', f, checksum=False)
    print up.getinfo(root + 'test.png')
    up.delete(root + 'test.png')

    up.delete(root)

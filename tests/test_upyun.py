#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import upyun
import unittest

BUCKET = os.getenv('UPYUN_BUCKET')
USERNAME = os.getenv('UPYUN_USERNAME')
PASSWORD = os.getenv('UPYUN_PASSWORD')

BUCKET_TYPE = os.getenv('UPYUN_BUCKET_TYPE') or 'F'
up = upyun.UpYun(BUCKET, USERNAME, PASSWORD, timeout=30,
                 endpoint=upyun.ED_TELECOM)

root = "/pysdk/"


class TestUpYun(unittest.TestCase):

    def test_auth_failed(self):
        with self.assertRaises(upyun.UpYunServiceException) as se:
            upyun.UpYun("bucket", "username", "password").getinfo('/')
        self.assertEqual(se.exception.status, 401)

    def test_client_exception(self):
        with self.assertRaises(upyun.UpYunClientException):
            e = upyun.UpYun("bucket", "username", "password", timeout=3)
            e.endpoint = "e.api.upyun.com"
            e.getinfo('/')

    def test_root(self):
        res = up.getinfo('/')
        self.assertDictEqual(res, {'file-type': 'folder'})

    def test_usage(self):
        res = up.usage()
        self.assertGreaterEqual(int(res), 0)

    @unittest.skipUnless(BUCKET_TYPE == 'F', "only support file bucket")
    def test_put_directly(self):
        up.put(root + 'ascii.txt', 'abcdefghijklmnopqrstuvwxyz\n')
        res = up.get(root + 'ascii.txt')
        self.assertEqual(res, 'abcdefghijklmnopqrstuvwxyz\n')
        up.delete(root + 'ascii.txt')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            up.getinfo(root + 'ascii.txt')
        self.assertEqual(se.exception.status, 404)

    def test_put(self):
        with open('tests/unix.png', 'rb') as f:
            res = up.put(root + 'unix.png', f, checksum=False)
        if BUCKET_TYPE is not 'F':
            self.assertDictEqual(res, {'frames': '1', 'width': '580',
                                       'file-type': 'PNG', 'height': '363'})
        else:
            self.assertIsNone(res)
        res = up.getinfo(root + 'unix.png')
        self.assertIsInstance(res, dict)
        self.assertEqual(res['file-size'], '90833')
        self.assertEqual(res['file-type'], 'file')
        up.delete(root + 'unix.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            up.getinfo(root + 'unix.png')
        self.assertEqual(se.exception.status, 404)

    def test_put_with_checksum(self):
        with open('tests/unix.png', 'rb') as f:
            before = up._UpYun__make_content_md5(f)
            up.put(root + 'unix.png', f, checksum=True)
        with open('tests/get.png', "wb") as f:
            up.get(root + 'unix.png', f)
        with open('tests/get.png', "rb") as f:
            after = up._UpYun__make_content_md5(f)
        self.assertEqual(before, after)
        os.remove('tests/get.png')
        up.delete(root + 'unix.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            up.getinfo(root + 'unix.png')
        self.assertEqual(se.exception.status, 404)

    def test_mkdir(self):
        up.mkdir(root + 'temp')
        res = up.getinfo(root + 'temp')
        self.assertIsInstance(res, dict)
        self.assertEqual(res['file-type'], "folder")
        up.delete(root + 'temp')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            up.getinfo(root + 'temp')
        self.assertEqual(se.exception.status, 404)

    def test_getlist(self):
        up.mkdir(root + 'temp')
        with open('tests/unix.png', 'rb') as f:
            up.put(root + 'unix.png', f, checksum=False)
        res = up.getlist(root)
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 2)
        self.assertDictEqual(res[0], {'time': res[0]['time'], 'type': 'F',
                                      'name': 'temp', 'size': '0'})
        self.assertDictEqual(res[1], {'time': res[1]['time'], 'type': 'N',
                                      'name': 'unix.png', 'size': '90833'})
        up.delete(root + 'temp')
        up.delete(root + 'unix.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            up.getlist(root + 'temp')
        self.assertEqual(se.exception.status, 404)

    def test_delete(self):
        with open('tests/unix.png', 'rb') as f:
            up.put(root + 'temp/unix.png', f, checksum=False)
        with self.assertRaises(upyun.UpYunServiceException) as se:
            up.delete(root + 'temp')
        self.assertEqual(se.exception.status, 503)
        up.delete(root + 'temp/unix.png')
        up.delete(root + 'temp')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            up.getinfo(root + 'temp')
        self.assertEqual(se.exception.status, 404)

    @unittest.skipIf(BUCKET_TYPE == 'F', "only support picture bucket")
    def test_put_with_gmkerl(self):
        headers = {"x-gmkerl-rotate": "90"}
        with open('tests/unix.png', 'rb') as f:
            res = up.put(root + 'xinu.png', f, checksum=False,
                         headers=headers)
        self.assertDictEqual(res, {'frames': '1', 'width': '363',
                                   'file-type': 'PNG', 'height': '580'})
        up.delete(root + 'xinu.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            up.getinfo(root + 'xinu.png')
        self.assertEqual(se.exception.status, 404)

    def test_handler_progressbar(self):
        class ProgressBarHandler(object):
            def __init__(self, totalsize, params):
                params.assertEqual(totalsize, 90833)
                self.params = params
                self.readtimes = 0
                self.totalsize = totalsize

            def update(self, readsofar):
                self.readtimes += 1
                self.params.assertLessEqual(readsofar, self.totalsize)

            def finish(self):
                self.params.assertEqual(self.readtimes, 11)

        with open('tests/unix.png', 'rb') as f:
            up.put(root + 'unix.png', f, handler=ProgressBarHandler,
                   params=self)
        with open('tests/get.png', 'wb') as f:
            up.get(root + 'unix.png', f, handler=ProgressBarHandler,
                   params=self)
        up.delete(root + 'unix.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            up.getinfo(root + 'xinu.png')
        self.assertEqual(se.exception.status, 404)

# -*- coding: utf-8 -*-
import io
import os
import sys
import time
import types
import uuid
import requests

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

curpath = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, curpath)

import upyun
from upyun import FileStore

upyun.add_stderr_logger()


def b(s):
    PY3 = sys.version_info[0] == 3

    if PY3:
        return s.encode('utf-8')
    else:
        return s


SERVICE = os.getenv('UPYUN_SERVICE')
USERNAME = os.getenv('UPYUN_USERNAME')
PASSWORD = os.getenv('UPYUN_PASSWORD')


def rootpath():
    return '/pysdk-%s/' % uuid.uuid4().hex


class DjangoFile(io.BytesIO):
    def __len__(self):
        return len(self.getvalue())


class TestUpYun(unittest.TestCase):
    def setUp(self):
        self.up = upyun.UpYun(SERVICE, USERNAME, PASSWORD,
                              timeout=100, endpoint=upyun.ED_AUTO)
        self.root = rootpath()
        self.up.mkdir(self.root)

    def tearDown(self):
        self.delete(self.root)

    def delete(self, key):
        try:
            self.up.delete(key)
        except upyun.UpYunServiceException as se:
            if se.status == 429:
                time.sleep(2)
                self.up.delete(key)
            else:
                raise

    def test_getenv_info(self):
        upyun.UpYun(None).getinfo('/')

    def test_debug_func(self):
        up = upyun.UpYun(SERVICE, USERNAME, PASSWORD,
                         endpoint=upyun.ED_AUTO, debug=True)
        up.getinfo('/')
        os.remove('debug.log')

    def test_auth_failed(self):
        with self.assertRaises(upyun.UpYunServiceException) as se:
            upyun.UpYun('service', 'username', 'password').getinfo('/')
        self.assertEqual(se.exception.status, 401)

    def test_client_exception(self):
        with self.assertRaises(upyun.UpYunClientException):
            e = upyun.UpYun('service', username='username',
                            password='password', timeout=100)
            e.up_rest.endpoint = 'e.api.upyun.com'
            e.getinfo('/')

    def test_root(self):
        res = self.up.getinfo('/')
        self.assertTrue(res.get('file-type') == 'folder')

    def test_usage(self):
        res = self.up.usage()
        self.assertGreaterEqual(int(res), 0)

    def test_put_directly(self):
        self.up.put(self.root + 'test.txt', 'abcdefghijklmnopqrstuvwxyz\n')
        res = self.up.get(self.root + 'test.txt')
        self.assertEqual(res, 'abcdefghijklmnopqrstuvwxyz\n')
        self.delete(self.root + 'test.txt')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'test.txt')
            self.assertEqual(se.exception.status, 404)

    def test_move(self):
        res = self.up.put(self.root + 'test-move.txt', "move")
        self.assertEqual(res["content-length"], "4")
        time.sleep(1)
        res = self.up.get(self.root + 'test-move.txt')
        self.assertEqual(res, "move")
        time.sleep(1)
        res = self.up.move(self.root + 'test-move.txt',
                           self.root + 'test-move1.txt')
        self.assertEqual(res["content-length"], "4")
        time.sleep(1)
        res = self.up.get(self.root + 'test-move1.txt')
        self.assertEqual(res, "move")
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'test-move.txt')
        self.assertEqual(se.exception.status, 404)
        self.delete(self.root + 'test-move1.txt')

    def test_copy(self):
        res = self.up.put(self.root + 'test-copy.txt', "copy")
        self.assertEqual(res["content-length"], "4")
        time.sleep(1)
        res = self.up.get(self.root + 'test-copy.txt')
        self.assertEqual(res, "copy")
        time.sleep(1)
        res = self.up.copy(self.root + 'test-copy.txt',
                           self.root + 'test-copy1.txt')
        self.assertEqual(res["content-length"], "4")
        time.sleep(1)
        res = self.up.get(self.root + 'test-copy.txt')
        self.assertEqual(res, "copy")
        res = self.up.get(self.root + 'test-copy1.txt')
        self.assertEqual(res, "copy")
        self.delete(self.root + 'test-copy.txt')
        self.delete(self.root + 'test-copy1.txt')

    def test_put(self):
        with open('tests/test.png', 'rb') as f:
            res = self.up.put(self.root + 'test.png', f, checksum=False)
        self.assertDictEqual(res, {'frames': '1', 'width': '1000',
                                   'file-type': 'PNG', 'height': '410'})

        res = self.up.getinfo(self.root + 'test.png')
        self.assertIsInstance(res, dict)
        self.assertEqual(res['file-size'], '13001')
        self.assertEqual(res['file-type'], 'file')
        self.delete(self.root + 'test.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'test.png')
        self.assertEqual(se.exception.status, 404)

    def test_put_with_checksum(self):
        with open('tests/test.png', 'rb') as f:
            before = upyun.make_content_md5(f)
            self.up.put(self.root + 'test.png', f, checksum=True)
        with open('tests/get.png', 'wb') as f:
            self.up.get(self.root + 'test.png', f)
        with open('tests/get.png', 'rb') as f:
            after = upyun.make_content_md5(f)
        self.assertEqual(before, after)
        os.remove('tests/get.png')
        self.delete(self.root + 'test.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'test.png')
        self.assertEqual(se.exception.status, 404)

    def test_resume(self):
        with open('tests/resume.txt', 'w') as f:
            f.seek(15 * 1024 * 1024)
            f.write(uuid.uuid4().hex)
        with open('tests/resume.txt', 'rb') as f:
            before = upyun.make_content_md5(f)
            self.up.put(self.root + 'resume.txt',
                        f, checksum=True, need_resume=True)
        with open('tests/get.txt', 'wb') as f:
            self.up.get(self.root + 'resume.txt', f)
        with open('tests/get.txt', 'rb') as f:
            after = upyun.make_content_md5(f)
        self.assertEqual(before, after)
        os.remove('tests/get.txt')
        os.remove('tests/resume.txt')
        self.delete(self.root + 'resume.txt')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'resume.txt')
        self.assertEqual(se.exception.status, 404)

    def test_resume_small(self):
        with open('tests/small-resume.txt', 'w') as f:
            f.seek(300 * 1024)
            f.write(uuid.uuid4().hex)
        with open('tests/small-resume.txt', 'rb') as f:
            before = upyun.make_content_md5(f)
            self.up.put(self.root + 'small-resume.txt',
                        f, checksum=True, need_resume=True)
        with open('tests/get.txt', 'wb') as f:
            self.up.get(self.root + 'small-resume.txt', f)
        with open('tests/get.txt', 'rb') as f:
            after = upyun.make_content_md5(f)
        self.assertEqual(before, after)
        os.remove('tests/get.txt')
        os.remove('tests/small-resume.txt')
        self.delete(self.root + 'small-resume.txt')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'small-resume.txt')
        self.assertEqual(se.exception.status, 404)

    def test_resume_store(self):
        with open('tests/resume_store.txt', 'w') as f:
            f.seek(15 * 1024 * 1024)
            f.write('abcdefghijklmnopqrstuvwxyz')
        with open('tests/resume_store.txt', 'rb') as f:
            before = upyun.make_content_md5(f)
            self.up.put(self.root + 'resume_store.txt',
                        f, headers={"X-Upyun-Multi-Type": 'text/plain'},
                        checksum=True, need_resume=True, store=FileStore())
        with open('tests/get.txt', 'wb') as f:
            self.up.get(self.root + 'resume_store.txt', f)
        with open('tests/get.txt', 'rb') as f:
            after = upyun.make_content_md5(f)
        self.assertEqual(before, after)
        os.remove('tests/get.txt')
        os.remove('tests/resume_store.txt')
        self.delete(self.root + 'resume_store.txt')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'resume_store.txt')
        self.assertEqual(se.exception.status, 404)

    def test_mkdir(self):
        self.up.mkdir(self.root + 'test')
        res = self.up.getinfo(self.root + 'test')
        self.assertIsInstance(res, dict)
        self.assertEqual(res['file-type'], 'folder')
        self.delete(self.root + 'test')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'test')
        self.assertEqual(se.exception.status, 404)

    def test_getlist(self):
        self.up.mkdir(self.root + 'test')
        with open('tests/test.png', 'rb') as f:
            self.up.put(self.root + 'test.png', f, checksum=False)
        res = self.up.getlist(self.root)
        self.assertIsInstance(res, list)
        self.assertEqual(len(res), 2)
        if res[0]['type'] == 'F':
            a, b = res[0], res[1]
        else:
            a, b = res[1], res[0]
        self.assertDictEqual(a, {'time': a['time'], 'type': 'F',
                                 'name': 'test', 'size': '0'})
        self.assertDictEqual(b, {'time': b['time'], 'type': 'N',
                                 'name': 'test.png', 'size': '13001'})

        lines = self.up.iterlist(self.root)
        self.assertEqual(isinstance(lines, types.GeneratorType), True)
        for line in lines:
            if line['type'] == 'F':
                self.assertEqual(line['name'], 'test')
                self.assertEqual(line['size'], '0')
            else:
                self.assertEqual(line['type'], 'N')
                self.assertEqual(line['name'], 'test.png')
                self.assertEqual(line['size'], '13001')
        self.delete(self.root + 'test')
        self.delete(self.root + 'test.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getlist(self.root + 'test')
        self.assertEqual(se.exception.status, 404)

    def test_delete(self):
        self.up.mkdir(self.root + 'test')
        with open('tests/test.png', 'rb') as f:
            self.up.put(self.root + 'test/test.png', f, checksum=False)
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.delete(self.root + 'test')
        self.assertIn(se.exception.status, [503, 403])
        self.delete(self.root + 'test/test.png')
        self.delete(self.root + 'test')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'test')
        self.assertEqual(se.exception.status, 404)

    def test_put_with_gmkerl(self):
        headers = {'x-gmkerl-rotate': '90'}
        with open('tests/test.png', 'rb') as f:
            res = self.up.put(self.root + 'test.png', f, checksum=False,
                              headers=headers)
        self.assertDictEqual(res, {'frames': '1', 'width': '410',
                                   'file-type': 'PNG', 'height': '1000'})

        self.delete(self.root + 'test.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'test.png')
        self.assertEqual(se.exception.status, 404)

    def test_handler_progressbar(self):
        class ProgressBarHandler(object):
            def __init__(self, totalsize, params):
                params.assertEqual(totalsize, 13001)
                self.params = params
                self.readtimes = 0
                self.totalsize = totalsize

            def update(self, readsofar):
                self.readtimes += 1
                self.params.assertLessEqual(readsofar, self.totalsize)

            def finish(self):
                self.params.assertEqual(self.readtimes, 3)

        self.up.up_rest.chunksize = 4096

        with open('tests/test.png', 'rb') as f:
            self.up.put(self.root + 'test.png', f, handler=ProgressBarHandler,
                        params=self)
        with open('tests/get.png', 'wb') as f:
            self.up.get(self.root + 'test.png', f, handler=ProgressBarHandler,
                        params=self)

        self.delete(self.root + 'test.png')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'test.png')
        self.assertEqual(se.exception.status, 404)

    def test_purge(self):
        res = self.up.purge('/test.png')
        self.assertListEqual(res, [])
        res = self.up.purge(['/test.png', 'test/test.png'])
        self.assertListEqual(res, [])
        res = self.up.purge('/test.png', 'invalid.upyun.com')
        self.assertListEqual(res, [u'/test.png'])

    def test_filelike_object_flask(self):
        class ProgressBarHandler(object):
            def __init__(self, totalsize, params):
                params.assertEqual(totalsize, 13)

            def finish(self):
                pass

        f = io.BytesIO(b('www.upyun.com'))
        res = self.up.put(self.root + 'test.txt', f, checksum=True,
                          handler=ProgressBarHandler, params=self)
        self.assertDictEqual(res, {})
        f.close()
        self.delete(self.root + 'test.txt')

    def test_filelike_object_django(self):
        f = DjangoFile(b('www.upyun.com'))
        res = self.up.put(self.root + 'test.txt', f, checksum=False)
        self.assertDictEqual(res, {})
        f.close()
        self.delete(self.root + 'test.txt')

    def test_filelike_object_stream(self):
        res1 = requests.get("http://httpbin.org/image/jpeg", stream=True)
        size = res1.headers["Content-Length"]
        self.up.put(self.root + 'test.jpeg', res1.raw)
        res2 = self.up.getinfo(self.root + 'test.jpeg')
        self.assertEqual(res2["file-size"], size)
        self.delete(self.root + 'test.jpeg')

    def test_put_form(self):
        def __put(up, kwargs={}):
            with open('tests/test.png', 'rb') as f:
                res = self.up.put(self.root + 'test.png', f,
                                  checksum=False, form=True,
                                  **kwargs)
                self.assertEqual(res['code'], 200)
                self.assertEqual(res['image-height'], 410)
                self.assertEqual(res['image-width'], 1000)
                self.assertEqual(res['image-frames'], 1)
                self.assertEqual(res['image-type'], 'PNG')

            res = self.up.getinfo(self.root + 'test.png')
            self.assertIsInstance(res, dict)
            self.assertEqual(res['file-size'], '13001')
            self.assertEqual(res['file-type'], 'file')
            self.delete(self.root + 'test.png')
            with self.assertRaises(upyun.UpYunServiceException) as se:
                self.up.getinfo(self.root + 'test.png')
            self.assertEqual(se.exception.status, 404)
        # - test conflict upload method
        up = upyun.UpYun(SERVICE, USERNAME, PASSWORD,
                         timeout=100, endpoint=upyun.ED_AUTO)
        kwargs = {'allow-file-type': 'jpg,jpeg,png',
                  'notify-url': 'http://httpbin.org/post',
                  }
        __put(self.up)
        time.sleep(2)
        __put(self.up, kwargs=kwargs)
        time.sleep(2)
        __put(up)

    def test_put_form_placeholder(self):
        def __put(up, fname, kwargs={}):
            with open('tests/test.png', 'rb') as f:
                res = self.up.put(fname, f, form=True, **kwargs)

            rname = 'testtest.png.png'
            res = self.up.getinfo(self.root + rname)
            self.assertIsInstance(res, dict)
            self.assertEqual(res['file-size'], '13001')
            self.assertEqual(res['file-type'], 'file')
            self.delete(self.root + rname)
            with self.assertRaises(upyun.UpYunServiceException) as se:
                self.up.getinfo(self.root + rname)
            self.assertEqual(se.exception.status, 404)

        up = upyun.UpYun(SERVICE, USERNAME, PASSWORD,
                         timeout=100, endpoint=upyun.ED_AUTO)
        fname = self.root + '{filename}{filename}.{suffix}{.suffix}'
        __put(up, fname)

    def test_pretreat(self):
        with open('/tmp/test.mp4', 'rb') as f:
            res = self.up.put(self.root + 'test.mp4', f, checksum=False)
        self.assertDictEqual(res, {})
        tasks = [{'type': 'probe'}]

        source = self.root + 'test.mp4'
        notify_url = 'http://httpbin.org/post'
        ids = self.up.pretreat(tasks, source, notify_url)
        self.assertIsInstance(ids, list)
        tasks = self.up.status(ids)
        for taskid in ids:
            self.assertIn(taskid, tasks.keys())
        self.delete(self.root + 'test.mp4')
        with self.assertRaises(upyun.UpYunServiceException) as se:
            self.up.getinfo(self.root + 'test.mp4')
        self.assertEqual(se.exception.status, 404)

    def test_make_signature(self):
        headers = {
            'Date': 'Fri, 20 Jan 2017 08:46:20 GMT',
            'Content-MD5': 'd36489794822f8d33fd28217d8a5bed4',
            'Authorization': 'UPYUN upyun:kfIIHZ+vY9qwp+cZXE2m7jGWzcE='
        }

        self.assertEqual(
            headers['Authorization'],
            upyun.make_signature(username='upyun',
                                 password='4758a92de3f4dd368c01e0dad8578481',
                                 method='POST',
                                 uri='/api/v1/echo',
                                 date=headers['Date'],
                                 content_md5=headers['Content-MD5']))

    def test_auth_server(self):
        up = upyun.UpYun(SERVICE, USERNAME,
                         auth_server='http://localhost:8080')
        up.getinfo('/')

# -*- coding: utf-8 -*-

import hashlib
import base64
import json

from .compat import b, PY3, builtin_str, bytes, str
from .exception import UpYunClientException

DEFAULT_CHUNKSIZE = 8192


def make_content_md5(value, chunksize=DEFAULT_CHUNKSIZE):
    if hasattr(value, 'fileno'):
        md5 = hashlib.md5()
        for chunk in iter(lambda: value.read(chunksize), b''):
            md5.update(chunk)
        value.seek(0)
        return md5.hexdigest()
    elif isinstance(value, bytes) or (not PY3 and
                                      isinstance(value, builtin_str)):
        return hashlib.md5(value).hexdigest()
    else:
        raise UpYunClientException('object type error')


def decode_msg(msg):
    if isinstance(msg, bytes):
        msg = msg.decode('utf-8')
    return msg


def encode_msg(msg):
    if isinstance(msg, str):
        msg = msg.encode('utf-8')
    return msg


def make_policy(data):
    policy = json.dumps(data)
    return base64.b64encode(b(policy))


def make_rest_signature(bucket, username, password,
                        method, uri, date, length):
    if method:
        signstr = '&'.join([method, uri, date, str(length), password])
        signature = hashlib.md5(b(signstr)).hexdigest()
        return 'UpYun %s:%s' % (username, signature)

    else:
        signstr = '&'.join([uri, bucket, date, password])
        signature = hashlib.md5(b(signstr)).hexdigest()
        return 'UpYun %s:%s:%s' % (bucket, username, signature)


def make_multi_signature(data, secret):
    list_meta = sorted(data.items(), key=lambda d: d[0])
    signature = ''.join(map(lambda kv: '%s%s' %
                        (kv[0], str(kv[1])), list_meta))
    signature += secret
    return make_content_md5(b(signature))


def make_av_signature(data, operator, password):
    assert isinstance(data, dict)
    signature = ''.join(map(lambda kv: '%s%s' %
                        (kv[0],
                         kv[1] if type(kv[1]) != list else ''.join(kv[1])),
                        sorted(data.items())))
    signature = '%s%s%s' % (operator, signature, password)
    return make_content_md5(b(signature))

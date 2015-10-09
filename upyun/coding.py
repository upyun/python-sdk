# -*- coding: utf-8 -*-

from compat import str, bytes

def decode_msg(msg):
    if isinstance(msg, bytes):
        msg = msg.decode('utf-8')
    return msg

def encode_msg(msg):
    if isinstance(msg, str):
        msg = msg.encode('utf-8')
    return msg

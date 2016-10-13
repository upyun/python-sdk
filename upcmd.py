#!/usr/bin/env python
# -*- coding: utf-8 -*-
# By @Akagi201

import upyun


def init():
    import apikey as k
    return upyun.UpYun(k.UPYUN_BUCKET, k.UPYUN_USERNAME, k.UPYUN_PASSWORD, timeout=30, endpoint=upyun.ED_AUTO)


up = init()


def _run():
    global _run
    _run = lambda: None

    msg = """
===================================================
Welcome to UPYUN Interactive Shell!
Here, you can explore and play with UPYUN APIs :)
---------------------------------------------------
Getting Started:
    0. Register an account on http://www.upyun.com
    1. Write your bucket_name/username/password in apikey.py
    2. Start this interactive shell and try various APIs
        For example, to upload a file with a string content, just type:
            up.put('/upyun-python-sdk/ascii.txt', 'abcdefghijklmnopqrstuvwxyz\n')

Enjoy!
"""

    try:
        from IPython import embed
        embed(banner2=msg)
    except ImportError:
        import code
        code.interact(msg, local=globals())


if __name__ == '__main__':
    _run()

#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os
import sys
import upyun

if sys.version_info <= (2, 5) or sys.version_info >= (2, 8):
    error = "ERROR: UpYun SDK requires Python Version 2.6 or 2.7 ... exiting\n"
    sys.stderr.write(error)
    sys.exit(1)

setup(
    name='upyun',
    version=upyun.__version__,
    description='UpYun Storage SDK for Python',
    license='License :: OSI Approved :: MIT License',
    platforms='Platform Independent',
    author='Monkey Zhang (timebug)',
    author_email='timebug.info@gmail.com',
    url='https://github.com/upyun/python-sdk',
    packages=['upyun'],
    keywords=['upyun', 'python', 'sdk'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],
)

try:
    import requests
except ImportError:
    msg = "\nOPTIONAL: pip install requests (recommend)\n"
    sys.stderr.write(msg)

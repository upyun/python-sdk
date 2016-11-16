#! /usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

import os
import sys
import re


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

with open('upyun/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)

if not version:
    raise RuntimeError('Cannot find version information')

setup(
    name='upyun',
    version=version,
    description='UpYun Storage SDK for Python',
    license='License :: OSI Approved :: MIT License',
    platforms='Platform Independent',
    author='Monkey Zhang (timebug)',
    author_email='timebug.info@gmail.com',
    url='https://github.com/upyun/python-sdk',
    packages=['upyun', 'upyun.modules'],
    keywords=['upyun', 'python', 'sdk'],
    install_requires=['requests>=2.4.3'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
)

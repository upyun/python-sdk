#!/usr/bin/env python
# -*- coding: utf-8 -*-

OK = 0
HTTP_OK = 200

FILESIZE_TOO_LARGE = (403001, "file size is larger than 1G")
INCORRECT_INIT_UPLOAD_RESULT = (503001, "init upload api response incorrect message")
UPDATE_STATUS_FAILED = (503002, "update status failed")
POST_DATA_FAILED = 503003
MULTIPART_POST_FAILED = 503004
CHUNK_UPLOAD_FAILED = (503005, "chunk upload failed")
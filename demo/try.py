#! /usr/bin/env python
# -*- coding: utf-8 -*-

import upyun


# ------------------ CONFIG ---------------------
BUCKETNAME = 'bucketname'
USERNAME = 'username'
PASSWORD = 'password'
# -----------------------------------------------


def ascii():
    content = "abcdefghijklmnopqrstuvwxyz\n" + \
              "01234567890112345678901234\n" + \
              "!@#$%^&*()-=[]{};':',.<>/?\n" + \
              "01234567890112345678901234\n" + \
              "abcdefghijklmnopqrstuvwxyz\n"

    return content


def run():

    up = upyun.UpYun(BUCKETNAME, USERNAME, PASSWORD, timeout=30,
                     endpoint=upyun.ED_AUTO)

    print "=================================================="
    print "Getting Started with UpYun Storage Service"
    print "==================================================\n"

    rootpath = '/upyun-python-sdk/'

    try:
        res = None

        print "Uploading a new object to UpYun from a file ... ",
        headers = {"x-gmkerl-rotate": "180"}
        with open('unix.png', 'rb') as f:
            res = up.put(rootpath + 'xinu.png', f, checksum=False,
                         headers=headers)
        print "oked\n"

        ispicbucket = True
        if res:
            print "[ width:%s, height:%s, frames:%s, type:%s ]\n" %\
                (res['width'], res['height'], res['frames'], res['file-type'])
        else:
            ispicbucket = False

        print "Downloading an object(%sxinu.png) ... " % rootpath,
        with open('xinu.png', 'wb') as f:
            up.get(rootpath + 'xinu.png', f)
        print 'oked\n'

        if not ispicbucket:
            print "Uploading a new object to UpYun from a stream "\
                  "of ASCII characters ... ",
            res = up.put(rootpath + 'ascii.txt', ascii(), checksum=True)
            print "oked\n"

            print "Downloading an object(%sascii.txt) ... " % rootpath,
            res = up.get(rootpath + 'ascii.txt')
            print "oked\n"

            if res:
                print res

        print "Creating an empty directory(%stemp/) ..." % rootpath,
        up.mkdir(rootpath + 'temp')
        print "oked\n"

        # up.endpoint = upyun.ED_TELECOM

        print "Listing objects ...",
        res = up.getlist(rootpath)
        print "oked\n"
        if res:
            space = 12
            types = ["name", "type", "size", "time"]
            print '|'.join([t.center(space) for t in types])
            print '-'*(space*len(types)+len(types)-1)
            for item in res:
                print '|'.join([' ' + item[t].ljust(space-1) for t in types])
            print

        print "Querying directory(%s) usage ... " % rootpath,
        res = up.usage(rootpath)
        print "oked\n"
        if res:
            print "[ use:" + res + " ]\n"

        print "Querying an object(%sxinu.png) info ..." % rootpath,
        res = up.getinfo(rootpath + 'xinu.png')
        print "oked\n"
        if res:
            print "[ type:%s, size:%s, date:%s ]" % \
                  (res['file-type'], res['file-size'], res['file-date'])
            print

        print "Deleting objects ...",
        up.delete(rootpath + 'xinu.png')
        if not ispicbucket:
            up.delete(rootpath + 'ascii.txt')
        up.delete(rootpath + 'temp')
        up.delete(rootpath)
        print "oked\n"

    except upyun.UpYunServiceException as se:
        print "failed\n"
        print "Except an UpYunServiceException ..."
        print "HTTP Status Code: " + str(se.status)
        print "Error Message:    " + se.msg + "\n"
        if se.err:
            print se.err
    except upyun.UpYunClientException as ce:
        print "failed\n"
        print "Except an UpYunClientException ..."
        print "Error Message: " + ce.msg + "\n"


if __name__ == '__main__':
    run()

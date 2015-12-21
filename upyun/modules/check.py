# -*- coding: utf-8 -*-
from .exception import UpYunClientException


# a decoration to check if example has members
def has_object(obj_name):
    def deco(func):
        def _(self, *a, **kw):
            if not hasattr(self, obj_name):
                msg = 'Class Upyun dont have an attr called %s' % obj_name
                raise UpYunClientException(msg)
            return func(self, *a, **kw)
        return _
    return deco

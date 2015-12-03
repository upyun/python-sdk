# -*- coding: utf-8 -*-

# --- a decoration to check if example has members
def has_object(obj_name):
    def deco(func):
        def _(self, *a, **kw):
            if not hasattr(self, obj_name):
                raise UpYunClientException()
            return func(self, *a, **kw)
        return _
    return deco
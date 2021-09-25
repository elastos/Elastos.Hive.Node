# -*- coding: utf-8 -*-

"""
Request utils.
"""
from flask import request


class RequestParams:
    def __init__(self):
        pass

    def get(self, key, def_val=None):
        return self.get2(key, def_val)[1]

    def get2(self, key, def_val=None):
        body = request.get_json(force=True, silent=True)
        if not body or type(body) is not dict:
            return None, None
        return body, body.get(key, def_val)


params = RequestParams()

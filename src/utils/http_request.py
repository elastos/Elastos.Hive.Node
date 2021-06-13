# -*- coding: utf-8 -*-

"""
Request utils.
"""
from flask import request


class RequestParams:
    def __init__(self):
        pass

    def get(self, key):
        return self.get2(key)[1]

    def get2(self, key):
        body = request.get_json(force=True, silent=True)
        if not body or type(body) is not dict:
            return None, None
        return body, body.get(key)


params = RequestParams()

# -*- coding: utf-8 -*-

"""
Request utils.
"""
from flask import request


class RequestParams:
    def __init__(self):
        pass

    def get(self, key):
        body = request.get_json(force=True, silent=True)
        if not body or type(body) is not dict:
            return None
        return body.get(key)


params = RequestParams()

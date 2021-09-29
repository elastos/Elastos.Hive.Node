# -*- coding: utf-8 -*-

"""
Request utils.
"""
import json

from flask import request


class RequestParams:
    def __init__(self):
        pass

    def get(self, key, def_val=None):
        # TODO:
        return self.__get2(key, def_val)[1]

    def __get2(self, key, def_val=None):
        # TODO: remove directly.
        body = request.get_json(force=True, silent=True)
        if not body or type(body) is not dict:
            return None, None
        return body, body.get(key, def_val)

    def get_body(self):
        body = request.get_json(force=True, silent=True)
        if not body or type(body) is not dict:
            return {}, f'Invalid request body.'
        return body, None

    def get_dict(self, key):
        body, msg = self.get_body()
        if msg:
            return {}, msg
        if key not in body:
            return {}, f'The parameter {key} does not exist.'
        val = body.get(key)
        if type(val) is not dict:
            return {}, f'The parameter {key} does not valid.'
        return val, None

    def get_str(self, key, def_val=''):
        body, msg = self.get_body()
        if msg:
            return def_val, msg
        if key not in body:
            return def_val, f'The parameter {key} does not exist.'
        val = body.get(key, def_val)
        if type(val) is not str:
            return def_val, f'The parameter {key} does not valid.'
        return val, None


class RequestArgs:
    def __init__(self):
        pass

    def get_int(self, key, def_val=0):
        val_str = request.args.get(key)
        if not val_str:
            return def_val, None
        try:
            return int(val_str), None
        except ValueError:
            return def_val, f'Invalid parameter {key}.'

    def get_str(self, key, def_val=''):
        if key not in request.args:
            return def_val, f'Invalid parameter {key}'
        return request.args.get(key, def_val), None

    def get_bool(self, key, def_val=False):
        val_str, _ = self.get_str(key)
        if val_str != '' and val_str != 'true' and val_str != 'false':
            return def_val, f'Invalid parameter {key}.'
        return val_str == 'true', None

    def get_dict(self, key):
        val_str, msg = self.get_str(key)
        if msg:
            return {}, msg
        try:
            result = json.loads(val_str) if (val_str, None) else ({}, None)
            if type(result) is not dict:
                return {}, f'Invalid parameter {key}.'
            return result, None
        except Exception as e:
            return {}, f'Invalid parameter {key}, not json format.'


params = RequestParams()
rqargs = RequestArgs()

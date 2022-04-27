# -*- coding: utf-8 -*-

"""
Request utils.
"""
import json

from flask import request
from werkzeug.routing import BaseConverter


class RegexConverter(BaseConverter):
    """ Support regex on url match """
    def __init__(self, url_map, *items):
        super().__init__(url_map)
        self.regex = items[0]


class BaseParams:
    def __init__(self):
        pass

    def get_root(self):
        # INFO: Override this.
        return {}, None

    def get_str(self, key, def_val=''):
        root, msg = self.get_root()
        if msg:
            return def_val, msg
        if key not in root:
            return def_val, f'The parameter {key} does not exist.'
        val = root.get(key, def_val)
        if type(val) is not str:
            return def_val, f'The parameter {key} does not valid.'
        return val, None

    def get_list(self, key):
        root, msg = self.get_root()
        if msg:
            return [], msg
        if key not in root:
            return [], f'The parameter {key} does not exist.'
        val = root.get(key, [])
        if type(val) is not str:
            return [], f'The parameter {key} does not valid.'
        return val, None


class RequestParams(BaseParams):
    def __init__(self):
        """ request body args """
        super().__init__()

    def get_root(self):
        body = request.get_json(force=True, silent=True)
        if not body or type(body) is not dict:
            return {}, f'Invalid request body.'
        return body, None

    def get_int(self, key, def_val=0):
        root, msg = self.get_root()
        if msg:
            return def_val, msg
        val = root.get(key)
        if type(val) != int:
            return def_val, f'Invalid parameter {key}.'
        return val, None

    def get_bool(self, key, def_val=False):
        root, msg = self.get_root()
        if msg:
            return def_val, msg
        val = root.get(key)
        if type(val) != bool:
            return def_val, f'Invalid parameter {key}.'
        return val, None

    def get_list(self, key, def_val=None):
        def_list = [] if def_val is None else def_val
        root, msg = self.get_root()
        if msg:
            return def_list, msg
        val = root.get(key)
        if type(val) != list:
            return def_val, f'Invalid parameter {key}.'
        return val, None

    def get_dict(self, key) -> (dict, str):
        body, msg = self.get_root()
        if msg:
            return {}, msg
        if key not in body:
            return {}, f'The parameter {key} does not exist.'
        val = body.get(key)
        if type(val) is not dict:
            return {}, f'The parameter {key} does not valid.'
        return val, None


class RequestArgs(BaseParams):
    def __init__(self):
        """ url args """
        super().__init__()

    def get_root(self):
        return request.args, None

    def get_int(self, key, def_val=0):
        val_str, msg = self.get_str(key)
        if msg:
            return def_val, msg
        elif not val_str:
            return def_val, None
        try:
            return int(val_str), None
        except ValueError:
            return def_val, f'Invalid parameter {key}.'

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

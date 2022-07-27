# -*- coding: utf-8 -*-

"""
Request utils.
"""
import json
import typing

from flask import request, g
from werkzeug.routing import BaseConverter

from src.utils.http_exception import InvalidParameterException


class FileFolderPath(BaseConverter):
    """ support read empty folder path, based on PathConverter """
    regex = r'[0-9a-zA-Z_/.]*'
    weight = 200
    part_isolating = False


class RegexConverter(BaseConverter):
    """ Support regex on url match
    @deprecated
    """
    def __init__(self, url_map, *items):
        super().__init__(url_map)
        self.regex = items[0]


# @deprecated start


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


class RequestBodyParams(BaseParams):
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


class RequestArgsParams(BaseParams):
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


params = RequestBodyParams()
rqargs = RequestArgsParams()


# @deprecated end


def get_dict(json_data: typing.Any, parent_name: str = None):
    """ parent name is "a.b.c", then return dict json_data["a"]["b"]["c"] """

    # value MUST be dict
    if not json_data or not isinstance(json_data, dict):
        raise InvalidParameterException(f'Invalid Parameter: "{json_data}" MUST be dictionary')

    # parent_name is like 'a.b.c'
    if parent_name:
        parts = parent_name.split('.')
        if (length := len(parts)) > 0:
            key = parts[0]
            if key not in json_data:
                raise InvalidParameterException(f'Invalid Parameter: Not found key "{key}"')

            return get_dict(json_data[key], parent_name='.'.join(parts[1:]) if length > 1 else None)
        else:
            # if parent_name is '.'
            return json_data

    return json_data


class RequestData(dict):
    """ request.body or other dict needs to get data """

    def __init__(self, *args, optional=False, **kwargs):
        """
        :param optional this dict is an optional dict from its parent
        """
        super().__init__(*args, **kwargs)
        self.optional = optional

    def get(self, key, type_=dict):
        """ get the value with type 'value_type' """
        if self.optional:
            raise InvalidParameterException(f'Invalid parameter: Can not get optional key "{key}"')

        if key not in self:
            raise InvalidParameterException(f'Invalid parameter: Not found key "{key}"')

        if type(self[key]) != type_:
            raise InvalidParameterException(f'Invalid parameter: The value of the key "{key}" MUST be the type "{type_}"')

        return RequestData(**get_dict(self[key])) if type_ == dict else self[key]

    def get_opt(self, key, type_, def_value):
        """ get the optional value with type 'value_type' and default value 'def_value'

        Note: the member of optional dict is also optional.

        :return: RequestData() if value_type=dict else None
        """
        if key not in self:
            return RequestData(optional=True) if type_ == dict else def_value

        if type(self[key]) != type_:
            raise InvalidParameterException(f'Invalid parameter: The value of the key "{key}" MUST be the type "{type_}"')

        return RequestData(optional=True, **get_dict(self[key])) if type_ == dict else self[key]

    def validate(self, key, type_=dict):
        if self.optional:
            raise InvalidParameterException(f'Invalid parameter: Can not get optional key "{key}"')

        if key not in self:
            raise InvalidParameterException(f'Invalid parameter: Not found key "{key}"')

        if type(self[key]) != type_:
            raise InvalidParameterException(f'Invalid parameter: The value of the key "{key}" MUST be the type "{type_}"')

    def validate_opt(self, key, type_=dict):
        if key in self and type(self[key]) != type_:
            raise InvalidParameterException(f'Invalid parameter: The value of the key "{key}" MUST be the type "{type_}"')


class RequestArgs(dict):
    """ request.args

    The different is that the 'dict' member is string.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def convert_value(key, value_str, type_, optional=False):
        """ convert string value to specific type one, key is for error message. """
        # all values from args are strings.
        if not value_str:
            raise InvalidParameterException(f'Invalid parameter: Not found args "{key}"')

        if type_ == dict:
            try:
                value = json.loads(value_str)
                if not isinstance(value, dict):
                    raise InvalidParameterException(f'Invalid parameter: The args "{key}" MUST be dictionary')
            except Exception as e:
                raise InvalidParameterException(f'Invalid parameter: The args "{key}" MUST be JSON')
            return RequestData(optional=optional, **value)
        elif type_ == int:
            try:
                value = int(value_str)
            except Exception as e:
                raise InvalidParameterException(f'Invalid parameter: The args "{key}" MUST be integer')
            return value
        elif type_ == bool:
            if value_str not in ['true', 'false']:  # JSON specification
                raise InvalidParameterException(f'Invalid parameter: The args "{key}" MUST be bool ("true", "false")')
            return value_str == 'true'
        return value_str

    def get(self, key, type_=dict):
        """ get the value with type 'value_type' """
        if key not in self:
            raise InvalidParameterException(f'Invalid parameter: Not found args "{key}"')

        return self.convert_value(key, self[key], type_)

    def get_opt(self, key, type_, def_value):
        if key not in self:
            return RequestData(optional=True) if type_ == dict else def_value

        return self.convert_value(key, self[key], type_, optional=True)

    def validate(self, key, type_=dict):
        self.get(key, type_)

    def validate_opt(self, key, type_=dict):
        self.get_opt(key, type_, None)


class RV:
    """ RequestValidator

    Validate the request args (url) and body, or get the value from them.
    It will be convenient to validate the data from http request.

    The following is the examples:

        RV.get_args()  # request args
        RV.get_body()  # request body
        RV.get_body(parent_name="executable.body")

        # get
        value = RV.get_body().get('executable')
        value = RV.get_body().get('collection_name', str)
        value = RV.get_body().get('allowAnonymousUser', bool)
        value = RV.get_body().get('executable').get('body')
        value = RV.get_body().get('executable').get('type', str)
        value = RV.get_body().get('executable').get('output', bool)

        # get optional
        value = RV.get_body().get_opt('executable')
        value = RV.get_body().get_opt('collection_name', str)
        value = RV.get_body().get_opt('allowAnonymousUser', bool)
        value = RV.get_body().get_opt('executable').get_opt('body')
        value = RV.get_body().get_opt('executable').get_opt('type', str, '')
        value = RV.get_body().get_opt('executable').get_opt('output', bool, True)

        # validate
        RV.get_body().validate('executable')
        RV.get_body().validate('collection_name', str)
        RV.get_body().validate('allowAnonymousUser', bool)
        RV.get_body().get('executable').validate('body')
        RV.get_body().get('executable').validate('type', str)
        RV.get_body().get('executable').validate('output', bool)

        # validate optional
        RV.get_body().validate_opt('executable')
        RV.get_body().validate_opt('collection_name', str)
        RV.get_body().validate_opt('allowAnonymousUser', bool)
        RV.get_body().get('executable').validate_opt('body')
        RV.get_body().get('executable').validate_opt('type', str)
        RV.get_body().get('executable').validate_opt('output', bool)

    """

    @staticmethod
    def get_body(parent_name: str = None):
        """ get body args in dict """
        if not hasattr(g, 'body'):
            body = request.get_json(force=True, silent=True)
            if not isinstance(body, dict):
                raise InvalidParameterException('Invalid request body: MUST be dictionary')
            g.body = RequestData(**body)
        return RequestData(**get_dict(g.body, parent_name))

    @staticmethod
    def get_args():
        """ get url args in dict """
        if not hasattr(g, 'args'):
            g.args = RequestArgs(**request.args)
        return g.args

    @staticmethod
    def get_value(key, value, type_):
        """ This is for endpoint function parameters """
        return RequestArgs.convert_value(key, value, type_)


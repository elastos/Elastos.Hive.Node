# -*- coding: utf-8 -*-

"""
Defines all success and error http response code and body.
For new exception, please define here.
"""
from bson import json_util
from flask import jsonify, request
import traceback
import logging
import json


class HiveException(BaseException):
    NO_INTERNAL_CODE = -1

    def __init__(self, code, internal_code, msg):
        self.code = code
        self.internal_code = internal_code
        self.msg = msg

    def get_error_response(self):
        error = {"message": self.msg}
        if self.internal_code > 0:
            error['internal_code'] = self.internal_code
        return jsonify({"error": error}), self.code

    @staticmethod
    def get_success_response(data, is_download=False, is_code=False):
        code = HiveException.__get_success_http_code()
        if is_code:
            # Support user-defined http status code.
            assert type(data) is tuple and len(data) == 2
            data, code = data[0], data[1]
        json_data = data if is_download else (json.dumps(data, default=json_util.default) if data else '')
        return json_data, code

    @staticmethod
    def __get_success_http_code():
        codes = {
            'GET': 200,
            'PUT': 200,
            'PATCH': 200,
            'POST': 201,
            'DELETE': 204,
        }
        assert request.method in codes
        return codes[request.method]


class BadRequestException(HiveException):
    UNCAUGHT_EXCEPTION = 1
    INVALID_PARAMETER = 2
    ALREADY_EXISTS = 3
    VAULT_NO_PERMISSION = 4
    DOES_NOT_EXISTS = 5

    def __init__(self, internal_code=INVALID_PARAMETER, msg='Invalid parameter'):
        super().__init__(400, internal_code, msg)


class UnauthorizedException(HiveException):
    def __init__(self, msg='You are unauthorized to make this request.'):
        super().__init__(401, super().NO_INTERNAL_CODE, msg)


class NotFoundException(HiveException):
    VAULT_NOT_FOUND = 1
    BACKUP_NOT_FOUND = 2
    SCRIPT_NOT_FOUND = 3
    COLLECTION_NOT_FOUND = 4

    def __init__(self, internal_code=VAULT_NOT_FOUND, msg='The vault does not found or not activate.'):
        super().__init__(404, internal_code, msg)


class VaultNotFoundException(NotFoundException):
    def __init__(self, msg='The vault does not found.'):
        super().__init__(internal_code=NotFoundException.VAULT_NOT_FOUND, msg=msg)


class BackupNotFoundException(NotFoundException):
    def __init__(self, msg='The backup vault does not found.'):
        super().__init__(internal_code=NotFoundException.BACKUP_NOT_FOUND)


class AlreadyExistsException(HiveException):
    def __init__(self, msg='Already exists.'):
        super().__init__(455, -1, msg)


class NotImplementedException(HiveException):
    def __init__(self, msg='Not implemented yet.'):
        super().__init__(501, super().NO_INTERNAL_CODE, msg)


def __get_restful_response_wrapper(func, is_download=False, is_code=False):
    def wrapper(self, *args, **kwargs):
        try:
            return HiveException.get_success_response(func(self, *args, **kwargs),
                                                      is_download=is_download,
                                                      is_code=is_code)
        except HiveException as e:
            return e.get_error_response()
        except Exception as e:
            logging.error(f'UNEXPECTED: {traceback.format_exc()}')
            return HiveException(500, BadRequestException.UNCAUGHT_EXCEPTION, traceback.format_exc()).get_error_response()
    return wrapper


def hive_restful_response(func):
    """
    Make sure the http response follows as version 2.
    This decorator is ONLY for class method.
        SUCCESS: json data, success http code for http method
        ERROR: {
            "error": {
                "message": "this is error message",
                "code": -1 # this is sub-error code.
            }
        }, error http code for http method
    """
    return __get_restful_response_wrapper(func)


def hive_restful_code_response(func):
    return __get_restful_response_wrapper(func, is_code=True)


def hive_download_response(func):
    return __get_restful_response_wrapper(func, is_download=True)

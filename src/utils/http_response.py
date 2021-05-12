# -*- coding: utf-8 -*-

"""
Defines all success and error http response code and body.
For new exception, please define here.
"""

from flask import jsonify, request
import traceback


class ErrorCode:
    UNCAUGHT_EXCEPTION          = 100001
    UNAUTHORIZED                = 100002
    VAULT_NOT_FOUND             = 100003
    VAULT_NO_PERMISSION         = 100004
    INVALID_PARAMETER           = 100005
    SCRIPT_NOT_FOUND            = 120001


class HiveException(BaseException):
    def __init__(self, http_code, code, msg):
        self.http_code = http_code
        self.code = code
        self.msg = msg

    def get_error_response(self):
        return jsonify({
            "error": {
                "message": self.msg,
                "code": self.code
            }
        }), self.http_code

    @staticmethod
    def get_success_response(data, is_download=False):
        json_data = data if is_download else (jsonify(data) if data else '')
        return json_data, HiveException.__get_success_http_code()

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
    def __init__(self, code=ErrorCode.INVALID_PARAMETER, msg='Invalid parameter'):
        super().__init__(400, code, msg)


class UnauthorizedException(HiveException):
    def __init__(self, code=ErrorCode.UNAUTHORIZED, msg='You are unauthorized to make this request.'):
        super().__init__(401, code, msg)


class NotFoundException(HiveException):
    def __init__(self, code=ErrorCode.VAULT_NOT_FOUND, msg='Vault not found or not activate.'):
        super().__init__(404, code, msg)


def __get_restful_response_wrapper(func, is_download=False):
    def wrapper(self, *args, **kwargs):
        try:
            return HiveException.get_success_response(func(self, *args, **kwargs), is_download)
        except HiveException as e:
            return e.get_error_response()
        except Exception as e:
            return HiveException(500, ErrorCode.UNCAUGHT_EXCEPTION, traceback.format_exc())
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


def hive_download_response(func):
    return __get_restful_response_wrapper(func, True)

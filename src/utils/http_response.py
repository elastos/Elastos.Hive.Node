# -*- coding: utf-8 -*-

"""
Defines all success and error http response code and body.
For new exception, please define here.
"""
import traceback
import logging

from flask import request
from flask_restful import Api
from sentry_sdk import capture_exception

from hive.util.server_response import ServerResponse
from src.utils.http_exception import HiveException, InternalServerErrorException


class HiveApi(Api):
    @staticmethod
    def _get_resp_success_code():
        codes = {
            'GET': 200,
            'PUT': 200,
            'PATCH': 200,
            'POST': 201,
            'DELETE': 204,
        }
        assert request.method in codes
        return codes[request.method]

    def make_response(self, data, *args, **kwargs):
        resp = super().make_response(data, *args, **kwargs)
        resp.status_code = HiveApi._get_resp_success_code()
        return resp

    def handle_error(self, e):
        """ Convert any exception (HiveException and Exception) to error response message. """
        if not hasattr(e, 'get_error_response'):
            e = InternalServerErrorException(msg=traceback.format_exc())
        return e.get_error_response()


server_response = ServerResponse("CallV2")


def __get_restful_response_wrapper(func, is_download=False, is_code=False):
    def wrapper(*args, **kwargs):
        try:
            return HiveException.get_success_response(func(*args, **kwargs), is_download=is_download, is_code=is_code)
        except HiveException as e:
            logging.getLogger('http response').error(f'HiveException: {str(e)}')
            capture_exception(error=Exception(f'HiveException: {str(e)}'))
            return e.get_error_response()
        except Exception as e:
            logging.getLogger('http response').error(f'UNEXPECTED: {traceback.format_exc()}')
            capture_exception(error=Exception(f'UNEXPECTED: {traceback.format_exc()}'))
            return InternalServerErrorException(msg=traceback.format_exc()).get_error_response()
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


def hive_stream_response(func):
    return __get_restful_response_wrapper(func, is_download=True)


def v2_wrapper(func):
    """ Wrapper for v1 modules to call v2 module functions.
    1. Use the class IpfsFiles in v2.

    For calling files.upload(name), please call like this:
        result, resp_err = v2_wrapper(files.upload)(name)
        if resp_err:
            return resp_err
    """
    def wrapper(*args, **kwargs):
        try:
            logging.getLogger('v2 wrapper').info(f'enter {request.full_path}, {request.method}')
            return func(*args, **kwargs), None
        except HiveException as e:
            logging.getLogger('v2 wrapper').error(f'HiveException: {str(e)}')
            return None, server_response.response_err(e.code, e.msg)
        except Exception as e:
            logging.getLogger('v2 wrapper').error(f'UNEXPECTED: {traceback.format_exc()}')
            return None, server_response.response_err(500, traceback.format_exc())
    return wrapper

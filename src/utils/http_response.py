# -*- coding: utf-8 -*-

"""
Defines all success and error http response code and body.
For new exception, please define here.
"""
import traceback
import logging

from flask import request

from src.utils.http_exception import HiveException, BadRequestException, InternalServerErrorException


def __get_restful_response_wrapper(func, is_download=False, is_code=False):
    def wrapper(self, *args, **kwargs):
        logging.getLogger('http response').info(f'enter {request.full_path}, {request.method}')
        try:
            return HiveException.get_success_response(func(self, *args, **kwargs),
                                                      is_download=is_download,
                                                      is_code=is_code)
        except HiveException as e:
            return e.get_error_response()
        except Exception as e:
            logging.error(f'UNEXPECTED: {traceback.format_exc()}')
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

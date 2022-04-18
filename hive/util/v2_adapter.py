"""
As the implementation of the files and scripting files service using the v2,
    this file is for v1 adapting v2 to match the method calling.
"""
import logging
import traceback

from flask import request
from sentry_sdk import capture_exception

from src import HiveException
from hive.util.server_response import ServerResponse

_server_response = ServerResponse("CallV2")


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
            return None, _server_response.response_err(e.code, e.msg)
        except Exception as e:
            msg = f'V2 wrapper error: {str(e)}, {traceback.format_exc()}'
            logging.getLogger('v2 wrapper').error(msg)
            capture_exception(error=Exception(f'V2W UNEXPECTED: {msg}'))
            return None, _server_response.response_err(500, msg)
    return wrapper

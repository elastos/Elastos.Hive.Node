# -*- coding: utf-8 -*-
"""
Defines all success and error http response code and body.
For new exception, please define here.
"""
import traceback
import logging
import typing as t

from werkzeug.exceptions import HTTPException
from flask import request, make_response, jsonify
from flask_restful import Api
from sentry_sdk import capture_exception

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
        """ Custom response for success response.
        :param data: the data returned by the API class method.
        :return: response object
        """
        resp = super().make_response(data, *args, **kwargs)
        resp.status_code = HiveApi._get_resp_success_code()
        return resp

    def handle_error(self, e):
        """ Convert any exception (HiveException, Exception, etc.) to error response message. """
        if isinstance(e, HTTPException):
            # the http exception from flask, here hive node has no opportunity to handle request in view
            return jsonify(HiveException.get_flask_error_dict(e.description)), e.code

        ex = e
        if not isinstance(e, HiveException):
            # to be treated as an unexpected exception
            msg = f'V2 internal error: {str(e)}, {traceback.format_exc()}'
            logging.getLogger('http response').error(msg)
            capture_exception(error=Exception(f'V2 UNEXPECTED: {msg}'))
            ex = InternalServerErrorException(msg)

        return jsonify(ex.get_error_dict()), ex.code


def response_stream(f: t.Callable[..., t.Any]) -> t.Callable[..., t.Any]:
    """ A decorator which makes the endpoint support the stream response """
    def wrapper(*args, **kwargs):
        ret_value = f(*args, **kwargs)
        if not ret_value or type(ret_value) is dict:
            return ret_value
        response = make_response(ret_value)
        response.headers['content-type'] = 'application/octet-stream'
        return response
    return wrapper

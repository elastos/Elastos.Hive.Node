import json

from flask import jsonify
import logging

from sentry_sdk import capture_exception

STATUS = "_status"
STATUS_OK = "OK"
STATUS_ERR = "ERR"


class ServerResponse:
    def __init__(self, logger_name="HiveNode"):
        self.logger = logging.getLogger(logger_name)

    def response_ok(self, data_dic=None):
        ret = {STATUS: STATUS_OK}
        if data_dic is not None:
            if not isinstance(data_dic, dict):
                msg = f'Invalid v1 response body: {str(data_dic)}'
                logging.getLogger('response ok').error(msg)
                capture_exception(error=Exception(f'V1 UNEXPECTED: {msg}'))
                return self.response_err(400, msg)

            ret.update(data_dic)

        return jsonify(ret)

    def response_err(self, code, msg):
        ret = {STATUS: STATUS_ERR}
        ret.update({"_error": {"code": code, "message": msg}})
        self.logger.error(msg)
        return jsonify(ret), code

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
            try:
                ret.update(data_dic)
            except Exception as e:
                capture_exception(error=Exception(f'invalid response body: {str(data_dic)}, {str(e)}'))
                return self.response_err(400, f'invalid response body: {str(data_dic)}, {str(e)}')
        self.logger.debug(json.dumps(ret))
        return jsonify(ret)

    def response_err(self, code, msg):
        ret = {STATUS: STATUS_ERR}
        ret.update({"_error": {"code": code, "message": msg}})
        self.logger.error(msg)
        capture_exception(error=Exception(f'error response: {str(ret)}'))
        return jsonify(ret), code

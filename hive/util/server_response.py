import json

from flask import jsonify
import logging

STATUS = "_status"
STATUS_OK = "OK"
STATUS_ERR = "ERR"


class ServerResponse:
    def __init__(self, logger_name="HiveNode"):
        self.logger = logging.getLogger(logger_name)

    def response_ok(self, data_dic=None):
        ret = {STATUS: STATUS_OK}
        if not isinstance(data_dic, dict):
            return self.response_err(500, f'impossible response body: {str(data_dic)}')

        try:
            ret.update(data_dic)
        except Exception as e:
            return self.response_err(400, f'invalid response body: {str(data_dic)}, {str(e)}')

        self.logger.debug(json.dumps(ret))
        return jsonify(ret)

    def response_err(self, code, msg):
        ret = {STATUS: STATUS_ERR}
        ret.update({"_error": {"code": code, "message": msg}})
        self.logger.error(msg)
        return jsonify(ret), code

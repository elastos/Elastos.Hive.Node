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
        if data_dic is not None:
            ret.update(data_dic)
        self.logger.debug(json.dumps(ret))
        return jsonify(ret)

    def response_err(self, code, msg):
        ret = {STATUS: STATUS_ERR}
        ret.update({"_error": {"code": code, "message": msg}})
        self.logger.error(msg)
        return jsonify(ret), code

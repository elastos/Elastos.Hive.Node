from eve import STATUS, STATUS_OK, STATUS_ERR
from flask import jsonify


def response_ok(data_dic=None):
    ret = {STATUS: STATUS_OK}
    if data_dic is not None:
        ret.update(data_dic)
    return jsonify(ret)


def response_err(code, msg):
    ret = {STATUS: STATUS_ERR}
    ret.update({"_error": {"code": code, "message": msg}})
    return jsonify(ret)

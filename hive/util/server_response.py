from flask import jsonify

STATUS = "_status"
STATUS_OK = "OK"
STATUS_ERR = "ERR"


def response_ok(data_dic=None):
    ret = {STATUS: STATUS_OK}
    if data_dic is not None:
        ret.update(data_dic)
    return jsonify(ret)


def response_err(code, msg):
    ret = {STATUS: STATUS_ERR}
    ret.update({"_error": {"code": code, "message": msg}})
    return jsonify(ret), code

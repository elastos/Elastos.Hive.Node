from flask import request, jsonify
from hive.util.auth import did_auth
from hive.util.server_response import response_err


def init_app(app):
    app.register_error_handler(500, handle_exception_500)


def pre_proc():
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, response_err(401, "auth failed")

    return did, app_id, None


def post_json_param_pre_proc(*args):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, None, response_err(401, "auth failed")

    content = request.get_json(force=True, silent=True)
    if content is None:
        return did, app_id, None, response_err(400, "parameter is not application/json")

    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return did, app_id, None, response_err(400, "parameter " + arg + " is null")

    return did, app_id, content, None


def get_pre_proc(*args):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, None, response_err(401, "auth failed")

    content = dict()
    for arg in args:
        data = request.args.get(arg, None)
        if data is None:
            return did, app_id, None, response_err(400, "parameter " + arg + " is null")
        else:
            content[arg] = data

    return did, app_id, content, None


def handle_exception_500(e):
    return response_err(500, "Exception:" + str(e))

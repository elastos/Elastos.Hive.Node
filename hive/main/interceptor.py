from flask import request, jsonify
from hive.util.auth import did_auth
from hive.util.server_response import ServerResponse
from util.payment.vault_service_manage import can_access_vault


def init_app(app):
    app.register_error_handler(500, handle_exception_500)


def handle_exception_500(e):
    response = ServerResponse("HiveNode")
    return response.response_err(500, "Exception:" + str(e))


def pre_proc(response, access_vault=None):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, response.response_err(401, "auth failed")

    if access_vault:
        if not can_access_vault(did, app_id, access_vault):
            return did, app_id, response.response_err(401, "access vault failed")

    return did, app_id, None


def post_json_param_pre_proc(response, *args, access_vault=None):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, None, response.response_err(401, "auth failed")

    if access_vault:
        if not can_access_vault(did, app_id, access_vault):
            return did, app_id, None, response.response_err(401, "access vault failed")

    content = request.get_json(force=True, silent=True)
    if content is None:
        return did, app_id, None, response.response_err(400, "parameter is not application/json")

    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return did, app_id, None, response.response_err(400, "parameter " + arg + " is null")

    return did, app_id, content, None


def get_pre_proc(response, *args, access_vault=None):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, None, response.response_err(401, "auth failed")

    if access_vault:
        if not can_access_vault(did, app_id, access_vault):
            return did, app_id, None, response.response_err(401, "access vault failed")

    content = dict()
    for arg in args:
        data = request.args.get(arg, None)
        if data is None:
            return did, app_id, None, response.response_err(400, "parameter " + arg + " is null")
        else:
            content[arg] = data

    return did, app_id, content, None

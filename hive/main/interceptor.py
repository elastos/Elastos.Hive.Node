import logging
from datetime import datetime
import traceback

from flask import request
from hive.util.auth import did_auth
from hive.util.server_response import ServerResponse
from hive.util.payment.vault_service_manage import can_access_vault


def init_app(app):
    app.register_error_handler(500, handle_exception_500)


def handle_exception_500(e):
    response = ServerResponse("HiveNode")
    logging.getLogger("Hive exception").exception(f"handle_exception_500: {traceback.format_exc()}")
    return response.response_err(500, f"Exception at {str(datetime.utcnow())} error is:{str(e)}")


def pre_proc(response, access_vault=None):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, response.response_err(401, "auth failed")

    if access_vault:
        r, msg = can_access_vault(did, access_vault)
        if not r:
            return did, app_id, response.response_err(400, msg)

    return did, app_id, None


def post_json_param_pre_proc(response, *args, access_vault=None):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, None, response.response_err(401, "auth failed")

    if access_vault:
        r, msg = can_access_vault(did, access_vault)
        if not r:
            return did, app_id, None, response.response_err(400, msg)

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
        r, msg = can_access_vault(did, access_vault)
        if not r:
            return did, app_id, None, response.response_err(400, msg)

    content = dict()
    for arg in args:
        data = request.args.get(arg, None)
        if data is None:
            return did, app_id, None, response.response_err(400, "parameter " + arg + " is null")
        else:
            content[arg] = data

    return did, app_id, content, None

import logging
from datetime import datetime
import traceback

from flask import request
from hive.util.auth import did_auth
from hive.util.error_code import INTERNAL_SERVER_ERROR, BAD_REQUEST, UNAUTHORIZED, SUCCESS
from hive.util.server_response import ServerResponse
from hive.util.payment.vault_service_manage import can_access_vault, can_access_backup


def init_app(app):
    app.register_error_handler(INTERNAL_SERVER_ERROR, handle_exception_500)


def handle_exception_500(e):
    response = ServerResponse("HiveNode")
    logging.getLogger("Hive exception").exception(f"handle_exception_500: {str(e)}, {traceback.format_exc()}")
    return response.response_err(INTERNAL_SERVER_ERROR, f"Uncaught exception: {str(e)}, {traceback.format_exc()}")


def pre_proc(response, access_vault=None):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, response.response_err(UNAUTHORIZED, "auth failed")

    if access_vault:
        r, msg = can_access_vault(did, access_vault)
        if r != SUCCESS:
            return did, app_id, response.response_err(r, msg)

    return did, app_id, None


def post_json_param_pre_proc(response, *args, access_vault=None):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, None, response.response_err(UNAUTHORIZED, "auth failed")

    if access_vault:
        r, msg = can_access_vault(did, access_vault)
        if r != SUCCESS:
            return did, app_id, None, response.response_err(r, msg)

    content = request.get_json(force=True, silent=True)
    if content is None:
        return did, app_id, None, response.response_err(BAD_REQUEST, "parameter is not application/json")

    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return did, app_id, None, response.response_err(BAD_REQUEST, "parameter " + arg + " is null")

    return did, app_id, content, None


def get_pre_proc(response, *args, access_vault=None):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, None, response.response_err(UNAUTHORIZED, "auth failed")

    if access_vault:
        r, msg = can_access_vault(did, access_vault)
        if r != SUCCESS:
            return did, app_id, None, response.response_err(r, msg)

    content = dict()
    for arg in args:
        data = request.args.get(arg, None)
        if data is None:
            return did, app_id, None, response.response_err(BAD_REQUEST, "parameter " + arg + " is null")
        else:
            content[arg] = data

    return did, app_id, content, None


def did_post_json_param_pre_proc(response, *args, access_vault=None, access_backup=None):
    did, app_id = did_auth()
    if did is None:
        return did, None, response.response_err(UNAUTHORIZED, "auth failed")

    content = request.get_json(force=True, silent=True)
    if content is None:
        return did, None, response.response_err(BAD_REQUEST, "parameter is not application/json")

    if access_vault:
        r, msg = can_access_vault(did, access_vault)
        if r != SUCCESS:
            return did, app_id, None, response.response_err(r, msg)

    if access_backup:
        r, msg = can_access_backup(did)
        if r != SUCCESS:
            return did, None, response.response_err(r, msg)

    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return did, None, response.response_err(BAD_REQUEST, "parameter " + arg + " is null")

    return did, content, None


def did_get_param_pre_proc(response, *args, access_vault=None, access_backup=None):
    did, app_id = did_auth()
    if did is None:
        return did, None, response.response_err(UNAUTHORIZED, "auth failed")

    if access_vault:
        r, msg = can_access_vault(did, access_vault)
        if r != SUCCESS:
            return did, app_id, None, response.response_err(r, msg)

    if access_backup:
        r, msg = can_access_backup(did)
        if r != SUCCESS:
            return did, None, response.response_err(r, msg)

    content = dict()
    for arg in args:
        data = request.args.get(arg, None)
        if data is None:
            return did, app_id, None, response.response_err(BAD_REQUEST, "parameter " + arg + " is null")
        else:
            content[arg] = data
    return did, content, None

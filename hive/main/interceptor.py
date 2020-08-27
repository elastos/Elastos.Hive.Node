from flask import request
from hive.util.auth import did_auth
from hive.util.server_response import response_err
from hive.main.hive_sync import HiveSync


def post_json_param_pre_proc(*args):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return did, app_id, None, response_err(401, "auth failed")

    if not HiveSync.is_app_sync_prepared(did, app_id):
        return did, app_id, None, response_err(406, "drive is not prepared")

    content = request.get_json(force=True, silent=True)
    if content is None:
        return did, app_id, None, response_err(400, "parameter is not application/json")

    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return did, app_id, None, response_err(400, "parameter " + arg + " is null")

    return did, app_id, content, None

from flask import request
from hive.util.auth import did_auth
from hive.util.server_response import response_err

PREPROCESS_PARAM_TYPE_NONE = "none"
PREPROCESS_PARAM_TYPE_URL = "url"
PREPROCESS_PARAM_TYPE_GET = "get"
PREPROCESS_PARAM_TYPE_POST = "post"


def request_auth_preprocess(func, arg_type, *args):
    did, app_id = did_auth()
    if (did is None) or (app_id is None):
        return response_err(401, "auth failed")

    content = request.get_json(force=True, silent=True)
    if content is None:
        return response_err(400, "parameter is not application/json")
    collection = content.get('collection', None)
    schema = content.get('schema', None)
    if (collection is None) or (schema is None):
        return response_err(400, "parameter is null")
    return func(did, app_id, **content)

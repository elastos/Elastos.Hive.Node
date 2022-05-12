from flask import request

from src.utils_v1.constants import SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_EXECUTABLE_PARAMS, \
    SCRIPTING_EXECUTABLE_CALLER_APP_DID
from src.utils_v1.error_code import BAD_REQUEST


def massage_keys_with_dollar_signs(d):
    for key, value in d.copy().items():
        if key[0] == "$" and key not in [SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_EXECUTABLE_CALLER_APP_DID,
                                         SCRIPTING_EXECUTABLE_PARAMS]:
            d[key.replace("$", "'$'")] = d.pop(key)
        if type(value) is dict:
            massage_keys_with_dollar_signs(value)
        elif type(value) is list:
            for item in value:
                massage_keys_with_dollar_signs(item)


def unmassage_keys_with_dollar_signs(d):
    for key, value in d.copy().items():
        if key[0:3] == "'$'":
            d[key.replace("'$'", "$")] = d.pop(key)
        if type(value) is dict:
            unmassage_keys_with_dollar_signs(value)
        elif type(value) is list:
            for item in value:
                unmassage_keys_with_dollar_signs(item)


def get_script_content(response, *args):
    content = request.get_json(force=True, silent=True)
    if content is None:
        return None, response.response_err(BAD_REQUEST, "parameter is not application/json")
    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return None, response.response_err(BAD_REQUEST, "parameter " + arg + " is null")
    return content, None


def check_json_param(content, content_type, args):
    if content is None:
        return f"parameter is null for '{content_type}"
    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return f"parameter '{arg}' is null for '{content_type}'"
    return None


def populate_file_body(body, params):
    if not body or not params \
            or not isinstance(body, dict) or not isinstance(params, dict) \
            or not body.get('path'):
        return

    value = body.get('path')
    if not isinstance(value, str) or not value:
        return

    for k, v in params.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        value = value.replace(f'$params.{k}', v)
        value = value.replace(f'${{params.{k}}}', v)

    if value != body.get('path'):
        body['path'] = value


def populate_with_params_values(did, app_did, options, params):
    """
    replace $params to the real value in options.
    :return error message
    """
    if not options or not params:
        return None

    for key, value in options.copy().items():
        if isinstance(value, dict):
            populate_with_params_values(did, app_did, value, params)
        elif isinstance(value, str):
            if value == SCRIPTING_EXECUTABLE_CALLER_DID:
                options[key] = did
            elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
                options[key] = app_did
            elif value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
                v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
                try:
                    v = params[v]
                except Exception as e:
                    return f"Exception: {str(e)}"
                options[key] = v
            else:
                options[key] = value
        else:
            options[key] = value
    return None

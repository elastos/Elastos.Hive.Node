from flask import request

from hive.util.constants import SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_EXECUTABLE_PARAMS, \
    SCRIPTING_EXECUTABLE_CALLER_APP_DID
from hive.util.did_file_info import query_download, query_properties, query_hash, query_upload_get_filepath
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import populate_options_find_many, \
    query_insert_one, query_find_many, populate_options_insert_one, populate_options_count_documents, \
    query_count_documents, populate_options_update_one, query_update_one, query_delete_one


def massage_keys_with_dollar_signs(d):
    for key, value in d.items():
        if key[0] == "$" and key not in [SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_EXECUTABLE_CALLER_APP_DID,
                                         SCRIPTING_EXECUTABLE_PARAMS]:
            d[key.replace("$", "'$'")] = d.pop(key)
        if type(value) is dict:
            massage_keys_with_dollar_signs(value)
        elif type(value) is list:
            for item in value:
                massage_keys_with_dollar_signs(item)


def unmassage_keys_with_dollar_signs(d):
    for key, value in d.items():
        if key[0:3] == "'$'":
            d[key.replace("'$'", "$")] = d.pop(key)
        if type(value) is dict:
            unmassage_keys_with_dollar_signs(value)
        elif type(value) is list:
            for item in value:
                unmassage_keys_with_dollar_signs(item)


def check_json_param(content, content_type, args):
    if content is None:
        return f"parameter is null for '{content_type}"
    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return f"parameter '{arg}' is null for '{content_type}'"
    return None


def run_condition(did, app_did, target_did, target_app_did, condition_body, params):
    query = {}
    for key, value in condition_body.get('filter').items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[key] = {"$in": [did]}
        elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
            query[key] = {"$in": [app_did]}
        elif value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
            v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
            if not (params and params.get(v, None)):
                return False
            query[key] = params[v]
        else:
            query[key] = value
    condition_body["filter"] = query

    options = populate_options_count_documents(condition_body)

    col = get_collection(target_did, target_app_did, condition_body.get('collection'))
    data, err_message = query_count_documents(col, condition_body, options)
    if err_message:
        return False
    if data.get('count') == 0:
        return False

    return True


def run_executable_find(did, app_did, target_did, target_app_did, executable_body, params):
    query = {}
    executable_body_filter = executable_body.get('filter', None)
    if executable_body_filter:
        for key, value in executable_body.get('filter').items():
            if value == SCRIPTING_EXECUTABLE_CALLER_DID:
                query[key] = {"$in": [did]}
            elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
                query[key] = {"$in": [app_did]}
            elif value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
                v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
                if not (params and params.get(v, None)):
                    return None, "Exception: Parameter is not set"
                query[key] = params[v]
            else:
                query[key] = value
        executable_body["filter"] = query

    options = populate_options_find_many(executable_body)

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_find_many(col, executable_body, options)
    if err_message:
        return None, err_message

    return data, None


def run_executable_insert(did, app_did, target_did, target_app_did, executable_body, params):
    created = False
    query = {}
    for key, value in executable_body.get('document').items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[key] = did
        elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
            query[key] = app_did
        else:
            if key == "created":
                created = True
            if value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
                k = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
                if not (params and params.get(k, None)):
                    return None, "Exception: Parameter is not set"
                v = params[k]
            else:
                v = value
            query[key] = v
    executable_body['document'] = query

    options = populate_options_insert_one(executable_body)

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_insert_one(col, executable_body, options, created=created)
    if err_message:
        return None, err_message

    return data, None


def run_executable_update(did, app_did, target_did, target_app_did, executable_body, params):
    filter_query = {}
    for key, value in executable_body.get('filter').items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            filter_query[key] = did
        elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
            filter_query[key] = app_did
        elif value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
            v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
            if not (params and params.get(v, None)):
                return None, "Exception: Parameter is not set"
            filter_query[key] = params[v]
        else:
            filter_query[key] = value
    executable_body['filter'] = filter_query
    update_set_query = {}
    for key, value in executable_body.get('update').get('$set').items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            update_set_query[key] = did
        elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
            update_set_query[key] = app_did
        elif value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
            v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
            if not (params and params.get(v, None)):
                return None, "Exception: Parameter is not set"
            update_set_query[key] = params[v]
        else:
            update_set_query[key] = value
    executable_body['update']['$set'] = update_set_query

    options = populate_options_update_one(executable_body)

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_update_one(col, executable_body, options)
    if err_message:
        return None, err_message

    return data, None


def run_executable_delete(did, app_did, target_did, target_app_did, executable_body, params):
    query = {}
    for key, value in executable_body.get('filter').items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[key] = {"$in": [did]}
        elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
            query[key] = {"$in": [app_did]}
        elif value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
            v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
            if not (params and params.get(v, None)):
                return None, "Exception: Parameter is not set"
            query[key] = params[v]
        else:
            query[key] = value
    executable_body["filter"] = query

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_delete_one(col, executable_body)
    if err_message:
        return None, err_message

    return data, None


def run_executable_file_upload(did, app_did, target_did, target_app_did, executable_body, params):
    executable_body_path = executable_body.get("path", "")
    file_name = ""
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        if not (params and params.get(v, None)):
            return None, "Exception: Parameter is not set"
        file_name = params[v]

    full_path_name, err = query_upload_get_filepath(target_did, target_app_did, file_name)
    if err:
        return None, f"Exception: Could not upload file. Status={err['status_code']} Error='{err['description']}'"
    try:
        uploaded_file = request.files['data']
        uploaded_file.save(full_path_name)
    except Exception as e:
        return None, f"Exception: Could not upload file. Error: {str(e)}"
    data = {
        "upload": "Successful",
        "path": file_name,
        "vault_endpoint": f"/api/v1/files/download?path={file_name}"
    }
    return data, None


def run_executable_file_download(did, app_did, target_did, target_app_did, executable_body, params):
    executable_body_path = executable_body.get("path", "")
    file_name = ""
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        if not (params and params.get(v, None)):
            return None, "Exception: Parameter is not set"
        file_name = params[v]

    data, status_code = query_download(target_did, target_app_did, file_name)
    if status_code != 200:
        return None, f"Exception: Could not download file. Status={status_code}"
    return data, None


def run_executable_file_properties(did, app_did, target_did, target_app_did, executable_body, params):
    executable_body_path = executable_body.get("path", "")
    name = ""
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        if not (params and params.get(v, None)):
            return None, "Exception: Parameter is not set"
        name = params[v]

    data, err = query_properties(target_did, target_app_did, name)
    if err:
        return None, f"Exception: Could not get properties of file. Status={err['status_code']} Error='{err['description']}'"
    return data, None


def run_executable_file_hash(did, app_did, target_did, target_app_did, executable_body, params):
    executable_body_path = executable_body.get("path", "")
    name = ""
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        if not (params and params.get(v, None)):
            return None, "Exception: Parameter is not set"
        name = params[v]

    data, err = query_hash(target_did, target_app_did, name)
    if err:
        return None, f"Exception: Could not get hash of file. Status={err['status_code']} Error='{err['description']}'"
    return data, None

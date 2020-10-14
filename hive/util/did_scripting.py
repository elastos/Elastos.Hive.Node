from hive.util.constants import SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_EXECUTABLE_PARAMS
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import populate_options_find_many, \
    query_insert_one, query_find_many, populate_options_insert_one, populate_options_count_documents, \
    query_count_documents, populate_options_update_one, query_update_one, query_delete_one


def check_json_param(content, content_type, args):
    if content is None:
        return f"parameter is null for '{content_type}"
    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return f"parameter '{arg}' is null for '{content_type}'"
    return None


def run_condition(did, app_id, target_did, condition_body, params):
    query = {}
    for key, value in condition_body.get('filter').items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[key] = {"$in": [did]}
        elif f"{SCRIPTING_EXECUTABLE_PARAMS}." in value:
            v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
            query[key] = params[v]
        else:
            query[key] = value
    condition_body["filter"] = query

    options = populate_options_count_documents(condition_body)

    col = get_collection(target_did, app_id, condition_body.get('collection'))
    data, err_message = query_count_documents(col, condition_body, options)
    if err_message:
        return False
    if data.get('count') == 0:
        return False

    return True


def run_executable_find(did, app_id, target_did, executable_body, params):
    query = {}
    executable_body_filter = executable_body.get('filter', None)
    if executable_body_filter:
        for key, value in executable_body.get('filter').items():
            if value == SCRIPTING_EXECUTABLE_CALLER_DID:
                query[key] = {"$in": [did]}
            elif f"{SCRIPTING_EXECUTABLE_PARAMS}." in value:
                v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
                query[key] = params[v]
            else:
                query[key] = value
        executable_body["filter"] = query

    options = populate_options_find_many(executable_body)

    col = get_collection(target_did, app_id, executable_body.get('collection'))
    data, err_message = query_find_many(col, executable_body, options)
    if err_message:
        return None, err_message

    return data, None


def run_executable_insert(did, app_id, target_did, executable_body, params):
    created = False
    query = {}
    for key, value in executable_body.get('document').items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[key] = did
        else:
            if key == "created":
                created = True
            if f"{SCRIPTING_EXECUTABLE_PARAMS}." in value:
                v = params[value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")]
            else:
                v = value
            query[key] = v
    executable_body['document'] = query

    options = populate_options_insert_one(executable_body)

    col = get_collection(target_did, app_id, executable_body.get('collection'))
    data, err_message = query_insert_one(col, executable_body, options, created=created)
    if err_message:
        return None, err_message

    return data, None


def run_executable_update(did, app_id, target_did, executable_body, params):
    filter_query = {}
    for key, value in executable_body.get('filter').items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            filter_query[key] = did
        elif f"{SCRIPTING_EXECUTABLE_PARAMS}." in value:
            v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
            filter_query[key] = params[v]
        else:
            filter_query[key] = value
    executable_body['filter'] = filter_query
    update_set_query = {}
    for key, value in executable_body.get('update').get("'$set'").items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            update_set_query[key] = did
        elif f"{SCRIPTING_EXECUTABLE_PARAMS}." in value:
            v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
            update_set_query[key] = params[v]
        else:
            update_set_query[key] = value
    executable_body['update'].pop("'$set'", None)
    executable_body['update']['$set'] = update_set_query

    options = populate_options_update_one(executable_body)

    col = get_collection(target_did, app_id, executable_body.get('collection'))
    data, err_message = query_update_one(col, executable_body, options)
    if err_message:
        return None, err_message

    return data, None


def run_executable_delete(did, app_id, target_did, executable_body, params):
    query = {}
    for key, value in executable_body.get('filter').items():
        if value == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[key] = {"$in": [did]}
        elif f"{SCRIPTING_EXECUTABLE_PARAMS}." in value:
            v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
            query[key] = params[v]
        else:
            query[key] = value
    executable_body["filter"] = query

    col = get_collection(target_did, app_id, executable_body.get('collection'))
    data, err_message = query_delete_one(col, executable_body)
    if err_message:
        return None, err_message

    return data, None

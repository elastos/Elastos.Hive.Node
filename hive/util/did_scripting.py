from hive.util.constants import SCRIPTING_EXECUTABLE_CALLER_DID
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


def run_condition(did, app_id, condition_body, params):
    query = {}
    for key, value in condition_body.get('filter').items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[value] = {"$in": [did]}
        else:
            if not params.get(key):
                return False
            query[value] = params[key]
    condition_body["filter"] = query

    options = populate_options_count_documents(condition_body)

    col = get_collection(did, app_id, condition_body.get('collection'))
    data, err_message = query_count_documents(col, condition_body, options)
    if err_message:
        return False
    if data.get('count') == 0:
        return False

    return True


def run_executable_find(did, app_id, executable_body, params):
    query = {}
    for key, value in executable_body.get('filter').items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[value] = {"$in": [did]}
        else:
            query[value] = params[key]
    executable_body["filter"] = query

    options = populate_options_find_many(executable_body)

    col = get_collection(did, app_id, executable_body.get('collection'))
    data, err_message = query_find_many(col, executable_body, options)
    if err_message:
        return None, err_message

    return data, None


def run_executable_insert(did, app_id, executable_body, params):
    created = False
    query = {}
    for key, value in executable_body.get('document').items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[value] = did
        else:
            if value == "created":
                created = True
            query[value] = params[key]
    executable_body['document'] = query

    options = populate_options_insert_one(executable_body)

    col = get_collection(did, app_id, executable_body.get('collection'))
    data, err_message = query_insert_one(col, executable_body, options, created=created)
    if err_message:
        return None, err_message

    return data, None


def run_executable_update(did, app_id, executable_body, params):
    filter_query = {}
    for key, value in executable_body.get('filter').items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            filter_query[value] = did
        else:
            filter_query[value] = params[key]
    executable_body['filter'] = filter_query
    update_set_query = {}
    for key, value in executable_body.get('update').get("'$set'").items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            update_set_query[value] = did
        else:
            update_set_query[value] = params[key]
    executable_body['update'].pop("'$set'", None)
    executable_body['update']['$set'] = update_set_query

    options = populate_options_update_one(executable_body)

    col = get_collection(did, app_id, executable_body.get('collection'))
    data, err_message = query_update_one(col, executable_body, options)
    if err_message:
        return None, err_message

    return data, None


def run_executable_delete(did, app_id, executable_body, params):
    query = {}
    for key, value in executable_body.get('filter').items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[value] = {"$in": [did]}
        else:
            query[value] = params[key]
    executable_body["filter"] = query

    col = get_collection(did, app_id, executable_body.get('collection'))
    data, err_message = query_delete_one(col, executable_body)
    if err_message:
        return None, err_message

    return data, None

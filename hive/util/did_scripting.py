from hive.util.constants import SCRIPTING_EXECUTABLE_CALLER_DID
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import populate_options_find_many, \
    query_insert_one, query_find_many, populate_options_insert_one, populate_options_count_documents, \
    query_count_documents


def check_json_param(content, content_type, args):
    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return f"parameter '{arg}' is null for '{content_type}'"
    return None


def run_condition(did, app_id, condition_body, params):
    options = populate_options_count_documents(condition_body)

    query = {}
    for key, value in condition_body.get('filter').items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[value] = {"$in": [did]}
        else:
            query[value] = params[key]
    condition_body["filter"] = query

    col = get_collection(did, app_id, condition_body.get('collection'))
    data, err_message = query_count_documents(col, condition_body, options)
    if err_message:
        return False
    if data.get('count') == 0:
        return False

    return True


def run_executable_find(did, app_id, executable_body, params):
    options = populate_options_find_many(executable_body)

    query = {}
    for key, value in executable_body.get('filter').items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[value] = {"$in": [did]}
        else:
            query[value] = params[key]
    executable_body["filter"] = query

    col = get_collection(did, app_id, executable_body.get('collection'))
    data, err_message = query_find_many(col, executable_body, options)
    if err_message:
        return None, err_message

    return data, None


def run_executable_insert(did, app_id, executable_body, params):
    options = populate_options_insert_one(executable_body)

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

    col = get_collection(did, app_id, executable_body.get('collection'))
    data, err_message = query_insert_one(col, executable_body, options, created=created)
    if err_message:
        return None, err_message

    return data, None


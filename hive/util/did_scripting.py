from hive.util.constants import SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_EXECUTABLE_PARAMS, \
    SCRIPTING_EXECUTABLE_CALLER_APP_DID, VAULT_ACCESS_R, VAULT_ACCESS_WR, VAULT_STORAGE_FILE, VAULT_STORAGE_DB, \
    SCRIPTING_SCRIPT_TEMP_TX_COLLECTION
from hive.util.did_file_info import query_download, query_properties, query_hash, query_upload_get_filepath
from hive.util.did_mongo_db_resource import populate_options_find_many, \
    query_insert_one, query_find_many, populate_options_insert_one, populate_options_count_documents, \
    query_count_documents, populate_options_update_one, query_update_one, query_delete_one, get_collection, \
    get_mongo_database_size
from hive.util.payment.vault_service_manage import can_access_vault, inc_vault_file_use_storage_byte, \
    update_vault_db_use_storage_byte


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


def populate_params_find_count_delete(did, app_did, query, params, condition=False):
    for key, value in query.items():
        if isinstance(value, dict):
            populate_params_find_count_delete(did, app_did, value, params)
        elif isinstance(value, str):
            if value == SCRIPTING_EXECUTABLE_CALLER_DID:
                query[key] = {"$in": [did]}
            elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
                query[key] = {"$in": [app_did]}
            elif value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
                v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
                if not (params and params.get(v, None)):
                    if condition:
                        return False
                    else:
                        return None, "Exception: Parameter is not set"
                query[key] = params[v]
            else:
                query[key] = value
        else:
            query[key] = value


def run_condition(did, app_did, target_did, target_app_did, condition_body, params):
    condition_body_filter = condition_body.get('filter', {})
    populate_params_find_count_delete(did, app_did, condition_body_filter, params, condition=True)

    options = populate_options_count_documents(condition_body)

    col = get_collection(target_did, target_app_did, condition_body.get('collection'))
    data, err_message = query_count_documents(col, condition_body, options)
    if err_message:
        return False
    if data.get('count') == 0:
        return False

    return True


def run_executable_find(did, app_did, target_did, target_app_did, executable_body, params):
    if not can_access_vault(target_did, VAULT_ACCESS_R):
        return None, "vault can not be accessed"

    executable_body_filter = executable_body.get('filter', {})
    populate_params_find_count_delete(did, app_did, executable_body_filter, params)

    options = populate_options_find_many(executable_body)

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_find_many(col, executable_body, options)
    if err_message:
        return None, err_message

    return data, None


def populate_params_insert_update(did, app_did, query, params):
    for key, value in query.items():
        if isinstance(value, dict):
            populate_params_insert_update(did, app_did, value, params)
        elif isinstance(value, str):
            if value == SCRIPTING_EXECUTABLE_CALLER_DID:
                query[key] = did
            elif value == SCRIPTING_EXECUTABLE_CALLER_APP_DID:
                query[key] = app_did
            elif value.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
                v = value.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
                if not (params and params.get(v, None)):
                    return None, "Exception: Parameter is not set"
                query[key] = params[v]
            else:
                query[key] = value
        else:
            query[key] = value


def run_executable_insert(did, app_did, target_did, target_app_did, executable_body, params):
    if not can_access_vault(target_did, VAULT_ACCESS_WR):
        return None, "vault can not be accessed"

    executable_body_document = executable_body.get('document', {})
    populate_params_insert_update(did, app_did, executable_body_document, params)
    created = "created" in executable_body_document.keys()

    options = populate_options_insert_one(executable_body)

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_insert_one(col, executable_body, options, created=created)
    if err_message:
        return None, err_message
    db_size = get_mongo_database_size(target_did, target_app_did)
    update_vault_db_use_storage_byte(did, db_size)

    return data, None


def run_executable_update(did, app_did, target_did, target_app_did, executable_body, params):
    if not can_access_vault(target_did, VAULT_ACCESS_WR):
        return None, "vault can not be accessed"

    executable_body_filter = executable_body.get('filter', {})
    populate_params_insert_update(did, app_did, executable_body_filter, params)

    executable_body_update = executable_body.get('update').get('$set')
    populate_params_insert_update(did, app_did, executable_body_update, params)

    options = populate_options_update_one(executable_body)

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_update_one(col, executable_body, options)
    if err_message:
        return None, err_message
    db_size = get_mongo_database_size(target_did, target_app_did)
    update_vault_db_use_storage_byte(did, db_size)

    return data, None


def run_executable_delete(did, app_did, target_did, target_app_did, executable_body, params):
    if not can_access_vault(target_did, VAULT_ACCESS_R):
        return None, "vault can not be accessed"

    executable_body_filter = executable_body.get('filter', {})
    populate_params_find_count_delete(did, app_did, executable_body_filter, params)

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_delete_one(col, executable_body)
    if err_message:
        return None, err_message
    db_size = get_mongo_database_size(target_did, target_app_did)
    update_vault_db_use_storage_byte(did, db_size)

    return data, None


def run_executable_file_upload(did, app_did, target_did, target_app_did, executable_body, params):
    if not can_access_vault(target_did, VAULT_ACCESS_WR):
        return None, "vault can not be accessed"
    executable_body_path = executable_body.get("path", "")
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        if not (params and params.get(v, None)):
            return None, "Exception: Parameter is not set"
        executable_body_path = params[v]

    if not executable_body_path:
        return None, f"Path cannot be empty"

    full_path_name, err = query_upload_get_filepath(target_did, target_app_did, executable_body_path)
    if err:
        return None, f"Exception: Could not upload file. Status={err['status_code']} Error='{err['description']}'"

    content = {
        "document": {
            "target_did": target_did,
            "target_app_did": target_app_did,
            "file_name": executable_body_path
        }
    }
    col = get_collection(did, app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION)
    if not col:
        return None, f"collection {SCRIPTING_SCRIPT_TEMP_TX_COLLECTION} does not exist"
    data, err_message = query_insert_one(col, content, {})
    if err_message:
        return None, f"Could not insert data into the database: Err: {err_message}"
    db_size = get_mongo_database_size(did, app_did)
    update_vault_db_use_storage_byte(did, db_size)

    transaction_id = data.get("inserted_id", None)
    if not transaction_id:
        return None, f"Could not retrieve the transaction ID. Please try again"
    data = {
        "transaction_id": transaction_id
    }

    return data, None


def run_executable_file_download(did, app_did, target_did, target_app_did, executable_body, params):
    if not can_access_vault(target_did, VAULT_ACCESS_R):
        return None, "vault can not be accessed"
    executable_body_path = executable_body.get("path", "")
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        if not (params and params.get(v, None)):
            return None, "Exception: Parameter is not set"
        executable_body_path = params[v]

    if not executable_body_path:
        return None, f"Path cannot be empty"

    content = {
        "document": {
            "target_did": target_did,
            "target_app_did": target_app_did,
            "file_name": executable_body_path
        }
    }
    col = get_collection(did, app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION)
    if not col:
        return None, f"collection {SCRIPTING_SCRIPT_TEMP_TX_COLLECTION} does not exist"
    data, err_message = query_insert_one(col, content, {})
    if err_message:
        return None, f"Could not insert data into the database: Err: {err_message}"
    db_size = get_mongo_database_size(did, app_did)
    update_vault_db_use_storage_byte(did, db_size)

    transaction_id = data.get("inserted_id", None)
    if not transaction_id:
        return None, f"Could not retrieve the transaction ID. Please try again"
    data = {
        "transaction_id": transaction_id
    }

    return data, None


def run_executable_file_properties(did, app_did, target_did, target_app_did, executable_body, params):
    if not can_access_vault(target_did, VAULT_ACCESS_R):
        return None, "vault can not be accessed"
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
    if not can_access_vault(target_did, VAULT_ACCESS_R):
        return None, "vault can not be accessed"
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

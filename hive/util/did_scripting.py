import jwt

from flask import request

from hive.main.hive_file import HiveFile
from hive.settings import hive_setting
from hive.util.constants import SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_EXECUTABLE_PARAMS, \
    SCRIPTING_EXECUTABLE_CALLER_APP_DID, VAULT_ACCESS_R, VAULT_ACCESS_WR, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION
from hive.util.did_file_info import query_upload_get_filepath
from hive.util.did_mongo_db_resource import populate_options_find_many, \
    query_insert_one, query_find_many, populate_options_insert_one, populate_options_count_documents, \
    query_count_documents, populate_options_update_one, query_update_one, query_delete_one, get_collection, \
    get_mongo_database_size
from hive.util.error_code import SUCCESS
from hive.util.payment.vault_service_manage import can_access_vault, update_vault_db_use_storage_byte
from src.modules.files.files_service import IpfsFiles
from src.utils.consts import COL_IPFS_FILES_SHA256
from hive.util.v2_adapter import v2_wrapper


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
        return None, 'parameter is not application/json'
    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return f'parameter {arg} is null'
    return content, None


def check_json_param(content, content_type, args):
    if content is None:
        return f"parameter is null for '{content_type}"
    for arg in args:
        data = content.get(arg, None)
        if data is None:
            return f"parameter '{arg}' is null for '{content_type}'"
    return None


def populate_with_params_values(did, app_did, options, params):
    """
    replace $params to the real value.
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


def run_condition(did, app_did, target_did, target_app_did, condition_body, params):
    condition_body_filter = condition_body.get('filter', {})
    err_message = populate_with_params_values(did, app_did, condition_body_filter, params)
    if err_message:
        return False

    options = populate_options_count_documents(condition_body)
    err_message = populate_with_params_values(did, app_did, options, params)
    if err_message:
        return False

    col = get_collection(target_did, target_app_did, condition_body.get('collection'))
    data, err_message = query_count_documents(col, condition_body, options)
    if err_message:
        return False
    if data.get('count') == 0:
        return False

    return True


def run_executable_find(did, app_did, target_did, target_app_did, executable_body, params):
    r, msg = can_access_vault(target_did, VAULT_ACCESS_R)
    if r != SUCCESS:
        return None, msg

    executable_body_filter = executable_body.get('filter', {})
    err_message = populate_with_params_values(did, app_did, executable_body_filter, params)
    if err_message:
        return None, err_message

    options = populate_options_find_many(executable_body)
    err_message = populate_with_params_values(did, app_did, options, params)
    if err_message:
        return None, err_message

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    if col is None:
        return None, f'Can not find the collection {executable_body.get("collection")}'
    data, err_message = query_find_many(col, executable_body, options)
    if err_message:
        return None, err_message

    return data, None


def run_executable_insert(did, app_did, target_did, target_app_did, executable_body, params):
    r, msg = can_access_vault(target_did, VAULT_ACCESS_WR)
    if r != SUCCESS:
        return None, msg

    executable_body_document = executable_body.get('document', {})
    err_message = populate_with_params_values(did, app_did, executable_body_document, params)
    if err_message:
        return None, err_message
    created = "created" in executable_body_document.keys()

    options = populate_options_insert_one(executable_body)
    err_message = populate_with_params_values(did, app_did, options, params)
    if err_message:
        return None, err_message

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_insert_one(col, executable_body, options, created=created)
    if err_message:
        return None, err_message
    db_size = get_mongo_database_size(target_did, target_app_did)
    update_vault_db_use_storage_byte(did, db_size)

    return data, None


def run_executable_update(did, app_did, target_did, target_app_did, executable_body, params):
    r, msg = can_access_vault(target_did, VAULT_ACCESS_WR)
    if r != SUCCESS:
        return None, msg

    executable_body_filter = executable_body.get('filter', {})
    err_message = populate_with_params_values(did, app_did, executable_body_filter, params)
    if err_message:
        return None, err_message

    executable_body_update = executable_body.get('update').get('$set')
    err_message = populate_with_params_values(did, app_did, executable_body_update, params)
    if err_message:
        return None, err_message

    options = populate_options_update_one(executable_body)
    err_message = populate_with_params_values(did, app_did, options, params)
    if err_message:
        return None, err_message

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_update_one(col, executable_body, options)
    if err_message:
        return None, err_message
    db_size = get_mongo_database_size(target_did, target_app_did)
    update_vault_db_use_storage_byte(did, db_size)

    return data, None


def run_executable_delete(did, app_did, target_did, target_app_did, executable_body, params):
    r, msg = can_access_vault(target_did, VAULT_ACCESS_R)
    if r != SUCCESS:
        return None, msg

    executable_body_filter = executable_body.get('filter', {})
    err_message = populate_with_params_values(did, app_did, executable_body_filter, params)
    if err_message:
        return None, err_message

    col = get_collection(target_did, target_app_did, executable_body.get('collection'))
    data, err_message = query_delete_one(col, executable_body)
    if err_message:
        return None, err_message
    db_size = get_mongo_database_size(target_did, target_app_did)
    update_vault_db_use_storage_byte(did, db_size)

    return data, None


def run_executable_file_upload(did, app_did, target_did, target_app_did, executable_body, params):
    r, msg = can_access_vault(target_did, VAULT_ACCESS_WR)
    if r != SUCCESS:
        return None, msg

    executable_body_path = executable_body.get("path", "")
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        try:
            v = params[v]
        except Exception as e:
            return None, f"Exception: {str(e)}"
        executable_body_path = v

    if not executable_body_path:
        return None, f"Path cannot be empty"

    full_path_name, err = query_upload_get_filepath(target_did, target_app_did, executable_body_path)
    if err:
        return None, f"Exception: Could not upload file. Status={err['status_code']} Error='{err['description']}'"

    content = {
        "document": {
            "file_name": executable_body_path,
            "fileapi_type": "upload"
        }
    }
    col = get_collection(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION)
    if col is None:
        return None, f"collection {SCRIPTING_SCRIPT_TEMP_TX_COLLECTION} does not exist"
    data, err_message = query_insert_one(col, content, {})
    if err_message:
        return None, f"Could not insert data into the database: Err: {err_message}"
    db_size = get_mongo_database_size(target_did, target_app_did)
    update_vault_db_use_storage_byte(target_did, db_size)

    row_id = data.get("inserted_id", None)
    if not row_id:
        return None, f"Could not retrieve the transaction ID. Please try again"

    data = {
        "transaction_id": jwt.encode({
            "row_id": row_id,
            "target_did": target_did,
            "target_app_did": target_app_did
        }, hive_setting.PASSWORD, algorithm='HS256')
    }

    return data, None


def run_executable_file_download(did, app_did, target_did, target_app_did, executable_body, params):
    r, msg = can_access_vault(target_did, VAULT_ACCESS_R)
    if r != SUCCESS:
        return None, msg
    executable_body_path = executable_body.get("path", "")
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        try:
            v = params[v]
        except Exception as e:
            return None, f"Exception: {str(e)}"
        executable_body_path = v

    if not executable_body_path:
        return None, f"Path cannot be empty"

    content = {
        "document": {
            "file_name": executable_body_path,
            "fileapi_type": "download"
        }
    }
    col = get_collection(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION)
    if col is None:
        return None, f"collection {SCRIPTING_SCRIPT_TEMP_TX_COLLECTION} does not exist"
    data, err_message = query_insert_one(col, content, {})
    if err_message:
        return None, f"Could not insert data into the database: Err: {err_message}"
    db_size = get_mongo_database_size(target_did, target_app_did)
    update_vault_db_use_storage_byte(target_did, db_size)

    row_id = data.get("inserted_id", None)
    if not row_id:
        return None, f"Could not retrieve the transaction ID. Please try again"

    data = {
        "transaction_id": jwt.encode({
            "row_id": row_id,
            "target_did": target_did,
            "target_app_did": target_app_did
        }, hive_setting.PASSWORD, algorithm='HS256')
    }

    return data, None


def run_executable_file_properties(did, app_did, target_did, target_app_did, executable_body, params):
    r, msg = can_access_vault(target_did, VAULT_ACCESS_R)
    if r != SUCCESS:
        return None, msg

    executable_body_path = executable_body.get("path", "")
    name = ""
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        try:
            v = params[v]
        except Exception as e:
            return None, f"Exception: {str(e)}"
        name = v

    metadata, resp_err = v2_wrapper(IpfsFiles().get_file_metadata)(target_did, target_app_did, name)
    if resp_err:
        return None, f'Exception: Could not get the properties of the file. Status={resp_err[1]} Error={resp_err[0]}'
    data = HiveFile.get_info_by_metadata(metadata)

    return data, None


def run_executable_file_hash(did, app_did, target_did, target_app_did, executable_body, params):
    r, msg = can_access_vault(target_did, VAULT_ACCESS_R)
    if r != SUCCESS:
        return None, msg

    executable_body_path = executable_body.get("path", "")
    name = ""
    if executable_body_path.startswith(f"{SCRIPTING_EXECUTABLE_PARAMS}."):
        v = executable_body_path.replace(f"{SCRIPTING_EXECUTABLE_PARAMS}.", "")
        try:
            v = params[v]
        except Exception as e:
            return None, f"Exception: {str(e)}"
        name = v

    metadata, resp_err = v2_wrapper(IpfsFiles().get_file_metadata)(target_did, target_app_did, name)
    if resp_err:
        return None, f'Exception: Could not get the hash of the file. Status={resp_err[1]} Error={resp_err[0]}'
    data = {"SHA256": metadata[COL_IPFS_FILES_SHA256]}

    return data, None

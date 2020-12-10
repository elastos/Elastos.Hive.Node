import copy
import os
import logging

from bson import ObjectId
from flask import request
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

from hive.main.interceptor import post_json_param_pre_proc, pre_proc
from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.constants import SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_EXECUTABLE_TYPE_FIND, SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR, \
    SCRIPTING_EXECUTABLE_TYPE_INSERT, SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS, SCRIPTING_EXECUTABLE_TYPE_AGGREGATED, \
    SCRIPTING_EXECUTABLE_TYPE_UPDATE, SCRIPTING_EXECUTABLE_TYPE_DELETE, SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES, SCRIPTING_EXECUTABLE_TYPE_FILE_HASH, SCRIPTING_EXECUTABLE_DOWNLOADABLE, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD, VAULT_ACCESS_WR, VAULT_ACCESS_R, VAULT_STORAGE_DB, \
    SCRIPTING_SCRIPT_TEMP_TX_COLLECTION
from hive.util.did_file_info import filter_path_root, query_upload_get_filepath, query_download
from hive.util.did_mongo_db_resource import gene_mongo_db_name, query_update_one, populate_options_update_one, \
    get_collection, get_mongo_database_size, query_delete_one
from hive.util.did_scripting import check_json_param, run_executable_find, run_condition, run_executable_insert, \
    run_executable_update, run_executable_delete, run_executable_file_download, run_executable_file_properties, \
    run_executable_file_hash, run_executable_file_upload, massage_keys_with_dollar_signs, \
    unmassage_keys_with_dollar_signs
from hive.util.payment.vault_service_manage import can_access_vault, update_vault_db_use_storage_byte, \
    inc_vault_file_use_storage_byte
from hive.util.server_response import ServerResponse


class HiveScripting:
    def __init__(self, app=None):
        self.app = app
        self.response = ServerResponse("HiveScripting")

    def init_app(self, app):
        self.app = app

    def __upsert_script_to_db(self, did, app_id, content):
        connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
        db_name = gene_mongo_db_name(did, app_id)
        db = connection[db_name]

        try:
            db.create_collection(SCRIPTING_SCRIPT_COLLECTION)
        except CollectionInvalid:
            pass
        except Exception as e:
            return None, f"Could not create collection. Please try again later. Exception : {str(e)}"
        try:
            db.create_collection(SCRIPTING_SCRIPT_TEMP_TX_COLLECTION)
        except CollectionInvalid:
            pass
        except Exception as e:
            return None, f"Could not create collection. Please try again later. Exception : {str(e)}"

        col = get_collection(did, app_id, SCRIPTING_SCRIPT_COLLECTION)

        new_content = {
            "filter": {
                "name": content.get("name")
            },
            "update": {
                "$set": {k: v for k, v in content.items() if k != 'name'}
            },
            "options": {
                "upsert": True,
                "bypass_document_validation": False
            }
        }

        options = populate_options_update_one(new_content)

        data, err_message = query_update_one(col, new_content, options)
        if err_message:
            return None, err_message
        db_size = get_mongo_database_size(did, app_id)
        update_vault_db_use_storage_byte(did, db_size)

        return data, None

    def __condition_validation(self, condition):
        condition_type = condition.get('type')
        condition_body = condition.get('body')
        if condition_type in [SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR]:
            if not isinstance(condition_body, list):
                return False
            if len(condition_body) == 1:
                return self.__condition_validation(condition_body[0])
            else:
                new_condition = {
                    "type": condition.get('type'),
                    "body": condition_body[1:]
                }
                return self.__condition_validation(condition_body[0]) and \
                       self.__condition_validation(new_condition)
        elif condition_type == SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS:
            err_message = check_json_param(condition, "condition", args=["type", "name", "body"])
            if err_message:
                return False
            err_message = check_json_param(condition_body, "condition.body", args=["collection", "filter"])
            if err_message:
                return False
        else:
            return False
        return True

    def __executable_validation(self, executable):
        err_message = check_json_param(executable, "executable", args=["type", "body"])
        if err_message:
            return err_message
        executable_type = executable.get('type')
        executable_body = executable.get('body')
        if executable_type == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            if not isinstance(executable_body, list):
                return f"Invalid parameters passed for executable type '{executable_type}'"
            if len(executable_body) == 1:
                return self.__executable_validation(executable_body[0])
            else:
                new_executable = {
                    "type": executable_type,
                    "body": executable_body[1:]
                }
                return self.__executable_validation(new_executable)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FIND:
            return check_json_param(executable_body, f"{executable.get('name')}", args=["collection"])
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            return check_json_param(executable_body, f"{executable.get('name')}", args=["collection", "document"])
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_DELETE:
            return check_json_param(executable_body, f"{executable.get('name')}", args=["collection", "filter"])
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_UPDATE:
            return check_json_param(executable_body, f"{executable.get('name')}",
                                    args=["collection", "filter", "update"])
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD:
            executable_name = executable.get('name')
            # We need to make sure that the script's name is not "_download" as it's a reserved field
            if executable_name == SCRIPTING_EXECUTABLE_DOWNLOADABLE:
                return f"invalid executable name '{executable_name}'. This name is reserved. Please use a different name"
            return check_json_param(executable_body, f"{executable_name}", args=["path"])
        elif executable_type in [SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD, SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES,
                                 SCRIPTING_EXECUTABLE_TYPE_FILE_HASH]:
            return check_json_param(executable_body, f"{executable.get('name')}", args=["path"])
        else:
            return f"invalid executable type '{executable_type}'"

    def __condition_execution(self, did, app_did, target_did, target_app_did, condition, params):
        condition_type = condition.get('type')
        condition_body = condition.get('body')
        if condition_type in [SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR]:
            if len(condition_body) == 1:
                return self.__condition_execution(did, app_did, target_did, target_app_did, condition_body[0], params)
            new_condition = {
                "type": condition_type,
                "body": condition_body[1:]
            }
            if condition_type == SCRIPTING_CONDITION_TYPE_AND:
                return self.__condition_execution(did, app_did, target_did, target_app_did, condition_body[0],
                                                  params) and \
                       self.__condition_execution(did, app_did, target_did, target_app_did, new_condition, params)
            elif condition_type == SCRIPTING_CONDITION_TYPE_OR:
                return self.__condition_execution(did, app_did, target_did, target_app_did, condition_body[0],
                                                  params) or \
                       self.__condition_execution(did, app_did, target_did, target_app_did, new_condition, params)
        else:
            return run_condition(did, app_did, target_did, target_app_did, condition_body, params)

    def __executable_execution(self, did, app_did, target_did, target_app_did, executable, params, output={},
                               output_key=None, capture_output=False):
        executable_type = executable.get('type')
        executable_body = executable.get('body')
        if not output_key:
            output_key = executable.get('name')

        if not capture_output:
            capture_output = executable.get('output', False)

        if executable_type == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            err_message = None
            for i, e in enumerate(executable_body):
                self.__executable_execution(did, app_did, target_did, target_app_did, e, params, output,
                                            e.get('name', f"output{i}"),
                                            e.get('output', False))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FIND:
            data, err_message = run_executable_find(did, app_did, target_did, target_app_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            data, err_message = run_executable_insert(did, app_did, target_did, target_app_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_UPDATE:
            data, err_message = run_executable_update(did, app_did, target_did, target_app_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_DELETE:
            data, err_message = run_executable_delete(did, app_did, target_did, target_app_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD:
            data, err_message = run_executable_file_upload(did, app_did, target_did, target_app_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD:
            data, err_message = run_executable_file_download(did, app_did, target_did, target_app_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES:
            data, err_message = run_executable_file_properties(did, app_did, target_did, target_app_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_HASH:
            data, err_message = run_executable_file_hash(did, app_did, target_did, target_app_did, executable_body, params)
        else:
            data, err_message = None, f"invalid executable type '{executable_type}'"

        if err_message:
            output[output_key] = err_message
        else:
            if capture_output:
                output[output_key] = data
        return output

    def __count_nested_condition(self, condition):
        content = copy.deepcopy(condition)
        count = {}
        for index, body in enumerate(content.get('body')):
            content_body = content.get('body')
            while isinstance(content_body, list):
                if index in count.keys():
                    count[index] += 1
                else:
                    count[index] = 1
                content_body = content_body[index].get('body')
        return count

    def set_script(self):
        # Request Validation
        did, app_id, content, err = post_json_param_pre_proc(self.response, "name", "executable",
                                                             access_vault=VAULT_ACCESS_WR)
        if err:
            return err

        logging.debug(f"Registering a script named '{content.get('name')}' with params: DID: '{did}', App DID: '{app_id}'")

        # Data Validation
        executable = content.get('executable')
        massage_keys_with_dollar_signs(executable)
        err_message = self.__executable_validation(executable)
        if err_message:
            logging.debug(f"Error while validating executables: {err_message}")
            return self.response.response_err(400, err_message)

        # Condition Validation
        condition = content.get('condition', None)
        if condition:
            err_message = check_json_param(condition, "condition", args=["type", "name", "body"])
            if err_message:
                logging.debug(f"Error while validating conditions: {err_message}")
                return self.response.response_err(400, err_message)
            nested_count = self.__count_nested_condition(condition)
            for count in nested_count.values():
                if count >= 5:
                    err_message = "conditions cannot be nested more than 5 times"
                    logging.debug(f"Error while validating conditions: {err_message}")
                    return self.response.response_err(400, err_message)
            is_valid = self.__condition_validation(condition)
            if not is_valid:
                err_message = "some of the parameters are not set for 'condition'"
                logging.debug(f"Error while validating conditions: {err_message}")
                return self.response.response_err(400, err_message)

        # Create collection "scripts" if it doesn't exist and
        # create/update script in the database
        data, err_message = self.__upsert_script_to_db(did, app_id, content)
        if err_message:
            return self.response.response_err(500, err_message)
        return self.response.response_ok(data)

    def run_script(self):
        # Request the Caller DID and Caller App Validation
        caller_did, caller_app_did, content, err = post_json_param_pre_proc(self.response, "name")
        if err:
            return err

        target_did, target_app_did = caller_did, caller_app_did
        # Request the Target DID and Target App Validation if present
        context = content.get('context', {})
        if context:
            target_did = context.get('target_did', caller_did)
            target_app_did = context.get('target_app_did', caller_app_did)

        if not can_access_vault(target_did, VAULT_ACCESS_R):
            logging.debug(f"Error while executing script named '{content.get('name')}': vault can not be accessed")
            return self.response.response_err(402, "vault can not be accessed")

        if not target_app_did:
            logging.debug(f"Error while executing script named '{content.get('name')}': target_app_did not set")
            return self.response.response_err(402, "target_app_did not set")

        logging.debug(f"Executing a script named '{content.get('name')}' with params: "
                      f"Caller DID: '{caller_did}', Caller App DID: '{caller_app_did}', "
                      f"Target DID: '{target_did}', Target App DID: '{target_app_did}'")

        # Find the script in the database
        col = get_collection(target_did, target_app_did, SCRIPTING_SCRIPT_COLLECTION)
        content_filter = {
            "name": content.get('name')
        }

        err_message = f"could not find script '{content['name']}' in the database. Please register the script " \
                      f"first with set_script' API endpoint"
        try:
            script = col.find_one(content_filter)
        except Exception as e:
            err_message = f"{err_message}. Exception: {str(e)}"
            logging.debug(f"Error while executing script named '{content.get('name')}': {err_message}")
            return self.response.response_err(404, err_message)

        if not script:
            logging.debug(f"Error while executing script named '{content.get('name')}': {err_message}")
            return self.response.response_err(404, err_message)

        params = content.get('params', None)
        condition = script.get('condition', None)
        if condition:
            # Currently, there's only one kind of condition("count" db query)
            if not can_access_vault(target_did, VAULT_ACCESS_R):
                logging.debug(f"Error while executing script named '{content.get('name')}': vault can not be accessed")
                return self.response.response_err(401, "vault can not be accessed")
            passed = self.__condition_execution(caller_did, caller_app_did, target_did, target_app_did, condition,
                                                params)
            if not passed:
                err_message = f"the conditions were not met to execute this script"
                logging.debug(f"Error while executing script named '{content.get('name')}': {err_message}")
                return self.response.response_err(403, err_message)

        executable = script.get("executable")
        unmassage_keys_with_dollar_signs(executable)
        output = {}
        data = self.__executable_execution(caller_did, caller_app_did, target_did, target_app_did, executable, params,
                                           output=output, output_key=executable.get('name', "output0"))

        return self.response.response_ok(data)

    def run_script_upload(self, transaction_id):
        caller_did, caller_app_did, response = pre_proc(self.response, access_vault=VAULT_ACCESS_WR)
        if response is not None:
            return response

        # Find the temporary tx in the database
        col = get_collection(caller_did, caller_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION)
        content_filter = {
            "_id": ObjectId(transaction_id)
        }

        err_message = f"could not find the transaction ID '{transaction_id}' in the database"
        try:
            script_temp_tx = col.find_one(content_filter)
        except Exception as e:
            err_message = f"{err_message}. Exception: {str(e)}"
            logging.debug(f"Error while executing file upload via scripting: {err_message}")
            return self.response.response_err(404, err_message)

        if not script_temp_tx:
            logging.debug(f"Error while executing file upload via scripting: {err_message}")
            return self.response.response_err(404, err_message)

        target_did = script_temp_tx.get('target_did', None)
        target_app_did = script_temp_tx.get('target_app_did', None)
        file_name = script_temp_tx.get('file_name', None)

        file_name = filter_path_root(file_name)

        full_path_name, err = query_upload_get_filepath(target_did, target_app_did, file_name)
        if err:
            logging.debug(f"Error while executing file upload via scripting: {err['description']}")
            return self.response.response_err(err["status_code"], err["description"])
        try:
            with open(full_path_name, "bw") as f:
                chunk_size = 4096
                while True:
                    chunk = request.stream.read(chunk_size)
                    if len(chunk) == 0:
                        break
                    f.write(chunk)
            file_size = os.path.getsize(full_path_name.as_posix())
            inc_vault_file_use_storage_byte(target_did, file_size)
        except Exception as e:
            logging.debug(f"Error while executing file upload via scripting: {str(e)}")
            return self.response.response_err(500, f"Exception: {str(e)}")

        content_filter = {
            "filter": {
                "_id": ObjectId(transaction_id)
            }
        }
        _, err_message = query_delete_one(col, content_filter)
        if err_message:
            logging.debug(f"Error while executing file upload via scripting: {err_message}")
            return self.response.response_err(500, err_message)
        db_size = get_mongo_database_size(caller_did, caller_app_did)
        update_vault_db_use_storage_byte(caller_did, db_size)

        return self.response.response_ok()

    def run_script_download(self, transaction_id):
        caller_did, caller_app_did, response = pre_proc(self.response, access_vault=VAULT_ACCESS_R)
        if response is not None:
            return response

        # Find the temporary tx in the database
        col = get_collection(caller_did, caller_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION)
        content_filter = {
            "_id": ObjectId(transaction_id)
        }

        err_message = f"could not find the transaction ID '{transaction_id}' in the database"
        try:
            script_temp_tx = col.find_one(content_filter)
        except Exception as e:
            err_message = f"{err_message}. Exception: {str(e)}"
            logging.debug(f"Error while executing file download via scripting: {err_message}")
            return self.response.response_err(404, err_message)

        if not script_temp_tx:
            logging.debug(f"Error while executing file download via scripting: {err_message}")
            return self.response.response_err(404, err_message)

        target_did = script_temp_tx.get('target_did', None)
        target_app_did = script_temp_tx.get('target_app_did', None)
        file_name = script_temp_tx.get('file_name', None)

        data, status_code = query_download(target_did, target_app_did, file_name)
        if status_code != 200:
            logging.debug(f"Error while executing file download via scripting: Could not download file")
            return self.response.response_err(status_code, "Could not download file")

        content_filter = {
            "filter": {
                "_id": ObjectId(transaction_id)
            }
        }
        _, err_message = query_delete_one(col, content_filter)
        if err_message:
            logging.debug(f"Error while executing file download via scripting: {err_message}")
            return self.response.response_err(500, err_message)
        db_size = get_mongo_database_size(caller_did, caller_app_did)
        update_vault_db_use_storage_byte(caller_did, db_size)

        return data

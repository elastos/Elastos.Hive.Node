import copy
import os
import logging

import jwt
from bson import ObjectId
from flask import request
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

from hive.main.interceptor import post_json_param_pre_proc
from hive.settings import hive_setting
from hive.util.auth import did_auth
from hive.util.constants import SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_EXECUTABLE_TYPE_FIND, SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR, \
    SCRIPTING_EXECUTABLE_TYPE_INSERT, SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS, SCRIPTING_EXECUTABLE_TYPE_AGGREGATED, \
    SCRIPTING_EXECUTABLE_TYPE_UPDATE, SCRIPTING_EXECUTABLE_TYPE_DELETE, SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES, SCRIPTING_EXECUTABLE_TYPE_FILE_HASH, SCRIPTING_EXECUTABLE_DOWNLOADABLE, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD, VAULT_ACCESS_WR, VAULT_ACCESS_R, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION
from hive.util.did_file_info import filter_path_root, query_upload_get_filepath, query_download
from hive.util.did_mongo_db_resource import gene_mongo_db_name, \
    get_collection, get_mongo_database_size, query_delete_one, convert_oid
from hive.util.did_scripting import check_json_param, run_executable_find, run_condition, run_executable_insert, \
    run_executable_update, run_executable_delete, run_executable_file_download, run_executable_file_properties, \
    run_executable_file_hash, run_executable_file_upload, massage_keys_with_dollar_signs, \
    unmassage_keys_with_dollar_signs, get_script_content
from hive.util.error_code import INTERNAL_SERVER_ERROR, BAD_REQUEST, UNAUTHORIZED, FORBIDDEN, NOT_FOUND, SUCCESS
from hive.util.payment.vault_service_manage import can_access_vault, update_vault_db_use_storage_byte
from hive.util.server_response import ServerResponse
from src.modules.ipfs.ipfs_files import IpfsFiles
from hive.util.v2_adapter import v2_wrapper


class HiveScripting:
    def __init__(self, app=None):
        self.app = app
        self.response = ServerResponse("HiveScripting")
        self.ipfs_files = IpfsFiles()

    def init_app(self, app):
        self.app = app

    def __upsert_script_to_db(self, did, app_id, content):
        if hive_setting.MONGO_URI:
            uri = hive_setting.MONGO_URI
            connection = MongoClient(uri)
        else:
            connection = MongoClient(hive_setting.MONGODB_URI)

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
        query = {
            "name": content.get("name")
        }
        options = {
            "upsert": True,
            "bypass_document_validation": False
        }
        try:
            ret = col.replace_one(query, convert_oid(content), **options)
            data = {
                "acknowledged": ret.acknowledged,
                "matched_count": ret.matched_count,
                "modified_count": ret.modified_count,
                "upserted_id": str(ret.upserted_id),
            }
        except Exception as e:
            return None, f"Exception: method: '__upsert_script_to_db', Err: {str(e)}"
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

        data = None
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
        # @fred: The error of executable will be taken as success.
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

        # Anonymity Options
        content['allowAnonymousUser'] = content.get('allowAnonymousUser', False)
        content['allowAnonymousApp'] = content.get('allowAnonymousApp', False)

        logging.debug(f"Registering a script named '{content.get('name')}' with params: DID: '{did}', App DID: '{app_id}', "
                      f"Anonymous User Access: {content['allowAnonymousUser']}, Anonymous App Access: {content['allowAnonymousApp']}")

        # Anonymity Validation
        if (content['allowAnonymousUser'] is True) and (content['allowAnonymousApp'] is False):
            err_message = "Error while validating anonymity options: Cannot set allowAnonymousUser to be True but " \
                          "allowAnonymousApp to be False as we cannot request an auth to prove an app identity without " \
                          "proving the user identity"
            logging.debug(err_message)
            return self.response.response_err(BAD_REQUEST, err_message)

        # Data Validation
        executable = content.get('executable')
        massage_keys_with_dollar_signs(executable)
        err_message = self.__executable_validation(executable)
        if err_message:
            logging.debug(f"Error while validating executables: {err_message}")
            return self.response.response_err(BAD_REQUEST, err_message)

        # Condition Validation
        condition = content.get('condition', None)
        if condition:
            err_message = check_json_param(condition, "condition", args=["type", "name", "body"])
            if err_message:
                logging.debug(f"Error while validating conditions: {err_message}")
                return self.response.response_err(BAD_REQUEST, err_message)
            nested_count = self.__count_nested_condition(condition)
            for count in nested_count.values():
                if count >= 5:
                    err_message = "conditions cannot be nested more than 5 times"
                    logging.debug(f"Error while validating conditions: {err_message}")
                    return self.response.response_err(BAD_REQUEST, err_message)
            is_valid = self.__condition_validation(condition)
            if not is_valid:
                err_message = "some of the parameters are not set for 'condition'"
                logging.debug(f"Error while validating conditions: {err_message}")
                return self.response.response_err(BAD_REQUEST, err_message)

        # Create collection "scripts" if it doesn't exist and
        # create/update script in the database
        data, err_message = self.__upsert_script_to_db(did, app_id, content)
        if err_message:
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)
        return self.response.response_ok(data)

    def __run_script(self, script_name, caller_did, caller_app_did, target_did, target_app_did, params):
        """
        :return: ok or error response
        """
        r, msg = can_access_vault(target_did, VAULT_ACCESS_R)
        if r != SUCCESS:
            logging.debug(f"Error while executing script named '{script_name}': vault can not be accessed")
            return self.response.response_err(r, msg)

        # Find the script in the database
        col = get_collection(target_did, target_app_did, SCRIPTING_SCRIPT_COLLECTION)
        content_filter = {
            "name": script_name
        }

        err_message = f"could not find script '{script_name}' in the database. Please register the script " \
                      f"first with set_script' API endpoint"
        try:
            script = col.find_one(content_filter)
        except Exception as e:
            err_message = f"{err_message}. Exception: {str(e)}"
            logging.debug(f"Error while executing script named '{script_name}': {err_message}")
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)

        if not script:
            logging.debug(f"Error while executing script named '{script_name}': {err_message}")
            return self.response.response_err(NOT_FOUND, err_message)

        # Validate anonymity options
        allow_anonymous_user = script.get('allowAnonymousUser', False)
        allow_anonymous_app = script.get('allowAnonymousApp', False)
        if (allow_anonymous_user is True) and (allow_anonymous_app is False):
            err_message = "Error while validating anonymity options: Cannot set allowAnonymousUser to be True but " \
                          "allowAnonymousApp to be False as we cannot request an auth to prove an app identity without " \
                          "proving the user identity"
            logging.debug(err_message)
            return self.response.response_err(BAD_REQUEST, err_message)
        if allow_anonymous_user is True:
            caller_did = None
        else:
            if not caller_did:
                logging.debug(f"Error while executing script named '{script_name}': Auth failed. caller_did "
                              f"not set")
                return self.response.response_err(UNAUTHORIZED, "Auth failed. caller_did not set")
        if allow_anonymous_app is True:
            caller_app_did = None
        else:
            if not caller_app_did:
                logging.debug(f"Error while executing script named '{script_name}': Auth failed. "
                              f"caller_app_did not set")
                return self.response.response_err(UNAUTHORIZED, "Auth failed. caller_app_did not set")

        logging.debug(f"Executing a script named '{script_name}' with params: "
                      f"Caller DID: '{caller_did}', Caller App DID: '{caller_app_did}', "
                      f"Target DID: '{target_did}', Target App DID: '{target_app_did}', "
                      f"Anonymous User Access: {allow_anonymous_user}, Anonymous App Access: {allow_anonymous_app}")

        condition = script.get('condition', None)
        if condition:
            # Currently, there's only one kind of condition("count" db query)
            r, msg = can_access_vault(target_did, VAULT_ACCESS_R)
            if r != SUCCESS:
                logging.debug(f"Error while executing script named '{script_name}': vault can not be accessed")
                return self.response.response_err(r, msg)
            passed = self.__condition_execution(caller_did, caller_app_did, target_did, target_app_did, condition,
                                                params)
            if not passed:
                err_message = f"the conditions were not met to execute this script"
                logging.debug(f"Error while executing script named '{script_name}': {err_message}")
                return self.response.response_err(FORBIDDEN, err_message)

        executable = script.get("executable")
        unmassage_keys_with_dollar_signs(executable)
        output = {}
        data = self.__executable_execution(caller_did, caller_app_did, target_did, target_app_did, executable, params,
                                           output=output, output_key=executable.get('name', "output0"))
        return self.response.response_ok(data)

    def run_script_url(self, target_did, target_app_did, script_name, params):
        # Get caller info
        caller_did, caller_app_did = did_auth()

        return self.__run_script(script_name, caller_did, caller_app_did, target_did, target_app_did, params)

    def run_script(self):
        # Request script content first
        content, err = get_script_content(self.response, "name")
        if err:
            msg = f'Failed to get the script content: {err}'
            logging.debug(msg)
            return self.response.response_err(BAD_REQUEST, msg)

        script_name = content.get('name')
        caller_did, caller_app_did = did_auth()
        target_did, target_app_did = caller_did, caller_app_did
        # Request the Target DID and Target App Validation if present
        context = content.get('context', {})
        if context:
            target_did = context.get('target_did', None)
            target_app_did = context.get('target_app_did', None)
        if not target_did:
            logging.debug(f"Error while executing script named '{script_name}': target_did not set")
            return self.response.response_err(BAD_REQUEST, "target_did not set")
        if not target_app_did:
            logging.debug(f"Error while executing script named '{script_name}': target_app_did not set")
            return self.response.response_err(BAD_REQUEST, "target_app_did not set")

        params = content.get('params', None)
        return self.__run_script(script_name, caller_did, caller_app_did, target_did, target_app_did, params)

    def run_script_upload(self, transaction_id):
        row_id, target_did, target_app_did, file_name, err = self.run_script_fileapi_setup(transaction_id, "upload")
        if err:
            logging.debug(err[1])
            return self.response.response_err(err[0], err[1])

        _, resp_err = v2_wrapper(self.ipfs_files.upload_file_with_path)(target_did, target_app_did, file_name)
        if resp_err:
            return resp_err

        err_message = self.run_script_fileapi_teardown(row_id, target_did, target_app_did, "upload")
        if err_message:
            logging.debug(err_message)
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)

        return self.response.response_ok()

    def run_script_download(self, transaction_id):
        row_id, target_did, target_app_did, file_name, err = self.run_script_fileapi_setup(transaction_id, "download")
        if err:
            logging.debug(err[1])
            return self.response.response_err(err[0], err[1])

        data, resp_err = v2_wrapper(self.ipfs_files.download_file_with_path)(
            target_did, target_app_did, file_name
        )
        if resp_err:
            return resp_err

        err_message = self.run_script_fileapi_teardown(row_id, target_did, target_app_did, "download")
        if err_message:
            logging.debug(err_message)
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)

        return data

    def run_script_fileapi_setup(self, transaction_id, fileapi_type):
        # Request script content first
        try:
            transaction_detail = jwt.decode(transaction_id, hive_setting.PASSWORD, algorithms=['HS256'])
            row_id, target_did, target_app_did = transaction_detail.get('row_id', None), transaction_detail.get('target_did', None), \
                                                 transaction_detail.get('target_app_did', None)
        except Exception as e:
            err = [INTERNAL_SERVER_ERROR, f"Error while executing file {fileapi_type} via scripting: Could not unpack details "
                        f"from transaction_id jwt token. Exception: {str(e)}"]
            return None, None, None, None, err

        r, m = can_access_vault(target_did, VAULT_ACCESS_R)
        if r != SUCCESS:
            err = [r, f"Error while executing file {fileapi_type} via scripting: vault can not be accessed"]
            return None, None, None, None, err

        # Find the temporary tx in the database
        try:
            col = get_collection(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION)
            content_filter = {
                "_id": ObjectId(row_id)
            }
            script_temp_tx = col.find_one(content_filter)
        except Exception as e:
            err = [NOT_FOUND, f"Error while executing file {fileapi_type} via scripting: Exception: {str(e)}"]
            return None, None, None, None, err

        if not script_temp_tx:
            err = [NOT_FOUND, f"Error while executing file {fileapi_type} via scripting: "
                        f"Exception: Could not find the transaction ID '{transaction_id}' in the database"]
            return None, None, None, None, err

        file_name = script_temp_tx.get('file_name', None)
        if not file_name:
            err = [NOT_FOUND, f"Error while executing file {fileapi_type} via scripting: Could not find a file_name "
                        f"'{file_name}' to be used to upload"]
            return None, None, None, None, err

        return row_id, target_did, target_app_did, file_name, None

    def run_script_fileapi_teardown(self, row_id, target_did, target_app_did, fileapi_type):
        try:
            col = get_collection(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION)
            content_filter = {
                "filter": {
                    "_id": ObjectId(row_id)
                }
            }
            _, err_message = query_delete_one(col, content_filter)
            if err_message:
                err_message = f"Error while executing file {fileapi_type} via scripting: {err_message}"
                return err_message
            db_size = get_mongo_database_size(target_did, target_app_did)
            update_vault_db_use_storage_byte(target_did, db_size)
        except Exception as e:
            err_message = f"Error while executing file {fileapi_type} via scripting: Exception: {str(e)}"
            return err_message
        return None

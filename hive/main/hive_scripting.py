import copy
import os
import logging

import jwt
from bson import ObjectId
from flask import request
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid

from hive.main.interceptor import post_json_param_pre_proc, check_auth
from hive.settings import hive_setting
from hive.util.auth import did_auth
from hive.util.constants import SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_EXECUTABLE_TYPE_FIND, SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR, \
    SCRIPTING_EXECUTABLE_TYPE_INSERT, SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS, SCRIPTING_EXECUTABLE_TYPE_AGGREGATED, \
    SCRIPTING_EXECUTABLE_TYPE_UPDATE, SCRIPTING_EXECUTABLE_TYPE_DELETE, SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES, SCRIPTING_EXECUTABLE_TYPE_FILE_HASH, SCRIPTING_EXECUTABLE_DOWNLOADABLE, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD, VAULT_ACCESS_WR, VAULT_ACCESS_R, VAULT_ACCESS_DEL,\
    SCRIPTING_SCRIPT_TEMP_TX_COLLECTION
from hive.util.did_file_info import filter_path_root, query_upload_get_filepath, query_download, query_properties,\
    query_hash
from hive.util.did_mongo_db_resource import gene_mongo_db_name, \
    get_collection, get_mongo_database_size, query_delete_one, convert_oid
from hive.util.did_scripting import check_json_param, run_executable_find, run_condition, run_executable_insert, \
    run_executable_update, run_executable_delete, run_executable_file_download, run_executable_file_properties, \
    run_executable_file_hash, run_executable_file_upload, massage_keys_with_dollar_signs, \
    unmassage_keys_with_dollar_signs, get_script_content
from hive.util.error_code import INTERNAL_SERVER_ERROR, BAD_REQUEST, UNAUTHORIZED, FORBIDDEN, NOT_FOUND, SUCCESS
from hive.util.payment.vault_service_manage import can_access_vault, update_vault_db_use_storage_byte, \
    inc_vault_file_use_storage_byte
from hive.util.server_response import ServerResponse
from hive.util.http_response import NotFoundException, ErrorCode, hive_restful_response, hive_download_response,\
    BadRequestException
from hive.util.database_client import cli
from hive.util.did_scripting import populate_with_params_values, populate_options_count_documents,\
    populate_options_find_many, populate_options_insert_one, populate_options_update_one


class HiveScripting:
    def __init__(self, app=None):
        self.app = app
        self.response = ServerResponse("HiveScripting")

    def init_app(self, app):
        self.app = app

    def __upsert_script_to_db(self, did, app_id, content):
        if hive_setting.MONGO_URI:
            uri = hive_setting.MONGO_URI
            connection = MongoClient(uri)
        else:
            connection = MongoClient(host=hive_setting.MONGO_HOST, port=hive_setting.MONGO_PORT)

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
        return data

    def run_script_url(self, target_did, target_app_did, script_name, params):
        # Get caller info
        caller_did, caller_app_did = did_auth()

        data = self.__run_script(script_name, caller_did, caller_app_did, target_did, target_app_did, params)

        return self.response.response_ok(data)

    def run_script(self):
        # Request script content first
        content, err = get_script_content(self.response, "name")
        if err:
            return err

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
        data = self.__run_script(script_name, caller_did, caller_app_did, target_did, target_app_did, params)

        return self.response.response_ok(data)

    def run_script_upload(self, transaction_id):
        row_id, target_did, target_app_did, file_name, err = self.run_script_fileapi_setup(transaction_id, "upload")
        if err:
            logging.debug(err[1])
            return self.response.response_err(err[0], err[1])

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
            return self.response.response_err(INTERNAL_SERVER_ERROR, f"Exception: {str(e)}")

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

        data, status_code = query_download(target_did, target_app_did, file_name)
        if status_code != SUCCESS:
            logging.debug(f"Error while executing file download via scripting: Could not download file")
            return self.response.response_err(status_code, "Could not download file")

        err_message = self.run_script_fileapi_teardown(row_id, target_did, target_app_did, "download")
        if err_message:
            logging.debug(err_message)
            return self.response.response_err(INTERNAL_SERVER_ERROR, err_message)

        return data

    def run_script_fileapi_setup(self, transaction_id, fileapi_type):
        # Request script content first
        try:
            transaction_detail = jwt.decode(transaction_id, hive_setting.DID_STOREPASS, algorithms=['HS256'])
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


def validate_exists(json_data, parent_name, prop_list):
    for prop in prop_list:
        parts = prop.split('.')
        prop_name = parent_name + '.' + parts[0] if parent_name else parts[0]
        if parts.length > 1:
            validate_exists(json_data[parts[0]], prop_name, '.'.join(parts[1:]))
        else:
            if not json_data.get(prop, None):
                raise BadRequestException(msg=f'Parameter {prop_name} MUST be provided')


class Condition:
    def __init__(self, json_data, params, did, app_id):
        self.json_data = json_data
        self.params = params
        self.did = did
        self.app_id = app_id

    @staticmethod
    def validate_data(json_data):
        if not json_data:
            return
        Condition.__validate_type(json_data, 1)

    @staticmethod
    def __validate_type(json_data, layer):
        if layer > 5:
            raise BadRequestException(msg='Too more nested conditions.')

        validate_exists(json_data, 'condition', ['name', 'type', 'body'])

        condition_type = json_data['type']
        if condition_type not in ['or', 'and', 'queryHasResults']:
            raise BadRequestException(msg=f"Unsupported condition type {condition_type}")

        if condition_type in ['and', 'or']:
            if not isinstance(json_data['body'], list)\
                    or json_data['body'].length < 1:
                raise BadRequestException(msg=f"Condition body MUST be list "
                                              f"and at least contain one element for the type '{condition_type}'")
            for data in json_data['body']:
                Condition.__validate_type(data, layer + 1)
        else:
            validate_exists(json_data['body'], 'condition.body', ['collection', ])

    def is_satisfied(self) -> bool:
        return self.__is_satisfied(self.json_data)

    def __is_satisfied(self, json_data) -> bool:
        ctype = json_data['type']
        if ctype == 'or':
            for data in json_data['body']:
                is_sat = self.__is_satisfied(data)
                if is_sat:
                    return True
            return False
        elif ctype == 'and':
            for data in json_data['body']:
                is_sat = self.__is_satisfied(data)
                if not is_sat:
                    return False
            return True
        else:
            return self.__is_satisfied_query_has_result(json_data)

    def __is_satisfied_query_has_result(self, json_data):
        col_name = json_data['collection']
        col_filter = json_data.get('filter', {})
        msg = populate_with_params_values(self.did, self.app_id, col_filter, self.params)
        if msg:
            raise BadRequestException(msg='Cannot find parameter: ' + msg)

        col = cli.get_user_collection(self.did, self.app_id, col_name)
        if not col:
            raise BadRequestException(msg='Do not find condition collection with name ' + col_name)

        options = populate_options_count_documents(json_data.get('body', {}))
        return col.count_documents(convert_oid(col_filter), **options) > 0


class Context:
    def __init__(self, json_data, did, app_id):
        self.target_did = did
        self.target_app_did = app_id
        if json_data:
            self.target_did = json_data['target_did']
            self.target_app_did = json_data['target_app_did']

    @staticmethod
    def validate_data(json_data):
        if not json_data:
            return

        target_did = json_data.get('target_did')
        target_app_did = json_data.get('target_app_did')
        if not target_did or target_app_did:
            raise BadRequestException(msg='target_did or target_app_did MUST be set.')

    def get_script_data(self, script_name):
        col = cli.get_user_collection(self.target_did, self.target_app_did, SCRIPTING_SCRIPT_COLLECTION)
        return col.find_one({'name': script_name})


class Executable:
    def __init__(self, script, executable_data):
        self.script = script
        self.name = executable_data['name']
        self.body = executable_data['body']
        self.is_output = executable_data.get('output', False)

    @staticmethod
    def validate_data(json_data):
        validate_exists(json_data, 'executable', ['name', 'type', 'body'])

        if json_data['type'] not in [SCRIPTING_EXECUTABLE_TYPE_AGGREGATED,
                                     SCRIPTING_EXECUTABLE_TYPE_FIND,
                                     SCRIPTING_EXECUTABLE_TYPE_INSERT,
                                     SCRIPTING_EXECUTABLE_TYPE_UPDATE,
                                     SCRIPTING_EXECUTABLE_TYPE_DELETE,
                                     SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD,
                                     SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD,
                                     SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES,
                                     SCRIPTING_EXECUTABLE_TYPE_FILE_HASH]:
            raise BadRequestException(msg=f"Invalid type {json_data['type']} of the executable.")

        if json_data['type'] == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED \
                and (not isinstance(json_data['body'], list) or json_data['body'].length < 1):
            raise BadRequestException(msg=f"Executable body MUST be list for type "
                                          f"'{SCRIPTING_EXECUTABLE_TYPE_AGGREGATED}'.")

        if json_data['type'] in [SCRIPTING_EXECUTABLE_TYPE_FIND,
                                 SCRIPTING_EXECUTABLE_TYPE_INSERT,
                                 SCRIPTING_EXECUTABLE_TYPE_UPDATE,
                                 SCRIPTING_EXECUTABLE_TYPE_DELETE]:
            validate_exists(json_data['body'], 'executable.body', ['collection', 'filter'])

        if json_data['type'] in [SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD,
                                 SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD,
                                 SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES,
                                 SCRIPTING_EXECUTABLE_TYPE_FILE_HASH]:
            validate_exists(json_data['body'], 'executable.body', ['path', ])

    def execute(self):
        pass

    def get_did(self):
        return self.script.did

    def get_app_id(self):
        return self.script.app_id

    def get_target_did(self):
        return self.script.context.target_did

    def get_target_app_did(self):
        return self.script.context.target_app_did

    def get_collection_name(self):
        return self.body['collection']

    def get_filter(self):
        return self.body.get('filter', {})

    def get_context(self):
        return self.script.context

    def get_document(self):
        return self.body.get('document', {})

    def get_update(self):
        return self.body.get('update', {})

    def get_params(self):
        return self.body['params']

    def get_output_data(self, data):
        return data if self.is_output else None

    def get_populated_filter(self):
        col_filter = self.get_filter()
        msg = populate_with_params_values(self.get_did(), self.get_app_id(), col_filter, self.get_params())
        if msg:
            raise BadRequestException(msg='Cannot get parameter value for the executable filter: ' + msg)
        return col_filter

    def get_populated_body(self):
        body = self.body
        msg = populate_with_params_values(self.get_did(), self.get_app_id(), body, self.get_params())
        if msg:
            raise BadRequestException(msg='Cannot get parameter value for the executable body: ' + msg)
        return body

    def _create_transaction(self, permission, action_type):
        cli.check_vault_access(self.get_target_did(), permission)

        body = self.get_populated_body()
        full_path, err = query_upload_get_filepath(self.get_target_did(), self.get_target_app_did(), body['path'])
        if err:
            raise BadRequestException(msg='Cannot get file full path with error message: ' + str(err))

        data = cli.insert_one(self.get_target_did(),
                              self.get_target_app_did(),
                              SCRIPTING_SCRIPT_TEMP_TX_COLLECTION,
                              {
                                  "document": {
                                      "file_name": body['path'],
                                      "fileapi_type": action_type
                                  }
                              })
        if not data.get('inserted_id', None):
            raise BadRequestException('Cannot retrieve the transaction ID.')

        update_vault_db_use_storage_byte(self.get_target_did(),
                                         get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))

        return {
            "transaction_id": jwt.encode({
                "row_id": data.get('inserted_id', None),
                "target_did": self.get_target_did(),
                "target_app_did": self.get_target_app_did()
            }, hive_setting.DID_STOREPASS, algorithm='HS256')
        }

    @staticmethod
    def create(script, executable_data):
        result = []
        Executable.__create(result, script, executable_data)
        return result

    @staticmethod
    def __create(result, script, executable_data):
        executable_type = executable_data['type']
        executable_body = executable_data['body']
        if executable_type == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            for data in executable_body:
                Executable.__create(result, script, data)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FIND:
            result.append(FindExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            result.append(InsertExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_UPDATE:
            result.append(UpdateExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_DELETE:
            result.append(DeleteExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD:
            result.append(FileUploadExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD:
            result.append(FileDownloadExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES:
            result.append(FilePropertiesExecutable(script, executable_data))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_HASH:
            result.append(FileHashExecutable(script, executable_data))


class FindExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(self.get_target_did(), VAULT_ACCESS_R)
        return self.get_output_data({"items": cli.find_many(self.get_target_did(),
                                                            self.get_target_app_did(),
                                                            self.get_populated_filter(),
                                                            populate_options_find_many(self.body))})


class InsertExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(self.get_target_did(), VAULT_ACCESS_WR)

        document = self.get_document()
        msg = populate_with_params_values(self.get_did(), self.get_app_id(), document, self.get_params())
        if msg:
            raise BadRequestException(msg='Cannot get parameter value for the executable document: ' + msg)

        data = cli.insert_one(self.get_target_did(),
                              self.get_target_app_did(),
                              self.get_collection_name(),
                              document,
                              populate_options_insert_one(self.body))

        update_vault_db_use_storage_byte(self.get_did(),
                                         get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))

        return self.get_output_data(data)


class UpdateExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(self.get_target_did(), VAULT_ACCESS_WR)

        col_update = self.get_update()
        msg = populate_with_params_values(self.get_did(), self.get_app_id(), col_update.get('$set'), self.get_params())
        if msg:
            raise BadRequestException(msg='Cannot get parameter value for the executable update: ' + msg)

        data = cli.update_one(self.get_target_did(),
                              self.get_target_app_did(),
                              self.get_collection_name(),
                              self.get_populated_filter(),
                              col_update,
                              populate_options_update_one(self.body))

        update_vault_db_use_storage_byte(self.get_did(),
                                         get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))

        return self.get_output_data(data)


class DeleteExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(self.get_target_did(), VAULT_ACCESS_DEL)

        data = cli.delete_one(self.get_target_did(),
                              self.get_target_app_did(),
                              self.get_collection_name(),
                              self.get_populated_filter())

        update_vault_db_use_storage_byte(self.get_did(),
                                         get_mongo_database_size(self.get_target_did(), self.get_target_app_did()))

        return self.get_output_data(data)


class FileUploadExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        return self._create_transaction(VAULT_ACCESS_WR, 'upload')


class FileDownloadExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        return self._create_transaction(VAULT_ACCESS_R, 'download')


class FilePropertiesExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(VAULT_ACCESS_R)

        body = self.get_populated_body()
        full_path, err = query_upload_get_filepath(self.get_target_did(), self.get_target_app_did(), body['path'])
        if err:
            raise BadRequestException(msg='Cannot get file full path with error message: ' + str(err))

        data, err = query_properties(self.get_target_did(), self.get_target_app_did(), body['path'])
        if err:
            raise BadRequestException('Failed to get file properties with error message: ' + str(err))
        return self.get_output_data(data)


class FileHashExecutable(Executable):
    def __init__(self, script, executable_data):
        super().__init__(script, executable_data)

    def execute(self):
        cli.check_vault_access(VAULT_ACCESS_R)

        body = self.get_populated_body()
        full_path, err = query_upload_get_filepath(self.get_target_did(), self.get_target_app_did(), body['path'])
        if err:
            raise BadRequestException(msg='Cannot get file full path with error message: ' + str(err))

        data, err = query_hash(self.get_target_did(), self.get_target_app_did(), body['path'])
        if err:
            raise BadRequestException('Failed to get file hash code with error message: ' + str(err))
        return self.get_output_data(data)


class Script:
    def __init__(self, script_name, run_data, did, app_id):
        self.did = did
        self.app_id = app_id
        self.name = script_name
        self.context = Context(run_data['context'], did, app_id)
        self.params = run_data['params']
        self.condition = None
        self.executables = []
        self.anonymous_user = False
        self.anonymous_app = False

    @staticmethod
    def validate_script_data(json_data):
        if not json_data:
            raise BadRequestException(msg="Script definition can't be empty.")

        validate_exists(json_data, '', ['executable', ])

        Condition.validate_data(json_data.get('condition', None))
        Executable.validate_data(json_data['executable'])

        anonymous_user = json_data.get('allowAnonymousUser', False)
        anonymous_app = json_data.get('allowAnonymousApp', False)
        if anonymous_user and not anonymous_app:
            raise BadRequestException(msg="Do not support 'allowAnonymousUser' true and 'allowAnonymousApp' false.")

    @staticmethod
    def validate_run_data(json_data):
        validate_exists(json_data, '', ['params', ])
        Context.validate_data(json_data['context'])

    def execute(self):
        """
        Run executables and return response data for the executable which output option is true.
        """
        script_data = self.context.get_script_data(self.name)
        if not script_data:
            raise BadRequestException(msg=f"Can't get the script with name '{self.name}'")
        self.executables = Executable.create(self, script_data['executable'])
        self.anonymous_user = script_data.get('allowAnonymousUser', False)
        self.anonymous_app = script_data.get('allowAnonymousApp', False)

        result = dict()
        for executable in self.executables:
            self.condition = Condition(script_data['condition'], executable.get_params(), self.did, self.app_id)
            if not self.condition.is_satisfied():
                raise BadRequestException(msg="Caller can't match the condition for the script.")

            ret = executable.execute()
            if ret:
                result[executable['name']] = ret

        return result


class HiveScriptingV2:
    def __init__(self, app=None):
        self.app = app

    def __check(self, permission):
        did, app_id = check_auth()
        cli.check_vault_access(did, permission)
        return did, app_id

    @hive_restful_response
    def set_script(self, script_name):
        did, app_id = self.__check(VAULT_ACCESS_WR)

        json_data = request.get_json(force=True, silent=True)
        Script.validate_script_data(json_data)

        result = self.__upsert_script_to_database(script_name, json_data, did, app_id)
        update_vault_db_use_storage_byte(did, get_mongo_database_size(did, app_id))
        return result

    def __upsert_script_to_database(self, script_name, json_data, did, app_id):
        col = cli.get_user_collection(did, app_id, SCRIPTING_SCRIPT_COLLECTION, True)
        json_data['name'] = script_name
        options = {
            "upsert": True,
            "bypass_document_validation": False
        }
        ret = col.replace_one({"name": script_name}, convert_oid(json_data), **options)
        return {
            "acknowledged": ret.acknowledged,
            "matched_count": ret.matched_count,
            "modified_count": ret.modified_count,
            "upserted_id": str(ret.upserted_id) if ret.upserted_id else '',
        }

    @hive_restful_response
    def delete_script(self, script_name):
        did, app_id = self.__check(VAULT_ACCESS_DEL)

        col = cli.get_user_collection(did, app_id, SCRIPTING_SCRIPT_COLLECTION)
        if not col:
            raise NotFoundException(ErrorCode.SCRIPT_NOT_FOUND, 'The script collection does not exist.')

        ret = col.delete_many({'name': script_name})
        if ret.deleted_count <= 0:
            raise NotFoundException(ErrorCode.SCRIPT_NOT_FOUND, 'The script tried to remove does not exist.')

        update_vault_db_use_storage_byte(did, get_mongo_database_size(did, app_id))

    @hive_restful_response
    def run_script(self, script_name):
        json_data = request.get_json(force=True, silent=True)
        Script.validate_run_data(json_data)
        did, app_id = check_auth()
        return Script(script_name, json_data, did, app_id).execute()

    @hive_restful_response
    def run_script_url(self, script_name, target_did, target_app_did, params):
        json_data = {
            'context': {
                'target_did': target_did,
                'target_app_did': target_app_did
            },
            'params': params
        }
        Script.validate_run_data(json_data)
        did, app_id = check_auth()
        return Script(script_name, json_data, did, app_id).execute()

    @hive_restful_response
    def upload_file(self, transaction_id):
        return self.handle_transaction(transaction_id)

    def handle_transaction(self, transaction_id, is_download=False):
        did, app_id = self.__check(VAULT_ACCESS_R if is_download else VAULT_ACCESS_WR)

        row_id, target_did, target_app_did = self.parse_transaction_id(transaction_id)
        col_filter = {"_id": ObjectId(row_id)}
        trans = cli.find_one(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION, col_filter)
        if not trans:
            raise BadRequestException("Cannot find the transaction by id.")

        data = None
        if is_download:
            data, status_code = query_download(target_did, target_app_did, trans['file_name'])
            if status_code == BAD_REQUEST:
                raise BadRequestException(msg='Cannot get file name by transaction id')
            elif status_code == NOT_FOUND:
                raise BadRequestException(msg=f"The file '{trans['file_name']}' does not exist.")
            elif status_code == FORBIDDEN:
                raise BadRequestException(msg=f"Cannot access the file '{trans['file_name']}'.")
            return data
        else:
            file_full_path, err = query_upload_get_filepath(target_did, target_app_did,
                                                            filter_path_root(trans['file_name']))
            if err:
                raise BadRequestException('Failed get file full path with error message: ' + str(err))
            inc_vault_file_use_storage_byte(target_did, cli.stream_to_file(request.stream, file_full_path))

        cli.delete_one(target_did, target_app_did, SCRIPTING_SCRIPT_TEMP_TX_COLLECTION, col_filter)
        update_vault_db_use_storage_byte(target_did, get_mongo_database_size(target_did, target_app_did))

        return data

    @hive_download_response
    def download_file(self, transaction_id):
        return self.handle_transaction(transaction_id, is_download=True)

    def parse_transaction_id(self, transaction_id):
        try:
            trans = jwt.decode(transaction_id, hive_setting.DID_STOREPASS, algorithms=['HS256'])
            return trans.get('row_id', None), trans.get('target_did', None), trans.get('target_app_did', None)
        except Exception as e:
            raise BadRequestException(msg=f"Invalid transaction id '{transaction_id}'")

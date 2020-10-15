import copy
import json

from flask import request
from pymongo import MongoClient

from hive.main.interceptor import post_json_param_pre_proc, pre_proc
from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.constants import SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_EXECUTABLE_TYPE_FIND, SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR, \
    SCRIPTING_EXECUTABLE_TYPE_INSERT, SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS, SCRIPTING_EXECUTABLE_TYPE_AGGREGATED, \
    SCRIPTING_EXECUTABLE_TYPE_UPDATE, SCRIPTING_EXECUTABLE_TYPE_DELETE, SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES, SCRIPTING_EXECUTABLE_TYPE_FILE_HASH, SCRIPTING_EXECUTABLE_DOWNLOADABLE, \
    SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import gene_mongo_db_name, query_update_one, populate_options_update_one
from hive.util.did_scripting import check_json_param, run_executable_find, run_condition, run_executable_insert, \
    run_executable_update, run_executable_delete, run_executable_file_download, run_executable_file_properties, \
    run_executable_file_hash, run_executable_file_upload
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

        if SCRIPTING_SCRIPT_COLLECTION not in db.list_collection_names():
            try:
                col = db.create_collection(SCRIPTING_SCRIPT_COLLECTION)
            except Exception as e:
                return None, f"Could not create collection. Please try again later. Exception : {str(e)}"
        else:
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
                return f"Invalid parameters passed for executble type '{executable_type}'"
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
            err_message = check_json_param(executable_body, f"{executable.get('name')}",
                                           args=["collection", "filter", "update"])
            if err_message:
                return err_message
            # We need to make sure to put extra quotation around "$set" or mongo update is going to fail because
            # it's going to try to validate it
            update_set = executable_body.get('update').get("$set", None)
            if update_set:
                executable_body["update"]["'$set'"] = update_set
                executable_body['update'].pop("$set", None)
            return None
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

    def __condition_execution(self, did, app_id, target_did, condition, params):
        condition_type = condition.get('type')
        condition_body = condition.get('body')
        if condition_type in [SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR]:
            if len(condition_body) == 1:
                return self.__condition_execution(did, app_id, target_did, condition_body[0], params)
            new_condition = {
                "type": condition_type,
                "body": condition_body[1:]
            }
            if condition_type == SCRIPTING_CONDITION_TYPE_AND:
                return self.__condition_execution(did, app_id, target_did, condition_body[0], params) and \
                       self.__condition_execution(did, app_id, target_did, new_condition, params)
            elif condition_type == SCRIPTING_CONDITION_TYPE_OR:
                return self.__condition_execution(did, app_id, target_did, condition_body[0], params) or \
                       self.__condition_execution(did, app_id, target_did, new_condition, params)
        else:
            return run_condition(did, app_id, target_did, condition_body, params)

    def __executable_execution(self, did, app_id, target_did, executable, params, output={}, output_key=None, capture_output=False):
        executable_type = executable.get('type')
        executable_body = executable.get('body')
        if not output_key:
            output_key = executable.get('name')

        if not capture_output:
            capture_output = executable.get('output', False)

        if executable_type == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            err_message = None
            for i, e in enumerate(executable_body):
                self.__executable_execution(did, app_id, target_did, e, params, output, e.get('name'), e.get('output', False))
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FIND:
            data, err_message = run_executable_find(did, app_id, target_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            data, err_message = run_executable_insert(did, app_id, target_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_UPDATE:
            data, err_message = run_executable_update(did, app_id, target_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_DELETE:
            data, err_message = run_executable_delete(did, app_id, target_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_UPLOAD:
            data, err_message = {}, None
            if capture_output:
                data, err_message = run_executable_file_upload(did, app_id, target_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_DOWNLOAD:
            data, err_message = run_executable_file_download(did, app_id, target_did, executable_body, params)
            if capture_output:
                output[SCRIPTING_EXECUTABLE_DOWNLOADABLE] = output_key
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_PROPERTIES:
            data, err_message = run_executable_file_properties(did, app_id, target_did, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FILE_HASH:
            data, err_message = run_executable_file_hash(did, app_id, target_did, executable_body, params)
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
        did, app_id, content, err = post_json_param_pre_proc(self.response, "name", "executable")
        if err:
            return err

        # Data Validation
        executable = content.get('executable')
        err_message = self.__executable_validation(executable)
        if err_message:
            return self.response.response_err(400, err_message)

        # Condition Validation
        condition = content.get('condition', None)
        if condition:
            err_message = check_json_param(condition, "condition", args=["type", "name", "body"])
            if err_message:
                return self.response.response_err(400, err_message)
            nested_count = self.__count_nested_condition(condition)
            for count in nested_count.values():
                if count >= 5:
                    err_message = "conditions cannot be nested more than 5 times"
                    return self.response.response_err(400, err_message)
            is_valid = self.__condition_validation(condition)
            if not is_valid:
                err_message = "some of the parameters are not set for 'condition'"
                return self.response.response_err(400, err_message)

        # Create collection "scripts" if it doesn't exist and
        # create/update script in the database
        data, err_message = self.__upsert_script_to_db(did, app_id, content)
        if err_message:
            return self.response.response_err(500, err_message)
        return self.response.response_ok(data)

    def run_script(self):
        content = {}
        # Sometimes, the script may be uploading a file so we need to handle the multi-form data first
        try:
            metadata = request.form.get('metadata', {})
            if metadata:
                content = json.loads(metadata)
                if content:
                    caller_did, caller_app_id, response = pre_proc(self)
                    if response is not None:
                        return response
                    valid_content = check_json_param(content, content.get("name", ""), args=["name", "params"])
                    if valid_content:
                        err_message = "Exception: parameter is not valid"
                        return self.response.response_err(400, err_message)
        except ValueError as e:
            pass

        if not content:
            # Request the Caller DID and Caller App Validation
            caller_did, caller_app_id, content, err = post_json_param_pre_proc(self.response, "name")
            if err:
                return err

        target_did, target_app_did = caller_did, caller_app_id
        # Request the Target DID and Target App Validation if present
        context = content.get('context', {})
        if context:
            target_did = context.get('target_did', caller_did)
            # Uncomment when anonymous app_did is allowed
            #target_app_did = context.get('target_app_did', app_id)

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
            return self.response.response_err(404, err_message)

        if not script:
            return self.response.response_err(404, err_message)

        params = content.get('params', None)
        condition = script.get('condition', None)
        if condition:
            passed = self.__condition_execution(caller_did, caller_app_id, target_did, condition, params)
            if not passed:
                err_message = f"the conditions were not met to execute this script"
                return self.response.response_err(403, err_message)

        executable = script.get("executable")
        output = {}
        data = self.__executable_execution(caller_did, caller_app_id, target_did, executable, params, output=output)

        download_file = output.get(SCRIPTING_EXECUTABLE_DOWNLOADABLE, None)
        if download_file:
            data = output.get(download_file)
            return data

        return self.response.response_ok(data)

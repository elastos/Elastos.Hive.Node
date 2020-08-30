import logging

from bson import ObjectId
from pymongo import MongoClient

from datetime import datetime

from hive.main.interceptor import post_json_param_pre_proc
from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.constants import SCRIPTING_CONDITION_COLLECTION, SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_EXECUTABLE_TYPE_FIND, DATETIME_FORMAT, \
    SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR, \
    SCRIPTING_EXECUTABLE_TYPE_INSERT, SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS, SCRIPTING_EXECUTABLE_TYPE_AGGREGATED
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import gene_mongo_db_name, \
    options_filter, query_update_one
from hive.util.did_scripting import check_json_param, run_executable_find, run_condition, run_executable_insert
from hive.util.server_response import response_ok, response_err


class HiveScripting:
    def __init__(self, app=None):
        self.app = app

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
            }
        }
        options = {
            "upsert": True,
            "bypass_document_validation": False
        }

        data, err_message = query_update_one(col, new_content, options)
        if err_message:
            return None, err_message

        return data, None

    def __condition_validation(self, condition):
        err_message = check_json_param(condition, "condition", args=["type", "body"])
        if err_message:
            return err_message
        condition_type = condition.get('type')
        condition_body = condition.get('body')
        if condition_type == SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS:
            return None
        if condition_type in [SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR]:
            if len(condition_body) == 1:
                return self.__condition_validation(condition_body[0])
            else:
                new_condition = {
                    "type": condition_type,
                    "body": condition_body[1:]
                }
                return self.__condition_validation(new_condition)
        else:
            return f"invalid condition type '{condition_type}"

    def __executable_validation(self, executable):
        err_message = check_json_param(executable, "executable", args=["type", "body"])
        if err_message:
            return err_message
        executable_type = executable.get('type')
        executable_body = executable.get('body')
        if executable_type == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            if len(executable_body) == 1:
                return self.__executable_validation(executable_body[0])
            else:
                new_executable = {
                    "type": SCRIPTING_EXECUTABLE_TYPE_AGGREGATED,
                    "body": executable_body[1:]
                }
                return self.__executable_validation(new_executable)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FIND:
            return check_json_param(executable_body, f"{executable.get('name')}", args=["collection", "filter"])
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            return check_json_param(executable_body, f"{executable.get('name')}", args=["collection", "document"])
        else:
            return f"invalid executable type '{executable_type}"
        
    def __condition_execution(self, did, app_id, condition, params):
        condition_type = condition.get('type')
        condition_body = condition.get('body')
        if condition_type == SCRIPTING_CONDITION_TYPE_AND:
            if len(condition_body) == 1:
                return self.__condition_execution(did, app_id, condition_body[0], params)
            else:
                new_condition = {
                    "type": SCRIPTING_CONDITION_TYPE_AND,
                    "body": condition_body[1:]
                }
                return self.__condition_execution(did, app_id, condition_body[0], params) and \
                       self.__condition_execution(did, app_id, new_condition, params)
        elif condition_type == SCRIPTING_CONDITION_TYPE_OR:
            if len(condition_body) == 1:
                return self.__condition_execution(did, app_id, condition_body[0], params)
            else:
                new_condition = {
                    "type": SCRIPTING_CONDITION_TYPE_OR,
                    "body": condition_body[1:]
                }
                return self.__condition_execution(did, app_id, condition_body[0], params) or \
                       self.__condition_execution(did, app_id, new_condition, params)
        else:
            return run_condition(did, app_id, condition_body, params)

    def __executable_execution(self, did, app_id, executable, params):
        executable_type = executable.get('type')
        executable_body = executable.get('body')
        if executable_type == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            if len(executable_body) == 1:
                return self.__executable_execution(did, app_id, executable_body[0], params)
            else:
                new_executable = {
                    "type": SCRIPTING_EXECUTABLE_TYPE_AGGREGATED,
                    "body": executable_body[1:]
                }
                return self.__executable_execution(did, app_id, new_executable, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FIND:
            return run_executable_find(did, app_id, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            return run_executable_insert(did, app_id, executable_body, params)

    def set_script(self):
        # Request Validation
        did, app_id, content, err = post_json_param_pre_proc("name", "executable")
        if err:
            return err

        # Data Validation
        executable = content.get('executable')
        err_message = self.__executable_validation(executable)
        if err_message:
            logging.debug(err_message)
            return response_err(400, err_message)

        # Condition Validation
        condition = content.get('condition', None)
        if condition:
            err_message = self.__condition_validation(condition)
            if err_message:
                logging.debug(err_message)
                return response_err(400, err_message)

        # Create collection "scripts" if it doesn't exist and
        # create/update script in the database
        data, err_message = self.__upsert_script_to_db(did, app_id, content)
        if err_message:
            logging.debug(err_message)
            return response_err(500, err_message)
        return response_ok(data)

    def run_script(self):
        # Request Validation
        did, app_id, content, err = post_json_param_pre_proc("name")
        if err:
            return err

        # Find the script in the database
        col = get_collection(did, app_id, SCRIPTING_SCRIPT_COLLECTION)
        content_filter = {
            "name": content["name"]
        }
        try:
            script = col.find_one(content_filter)
            if ("_id" in script) and (isinstance(script["_id"], ObjectId)):
                script["_id"] = str(script["_id"])
        except Exception as e:
            err_message = f"could not find script '{content['name']}' in the database. Please register the script " \
                          f"first with set_script' API endpoint. Exception: {str(e)}"
            logging.debug(err_message)
            return response_err(404, err_message)

        params = content.get('params', None)
        condition = script.get("condition")
        if condition:
            passed = self.__condition_execution(did, app_id, condition, params)
            if not passed:
                err_message = f"the conditions were not met to execute this script"
                logging.debug(err_message)
                return response_err(403, err_message)

        executable = script.get("executable")
        data, err_message = self.__executable_execution(did, app_id, executable, params)
        if err_message:
            logging.debug(err_message)
            return response_err(500, err_message)

        return response_ok(data)

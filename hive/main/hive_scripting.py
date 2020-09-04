import copy
import logging

from bson import ObjectId
from pymongo import MongoClient

from hive.main.interceptor import post_json_param_pre_proc
from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.constants import SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_EXECUTABLE_TYPE_FIND, SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR, \
    SCRIPTING_EXECUTABLE_TYPE_INSERT, SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS, SCRIPTING_EXECUTABLE_TYPE_AGGREGATED
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import gene_mongo_db_name, query_update_one
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
            return check_json_param(executable_body, f"{executable.get('name')}", args=["collection", "filter"])
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            return check_json_param(executable_body, f"{executable.get('name')}", args=["collection", "document"])
        else:
            return f"invalid executable type '{executable_type}"

    def __condition_execution(self, did, app_id, condition, params):
        condition_type = condition.get('type')
        condition_body = condition.get('body')
        if condition_type in [SCRIPTING_CONDITION_TYPE_AND, SCRIPTING_CONDITION_TYPE_OR]:
            if len(condition_body) == 1:
                return self.__condition_execution(did, app_id, condition_body[0], params)
            new_condition = {
                "type": condition_type,
                "body": condition_body[1:]
            }
            if condition_type == SCRIPTING_CONDITION_TYPE_AND:
                return self.__condition_execution(did, app_id, condition_body[0], params) and \
                       self.__condition_execution(did, app_id, new_condition, params)
            elif condition_type == SCRIPTING_CONDITION_TYPE_OR:
                return self.__condition_execution(did, app_id, condition_body[0], params) or \
                       self.__condition_execution(did, app_id, new_condition, params)
        else:
            return run_condition(did, app_id, condition_body, params)

    def __executable_execution(self, did, app_id, executable, params):
        executable_type = executable.get('type')
        executable_body = executable.get('body')
        if executable_type == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            for i, e in enumerate(executable_body):
                if i == len(executable_body) - 1:
                    return self.__executable_execution(did, app_id, e, params)
                else:
                    self.__executable_execution(did, app_id, e, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_FIND:
            return run_executable_find(did, app_id, executable_body, params)
        elif executable_type == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            return run_executable_insert(did, app_id, executable_body, params)

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
            err_message = check_json_param(condition, "condition", args=["type", "name", "body"])
            if err_message:
                logging.debug(err_message)
                return response_err(400, err_message)
            nested_count = self.__count_nested_condition(condition)
            for count in nested_count.values():
                if count >= 5:
                    err_message = "conditions cannot be nested more than 5 times"
                    logging.debug(err_message)
                    return response_err(400, err_message)
            is_valid = self.__condition_validation(condition)
            if not is_valid:
                err_message = "some of the parameters are not set for 'condition'"
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
            "name": content.get('name')
        }
        try:
            script = col.find_one(content_filter)
        except Exception as e:
            err_message = f"could not find script '{content['name']}' in the database. Please register the script " \
                          f"first with set_script' API endpoint. Exception: {str(e)}"
            logging.debug(err_message)
            return response_err(404, err_message)

        params = content.get('params')
        condition = script.get('condition', None)
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

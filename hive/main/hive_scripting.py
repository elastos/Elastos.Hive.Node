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
from hive.util.did_scripting import check_json_param, run_executable_find, check_condition, run_executable_insert
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

    def set_script(self):
        # Request Validation
        did, app_id, content, err = post_json_param_pre_proc("name", "executable")
        if err:
            return err

        # Data Validation
        content_executable = content.get('executable')
        err_message = check_json_param(content_executable, "executable", args=["type", "name", "body"])
        if err_message:
            logging.debug(err_message)
            return response_err(400, err_message)

        # Executable Validation for type "aggregated"
        if content_executable.get('type') == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            for executable in content_executable.get('body'):
                err_message = check_json_param(executable, "executable.body", args=["type", "name", "body"])
                if err_message:
                    logging.debug(err_message)
                    return response_err(400, err_message)
                # Executable Validation for type "find"
                if executable.get('type') == SCRIPTING_EXECUTABLE_TYPE_FIND:
                    err_message = check_json_param(executable.get('body'), "executable.body",
                                                   args=["collection", "filter"])
                    if err_message:
                        logging.debug(err_message)
                        return response_err(400, err_message)
                # Executable Validation for type "insert"
                elif executable.get('type') == SCRIPTING_EXECUTABLE_TYPE_INSERT:
                    err_message = check_json_param(executable.get('body'), "executable.body",
                                                   args=["collection", "document"])
                    if err_message:
                        logging.debug(err_message)
                        return response_err(400, err_message)
                else:
                    logging.debug(err_message)
                    return response_err(400, f"invalid executable type '{content_executable.get('type')}")
        # Executable Validation for type "find"
        elif content_executable.get('type') == SCRIPTING_EXECUTABLE_TYPE_FIND:
            err_message = check_json_param(content_executable.get('body'), "executable.body",
                                           args=["collection", "filter"])
            if err_message:
                logging.debug(err_message)
                return response_err(400, err_message)
        # Executable Validation for type "insert"
        elif content_executable.get('type') == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            err_message = check_json_param(content_executable.get('body'), "executable.body",
                                           args=["collection", "document"])
            if err_message:
                logging.debug(err_message)
                return response_err(400, err_message)
        else:
            err_message = f"invalid executable type '{content_executable.get('type')}"
            logging.debug(err_message)
            return response_err(400, err_message)

        # Condition Validation
        condition = content.get('condition', None)
        if condition:
            err_message = check_json_param(condition, "condition", args=["type", "name", "body"])
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
            condition_type = condition.get('type')
            total_passed = [True]
            if condition_type == SCRIPTING_CONDITION_TYPE_AND:
                for c in condition.get('body'):
                    if c.get('type') == SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS:
                        passed = check_condition(did, app_id, c.get('body'), params)
                        if not passed:
                            total_passed.append(False)
                            break
            elif condition_type == SCRIPTING_CONDITION_TYPE_OR:
                for i, c in enumerate(condition.get('body')):
                    if c.get('type') == SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS:
                        passed = check_condition(did, app_id, c.get('body'), params)
                        if passed:
                            total_passed.append(True)
                            break
                        else:
                            if i == len(c.get('body') - 1):
                                total_passed.append(False)
            elif condition_type == SCRIPTING_CONDITION_TYPE_QUERY_HAS_RESULTS:
                passed = check_condition(did, app_id, condition.get('body'), params)
                total_passed.append(passed)
            if False in total_passed:
                err_message = f"the conditions were not met to execute this script"
                logging.debug(err_message)
                return response_err(403, err_message)

        data = {}
        executable = script.get("executable")
        if executable.get('type') == SCRIPTING_EXECUTABLE_TYPE_AGGREGATED:
            for e in executable.get('body'):
                if e.get('type') == SCRIPTING_EXECUTABLE_TYPE_FIND:
                    data, err_message = run_executable_find(did, app_id, e.get('body'), params)
                    if err_message:
                        logging.debug(err_message)
                        return response_err(500, err_message)
                elif e.get('type') == SCRIPTING_EXECUTABLE_TYPE_INSERT:
                    data, err_message = run_executable_insert(did, app_id, e.get('body'), params)
                    if err_message:
                        logging.debug(err_message)
                        return response_err(500, err_message)
        if executable.get('type') == SCRIPTING_EXECUTABLE_TYPE_FIND:
            data, err_message = run_executable_find(did, app_id, executable.get('body'), params)
            if err_message:
                logging.debug(err_message)
                return response_err(500, err_message)
        elif executable.get('type') == SCRIPTING_EXECUTABLE_TYPE_INSERT:
            data, err_message = run_executable_insert(did, app_id, executable.get('body'), params)
            if err_message:
                logging.debug(err_message)
                return response_err(500, err_message)

        return response_ok(data)

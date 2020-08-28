from bson import ObjectId
from pymongo import MongoClient

from datetime import datetime

from hive.main.interceptor import post_json_param_pre_proc
from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.constants import SCRIPTING_SUBCONDITION_COLLECTION, SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_EXECUTABLE_FIND_MANY, SCRIPTING_EXECUTABLE_FIND_ONE, DATETIME_FORMAT, \
    SCRIPTING_CONDITION_HAS_RESULTS, SCRIPTING_CONDITION_OP_SUB, SCRIPTING_CONDITION_OP_AND, SCRIPTING_CONDITION_OP_OR, \
    SCRIPTING_EXECUTABLE_INSERT_ONE
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import gene_mongo_db_name, \
    options_filter
from hive.util.did_scripting import run_executable_find, check_condition, run_executable_insert
from hive.util.server_response import response_ok, response_err


class HiveScripting:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app

    def __upsert_script_to_db(self, did, app_id, collection_name, content):
        connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
        db_name = gene_mongo_db_name(did, app_id)
        db = connection[db_name]
        if collection_name not in db.list_collection_names():
            try:
                col = db.create_collection(collection_name)
            except Exception as e:
                return None, response_err(500, "Exception:" + str(e))
        else:
            col = get_collection(did, app_id, collection_name)

        lookup = {
            "name": content.get("name")
        }
        content = {k: v for k, v in content.items() if k != 'name'}

        content["modified"] = datetime.utcnow()
        update = {
            "$set": content,
            "$setOnInsert": {
                "created": datetime.utcnow()
            }
        }
        options = {
            "upsert": True,
            "bypass_document_validation": False
        }
        try:
            ret = col.update_one(lookup, update, **options)
            data = {
                "acknowledged": ret.acknowledged,
                "matched_count": ret.matched_count,
                "modified_count": ret.modified_count,
                "upserted_id": str(ret.upserted_id),
            }
            return data, None
        except Exception as e:
            return None, response_err(500, "Exception:" + str(e))

    def set_subcondition(self):
        # Request Validation
        did, app_id, content, err = post_json_param_pre_proc("name", "condition")
        if err:
            return err

        # Data Validation
        condition_endpoint = content.get('condition').get('endpoint', None)
        if condition_endpoint is None:
            return response_err(400, "the parameter 'endpoint' must be set for 'condition'")

        # Create collection "subconditions" if it doesn't exist and
        # return response
        data, err = self.__upsert_script_to_db(did, app_id, SCRIPTING_SUBCONDITION_COLLECTION, content)
        if err:
            return err
        return response_ok(data)

    def set_script(self):
        # Request Validation
        did, app_id, content, err = post_json_param_pre_proc("name", "exec_sequence")
        if err:
            return err

        # Data Validation
        for executable in content.get('exec_sequence'):
            if executable.get('endpoint', None) is None:
                return response_err(400, "'endpoint' parameter for 'exec_sequence' is not set")

        # Create collection "scripts" if it doesn't exist and
        # return response
        data, err = self.__upsert_script_to_db(did, app_id, SCRIPTING_SCRIPT_COLLECTION, content)
        if err:
            return err
        return response_ok(data)

    def run_script(self):
        # Request Validation
        did, app_id, content, err = post_json_param_pre_proc("name")
        if err:
            return err

        # Find the script in the database
        col = get_collection(did, app_id, SCRIPTING_SCRIPT_COLLECTION)
        content_options = {
            "options": {
                "filter": {k: v for k, v in content.items() if k != 'params'}
            }
        }
        options = options_filter(content_options, ("filter",
                                                   "projection",
                                                   "skip",
                                                   "limit",
                                                   "sort",
                                                   "allow_partial_results",
                                                   "return_key",
                                                   "show_record_id",
                                                   "batch_size"))
        try:
            script = col.find_one(**options)
            if ("_id" in script) and (isinstance(script["_id"], ObjectId)):
                script["_id"] = str(script["_id"])
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

        # TODO: Execute the conditions
        params = content.get('params', None)
        condition = script.get("condition")
        if condition:
            # TODO: Verify this key exists in set_script later
            operation = condition.get('operation')
            total_passed = [True]
            if operation == SCRIPTING_CONDITION_OP_AND:
                for c in condition.get('conditions'):
                    passed = check_condition(did, app_id, c, params)
                    if not passed:
                        total_passed.append(False)
                        break
            elif operation == SCRIPTING_CONDITION_OP_OR:
                for i, c in enumerate(condition.get('conditions')):
                    passed = check_condition(did, app_id, c, params)
                    if passed:
                        total_passed.append(True)
                        break
                    else:
                        if i == len(condition.get('conditions') - 1):
                            total_passed.append(False)
            if False in total_passed:
                return response_err(403, "the conditions were not met to execute this script")

        # TODO: Run the executables in order and grab the result from the last executable
        exec_sequence = script.get("exec_sequence")
        data = {}
        for index, executable in enumerate(exec_sequence):
            endpoint = executable.get("endpoint")
            if endpoint == SCRIPTING_EXECUTABLE_FIND_MANY:
                data, err_message = run_executable_find(did, app_id, executable, params)
                if err_message:
                    return response_err(500, err_message)
            elif endpoint == SCRIPTING_EXECUTABLE_FIND_ONE:
                data, err_message = run_executable_find(did, app_id, executable, params, find_one=True)
                if err_message:
                    return response_err(500, err_message)
            elif endpoint == SCRIPTING_EXECUTABLE_INSERT_ONE:
                data, err_message = run_executable_insert(did, app_id, executable, params)
                if err_message:
                    return response_err(500, err_message)

        return response_ok(data)

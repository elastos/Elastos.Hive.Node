from bson import ObjectId
from pymongo import MongoClient

from hive.main.interceptor import post_json_param_pre_proc
from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.constants import SCRIPTING_SUBCONDITION_COLLECTION, SCRIPTING_SCRIPT_COLLECTION, \
    SCRIPTING_EXECUTABLE_FIND_MANY, SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_EXECUTABLE_FIND_ONE
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import gene_mongo_db_name, \
    options_filter, gene_sort
from hive.util.did_scripting import run_executable_find
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
        update = {
            "$set": content
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
        condition_type = content.get('condition').get('type', None)
        condition_collection = content.get('condition').get('collection', None)
        condition_query = content.get('condition').get('query', None)
        if (condition_type is None) or (condition_collection is None) or (condition_query is None):
            return response_err(400, "all the parameters for 'condition' are not set")

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
        content = {
            "options": {
                "filter": content
            }
        }
        options = options_filter(content, ("filter",
                                           "projection",
                                           "skip",
                                           "limit",
                                           "sort",
                                           "allow_partial_results",
                                           "return_key",
                                           "show_record_id",
                                           "batch_size"))
        print("options: ", options)
        try:
            script = col.find_one(**options)
            if ("_id" in script) and (isinstance(script["_id"], ObjectId)):
                script["_id"] = str(script["_id"])
            print("script: ", script["name"])
        except Exception as e:
            return response_err(500, "Exception:" + str(e))

        # TODO: Execute the conditions
        params = content.get('params', None)
        condition = script.get("condition")
        if condition:
            pass

        # TODO: Run the executables in order and grab the result from the last executable
        exec_sequence = script.get("exec_sequence")
        data = {}
        for index, executable in enumerate(exec_sequence):
            endpoint = executable.get("endpoint")
            if index == len(exec_sequence) - 1:
                if endpoint == SCRIPTING_EXECUTABLE_FIND_MANY:
                    data, err_message = run_executable_find(did, app_id, executable, params)
                    if err_message:
                        return response_err(500, err_message)
                elif endpoint == SCRIPTING_EXECUTABLE_FIND_ONE:
                    data, err_message = run_executable_find(did, app_id, executable, params, find_one=True)
                    if err_message:
                        return response_err(500, err_message)
            else:
                pass
                # run_script_from_db(did, app_id, db_name, executable, params)

        return response_ok(data)

import json

from flask import request

from hive.main.hive_sync import HiveSync
from hive.util.auth import did_auth
from hive.util.constants import SCRIPTING_SUBCONDITIONS_SCHEMA, \
    SCRIPTING_SUBCONDITION_COLLECTION, SCRIPTING_SCRIPT_COLLECTION, SCRIPTING_SCRIPTS_SCHEMA
from hive.util.did_mongo_db_resource import find_schema_of_did_resource, add_did_resource_to_db, gene_mongo_db_name
from hive.util.did_scripting import upsert_subcondition_to_db, upsert_script_to_db, find_script_from_db, \
    run_script_from_db
from hive.util.server_response import response_ok, response_err


class HiveScripting:
    def __init__(self, app=None):
        self.app = app

    def init_app(self, app):
        self.app = app

    def set_subcondition(self):
        # Request Validation
        did, app_id, content = self.get_content_after_validation()

        # Data Validation
        name = content.get('name', None)
        condition_type = content.get('condition_type', None)
        condition = content.get('condition', None)
        if (name is None) or (condition is None) or (condition_type is None):
            return response_err(400, "main parameters are not set")

        # Add the schema if it doesn't exist
        collection = SCRIPTING_SUBCONDITION_COLLECTION
        schema_db = find_schema_of_did_resource(did, app_id, collection)
        if schema_db is None:
            add_did_resource_to_db(did, app_id, collection, json.dumps(SCRIPTING_SUBCONDITIONS_SCHEMA["schema"]))

        # Insert/Update the data into the database
        db_name = gene_mongo_db_name(did, app_id)
        upsert_subcondition_to_db(did, app_id, db_name, collection, name, condition_type, condition)

        return response_ok({})

    def set_script(self):
        # Request Validation
        did, app_id, content = self.get_content_after_validation()

        # Data Validation
        name = content.get('name', None)
        exec_sequence = content.get('exec_sequence', None)
        if (name is None) or (exec_sequence is None):
            return response_err(400, "main parameters are not set")

        # Add the schema if it doesn't exist
        collection = SCRIPTING_SCRIPT_COLLECTION
        schema_db = find_schema_of_did_resource(did, app_id, collection)
        if schema_db is None:
            add_did_resource_to_db(did, app_id, collection, json.dumps(SCRIPTING_SCRIPTS_SCHEMA["schema"]))

        # Insert/Update the data into the database
        condition = content.get('condition', None)
        db_name = gene_mongo_db_name(did, app_id)
        upsert_script_to_db(did, app_id, db_name, collection, name, exec_sequence, condition)

        return response_ok({})

    def run_script(self):
        # Request Validation
        did, app_id, content = self.get_content_after_validation()

        # Data Validation
        script_name = content.get('name', None)
        if (script_name is None):
            return response_err(400, "main parameters are not set")

        # Find the script in the database
        db_name = gene_mongo_db_name(did, app_id)
        script = find_script_from_db(did, app_id, db_name, script_name)
        if script["error"]:
            return response_err(406, f"could not find the script '{script_name}'. Please register the script first")

        # TODO: Execute the conditions
        exec_sequence, condition = script["data"][0], script["data"][1]
        params = content.get('params', None)
        if condition:
            pass

        # TODO: Run the exec sequences
        data = {}
        for index, executable in enumerate(exec_sequence):
            if index == len(exec_sequence) - 1:
                data = run_script_from_db(did, app_id, db_name, executable, params)
            else:
                run_script_from_db(did, app_id, db_name, executable, params)

        return response_ok(data)

    def get_content_after_validation(self):
        did, app_id = did_auth()
        if (did is None) or (app_id is None):
            return response_err(401, "auth failed")

        if not HiveSync.is_app_sync_prepared(did, app_id):
            return response_err(406, "drive is not prepared")

        content = request.get_json(force=True, silent=True)
        if content is None:
            return response_err(400, "parameter is not application/json")
        return did, app_id, content

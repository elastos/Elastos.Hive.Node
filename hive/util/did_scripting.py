from pymongo import MongoClient

from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.constants import SCRIPTING_DID, SCRIPTING_APP_ID, SCRIPTING_NAME, SCRIPTING_CONDITION, \
    SCRIPTING_EXEC_SEQUENCE, SCRIPTING_SCRIPT_COLLECTION, SCRIPTING_EXECUTABLE_FIND_ONE, SCRIPTING_EXECUTABLE_FIND_MANY, \
    SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_CONDITION_TYPE


def upsert_subcondition_to_db(did, app_id, db_name, collection, name, condition_type, condition):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[db_name]
    col = db[collection]
    query = {SCRIPTING_DID: did, SCRIPTING_APP_ID: app_id, SCRIPTING_NAME: name}
    values = {"$set": {SCRIPTING_CONDITION: condition, SCRIPTING_CONDITION_TYPE: condition_type}}
    u = col.update_one(query, values, upsert=True)
    return u


def upsert_script_to_db(did, app_id, db_name, collection, name, exec_sequence, condition):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[db_name]
    col = db[collection]
    query = {SCRIPTING_DID: did, SCRIPTING_APP_ID: app_id, SCRIPTING_NAME: name}
    values = {"$set": {SCRIPTING_EXEC_SEQUENCE: exec_sequence, SCRIPTING_CONDITION: condition}}
    u = col.update_one(query, values, upsert=True)
    return u


def find_script_from_db(did, app_id, db_name, name):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[db_name]
    col = db[SCRIPTING_SCRIPT_COLLECTION]
    query = {SCRIPTING_DID: did, SCRIPTING_APP_ID: app_id, SCRIPTING_NAME: name}
    data = col.find_one(query)
    result = {
        "data": None,
        "error": None
    }
    if not data:
        result["error"] = "No script found"
    else:
        result["data"] = (data[SCRIPTING_EXEC_SEQUENCE], data[SCRIPTING_CONDITION])
    return result


def run_script_from_db(did, app_id, db_name, executable, params):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[db_name]
    col = db[executable["name"]]
    query = {SCRIPTING_DID: did, SCRIPTING_APP_ID: app_id}
    for key, value in executable["query"].items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[value] = did
        else:
            query[value] = params[key]
    endpoint = executable["endpoint"]
    projections = executable.get('options', {}).get('projection', None)
    print(query, projections)
    if endpoint == SCRIPTING_EXECUTABLE_FIND_ONE:
        data = {}
    elif endpoint == SCRIPTING_EXECUTABLE_FIND_MANY:
        data = col.find(query, projections)
    return data

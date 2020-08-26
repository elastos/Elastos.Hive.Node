from pymongo import MongoClient

from hive.settings import MONGO_HOST, MONGO_PORT
from hive.util.constants import SCRIPTING_DID, SCRIPTING_APP_ID, SCRIPTING_NAME, SCRIPTING_CONDITION, \
    SCRIPTING_EXEC_SEQUENCE, SCRIPTING_SCRIPT_COLLECTION


def upsert_subcondition_to_db(did, app_id, db_name, collection, name, condition):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[db_name]
    col = db[collection]
    query = {SCRIPTING_DID: did, SCRIPTING_APP_ID: app_id, SCRIPTING_NAME: name}
    values = {"$set": {SCRIPTING_CONDITION: condition}}
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

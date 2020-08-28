import logging
from datetime import datetime

from bson import ObjectId

from hive.util.constants import SCRIPTING_EXECUTABLE_CALLER_DID, SCRIPTING_SUBCONDITION_COLLECTION, \
    SCRIPTING_CONDITION_HAS_RESULTS, SCRIPTING_CONDITION_OP_SUB, SCRIPTING_CONDITION_OP_AND, SCRIPTING_CONDITION_OP_OR
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import options_filter, gene_sort


def check_condition(did, app_id, condition, params):
    col = get_collection(did, app_id, SCRIPTING_SUBCONDITION_COLLECTION)
    content_options = {
        "options": {
            "filter": {
                "name": condition.get('name')
            }
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
        subcondition = col.find_one(**options)
        if ("_id" in subcondition) and (isinstance(subcondition["_id"], ObjectId)):
            subcondition["_id"] = str(subcondition["_id"])
    except Exception as e:
        logging.debug("Exception: " + str(e))
        return False

    condition_script = subcondition.get('condition')
    if condition_script.get('endpoint') == SCRIPTING_CONDITION_HAS_RESULTS:
        data, err_message = run_executable_find(did, app_id, condition_script, params, find_one=True)
        if err_message:
            logging.debug(f"condition script '{subcondition.get('name')}' did not execute successfully")
            return False
    return True


def run_executable_find(did, app_id, executable, params, find_one=False):
    options = executable.get("options", None)
    if options:
        if options.get('filter', None) is not None:
            query = {}
            for key, value in options.get('filter').items():
                if key == SCRIPTING_EXECUTABLE_CALLER_DID:
                    v = {"$in": [did]}
                else:
                    v = params[key]
                if value == "_id":
                    query[value] = ObjectId(v)
                else:
                    query[value] = v
            executable["options"]["filter"] = query

    col = get_collection(did, app_id, executable.get('collection'))

    content = {k: v for k, v in executable.items() if k != 'endpoint'}
    options = options_filter(content, ("filter",
                                       "projection",
                                       "skip",
                                       "limit",
                                       "sort",
                                       "allow_partial_results",
                                       "return_key",
                                       "show_record_id",
                                       "batch_size"))
    if "sort" in options:
        sorts = gene_sort(options["sort"])
        options["sort"] = sorts

    try:
        if find_one:
            result = col.find_one(**options)
            if ("_id" in result) and (isinstance(result["_id"], ObjectId)):
                result["_id"] = str(result["_id"])
            data = {"items": result}
        else:
            result = col.find(**options)
            arr = list()
            for c in result:
                if ("_id" in c) and (isinstance(c["_id"], ObjectId)):
                    c["_id"] = str(c["_id"])
                arr.append(c)
            data = {"items": arr}
        return data, None
    except Exception as e:
        return None, "Exception: method: 'run_executable_find', " + str(e)


def run_executable_insert(did, app_id, executable, params):
    document = executable.get("document", None)
    if not document:
        return None, "Exception: method: 'run_executable_insert', parameter 'document' was not passed"

    query = {}
    for key, value in document.items():
        if key == SCRIPTING_EXECUTABLE_CALLER_DID:
            query[value] = did
        else:
            query[value] = params[key]
    document = query
    document["created"] = datetime.utcnow()
    document["modified"] = datetime.utcnow()

    options = executable.get("options", None)
    if options:
        options = options_filter(options, ("bypass_document_validation",))
    try:
        col = get_collection(did, app_id, executable.get('collection'))
        ret = col.insert_one(document, **options)

        data = {
            "acknowledged": ret.acknowledged,
            "inserted_id": str(ret.inserted_id)
        }
        return data, None
    except Exception as e:
        return None, "Exception: method: 'run_executable_insert', " + str(e)

from bson import ObjectId

from hive.util.constants import SCRIPTING_EXECUTABLE_CALLER_DID
from hive.util.did_info import get_collection
from hive.util.did_mongo_db_resource import options_filter, gene_sort


def run_executable_find(did, app_id, executable, params, find_one=False):
    options = executable.get("options", None)
    if options:
        if options.get('filter', None) is not None:
            query = {}
            for key, value in options.get('filter').items():
                if key == SCRIPTING_EXECUTABLE_CALLER_DID:
                    query[value] = {"$in": [did]}
                else:
                    query[value] = params[key]
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
        return None, "Exception:" + str(e)

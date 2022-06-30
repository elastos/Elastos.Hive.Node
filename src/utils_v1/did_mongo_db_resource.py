import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from bson import ObjectId, json_util
from pymongo import MongoClient

from src.settings import hive_setting
from src.utils.http_exception import BadRequestException
from src.utils_v1.common import did_tail_part


def create_db_client():
    """ Create the instance of the MongoClient by the setting MONGO_TYPE. """
    return MongoClient(hive_setting.MONGODB_URI)


def convert_oid(query, update=False):
    """ for v2: to make the following convert

        "group_id": {"$oid": "5f497bb83bd36ab235d82e6a"}

    to:

        "group_id": ObjectId("5f497bb83bd36ab235d82e6a")
    """
    new_query = {}
    for key, value in query.items():
        new_query[key] = value
        if isinstance(value, dict):
            if update:
                for k, v in value.items():
                    new_query[key][k] = v
                    if isinstance(v, dict):
                        if "$oid" in v.keys():
                            new_query[key][k] = ObjectId(v["$oid"])
            else:
                if "$oid" in value.keys():
                    new_query[key] = ObjectId(value["$oid"])
    return new_query


def options_filter(body, option_keys):
    """ filter options in options_keys from the "options" of body """
    if not body or not isinstance(body.get('options'), dict):
        return {}
    return {k: v for k, v in body.get('options').items() if k in option_keys}


def gene_sort(sorts_src):
    sorts = list()
    if isinstance(sorts_src, list):
        # same as mongodb
        sorts.extend(sorts_src)
    elif isinstance(sorts_src, dict):
        sorts.extend(sorts_src.items())
    return sorts


def populate_options_insert_one(content):
    options = options_filter(content, ("bypass_document_validation",))
    return options


def populate_options_update_one(content):
    options = options_filter(content, ("upsert", "bypass_document_validation"))
    return options


def query_update_one(col, content, options):
    try:
        update_set_on_insert = content.get('update').get('$setOnInsert', None)
        now = int(datetime.now().timestamp())
        if update_set_on_insert:
            content["update"]["$setOnInsert"]['created'] = now
        else:
            content["update"]["$setOnInsert"] = {
                "created": now
            }
        if "$set" in content["update"]:
            content["update"]["$set"]["modified"] = now
        ret = col.update_one(convert_oid(content["filter"]), convert_oid(content["update"], update=True), **options)
        data = {
            "acknowledged": ret.acknowledged,
            "matched_count": ret.matched_count,
            "modified_count": ret.modified_count,
            "upserted_id": str(ret.upserted_id),
        }
        return data, None
    except Exception as e:
        return None, f"Exception: method: 'query_update_one', Err: {str(e)}"


def populate_options_count_documents(content):
    options = options_filter(content, ("skip", "limit", "maxTimeMS"))
    return options


def query_count_documents(col, content, options):
    try:
        count = col.count_documents(convert_oid(content["filter"]), **options)
        data = {"count": count}
        return data, None
    except Exception as e:
        return None, f"Exception: method: 'query_count_documents', Err: {str(e)}"


def populate_find_options_from_body(body):
    options = options_filter(body, ("projection",
                                    "skip",
                                    "limit",
                                    "sort",
                                    "allow_partial_results",
                                    "return_key",
                                    "show_record_id",
                                    "batch_size"))
    if "sort" in options:
        options["sort"] = gene_sort(options["sort"])
    return options


def query_find_many(col, content, options):
    try:
        if "filter" in content:
            result = col.find(convert_oid(content["filter"]), **options)
        else:
            result = col.find(**options)
        arr = list()
        for c in json.loads(json_util.dumps(result)):
            arr.append(c)
        data = {"items": arr}
        return data, None
    except Exception as e:
        return None, f"Exception: method: 'query_find_many', Err: {str(e)}"


def query_delete_one(col, content):
    try:
        result = col.delete_one(convert_oid(content["filter"]))
        data = {
            "acknowledged": result.acknowledged,
            "deleted_count": result.deleted_count,
        }
        return data, None
    except Exception as e:
        return None, f"Exception: method: 'query_delete_one', Err: {str(e)}"


def gene_mongo_db_name(did, app_did):
    md5 = hashlib.md5()
    md5.update((did + "_" + app_did).encode("utf-8"))
    return get_user_database_prefix() + str(md5.hexdigest())


def get_user_database_prefix():
    return 'hive_user_db_' if not hive_setting.ATLAS_ENABLED else 'hu_'


def get_collection(did, app_did, collection):
    connection = create_db_client()
    db_name = gene_mongo_db_name(did, app_did)
    db = connection[db_name]
    if collection not in db.list_collection_names():
        return None
    col = db[collection]
    return col


def delete_mongo_database(did, app_did):
    connection = create_db_client()
    db_name = gene_mongo_db_name(did, app_did)
    connection.drop_database(db_name)


def get_save_mongo_db_path(did):
    path = Path(hive_setting.VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did) / "mongo_db"
    else:
        path = path.resolve() / did_tail_part(did) / "mongo_db"
    return path.resolve()


def dump_mongodb_to_full_path(db_name, full_path: Path):
    try:
        line2 = f'mongodump --uri="{hive_setting.MONGODB_URI}" -d {db_name} --archive="{full_path.as_posix()}"'
        subprocess.check_output(line2, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise BadRequestException(f'Failed to dump database {db_name}: {e.output}')


def restore_mongodb_from_full_path(full_path: Path):
    if not full_path.exists():
        raise BadRequestException(f'Failed to import mongo db by invalid full dir {full_path.as_posix()}')

    try:
        # https://www.mongodb.com/docs/database-tools/mongorestore/#cmdoption--drop
        # --drop: drop collections before restore, but does not drop collections that are not in the backup.
        line2 = f'mongorestore --uri="{hive_setting.MONGODB_URI}" --drop --archive="{full_path.as_posix()}"'
        subprocess.check_output(line2, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise BadRequestException(f'Failed to load database by {full_path.as_posix()}: {e.output}')


def delete_mongo_db_export(did):
    save_path = get_save_mongo_db_path(did)
    if save_path.exists():
        shutil.rmtree(save_path)

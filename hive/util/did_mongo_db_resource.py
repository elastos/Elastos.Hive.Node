import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from bson import ObjectId, json_util
from pymongo import MongoClient

from hive.settings import hive_setting
from hive.util.constants import DATETIME_FORMAT, DID, APP_ID
from hive.util.common import did_tail_part, create_full_path_dir


def convert_oid(query, update=False):
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


def options_filter(content, args):
    ops = dict()
    if "options" not in content:
        return ops
    options = content["options"]
    for arg in args:
        if arg in options:
            ops[arg] = options[arg]
    return ops


def gene_sort(sort_para):
    sorts = list()
    if isinstance(sort_para, list):
        for sort in sort_para:
            for field in sort.keys():
                sorts.append((field, sort[field]))
    elif isinstance(sort_para, dict):
        for field in sort_para.keys():
            sorts.append((field, sort_para[field]))
    return sorts


def populate_options_insert_one(content):
    options = options_filter(content, ("bypass_document_validation",))
    return options


def query_insert_one(col, content, options, created=False):
    try:
        if created:
            content["document"]["created"] = datetime.strptime(content["document"]["created"], DATETIME_FORMAT)
        else:
            content["document"]["created"] = datetime.utcnow()
        content["document"]["modified"] = datetime.utcnow()
        ret = col.insert_one(convert_oid(content["document"]), **options)

        data = {
            "acknowledged": ret.acknowledged,
            "inserted_id": str(ret.inserted_id)
        }
        return data, None
    except Exception as e:
        return None, f"Exception: method: 'query_insert_one', Err: {str(e)}"


def populate_options_update_one(content):
    options = options_filter(content, ("upsert", "bypass_document_validation"))
    return options


def query_update_one(col, content, options):
    try:
        update_set_on_insert = content.get('update').get('$setOnInsert', None)
        if update_set_on_insert:
            content["update"]["$setOnInsert"]['created'] = datetime.utcnow()
        else:
            content["update"]["$setOnInsert"] = {
                "created": datetime.utcnow()
            }
        if "$set" in content["update"]:
            content["update"]["$set"]["modified"] = datetime.utcnow()
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


def populate_options_find_many(content):
    options = options_filter(content, ("projection",
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


def gene_mongo_db_name(did, app_id):
    md5 = hashlib.md5()
    md5.update((did + "_" + app_id).encode("utf-8"))
    return "hive_user_db_" + str(md5.hexdigest())


def get_collection(did, app_id, collection):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db_name = gene_mongo_db_name(did, app_id)
    db = connection[db_name]
    if collection not in db.list_collection_names():
        return None
    col = db[collection]
    return col


def delete_mongo_database(did, app_id):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db_name = gene_mongo_db_name(did, app_id)
    connection.drop_database(db_name)


def get_mongo_database_size(user_did, app_did):
    """ for database usage size updating """
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    # get user's database
    db_name = gene_mongo_db_name(user_did, app_did)
    if db_name not in connection.list_database_names():
        # user's database not exists
        return 0.0
    db = connection[db_name]

    # count by state: https://www.mongodb.com/docs/v4.4/reference/command/dbStats/
    return int(db.command('dbstats')['totalSize'])


def get_save_mongo_db_path(did):
    path = Path(hive_setting.VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did) / "mongo_db"
    else:
        path = path.resolve() / did_tail_part(did) / "mongo_db"
    return path.resolve()


def export_mongo_db(did, app_id):
    save_path = get_save_mongo_db_path(did)
    if not save_path.exists():
        if not create_full_path_dir(save_path):
            return False
    db_name = gene_mongo_db_name(did, app_id)
    line2 = 'mongodump --uri "%s" -d %s -o %s' % (hive_setting.MONGODB_URI, db_name, save_path)
    subprocess.call(line2, shell=True)
    return True


def import_mongo_db(did):
    save_path = get_save_mongo_db_path(did)
    if not save_path.exists():
        return False
    line2 = 'mongorestore --uri "%s" --drop %s' % (hive_setting.MONGODB_URI, save_path)
    subprocess.call(line2, shell=True)
    return True


def delete_mongo_db_export(did):
    save_path = get_save_mongo_db_path(did)
    if save_path.exists():
        shutil.rmtree(save_path)

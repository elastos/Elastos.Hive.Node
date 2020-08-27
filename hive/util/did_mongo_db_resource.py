import hashlib
import json
import subprocess
from pathlib import Path

import pymongo
from pymongo import MongoClient

from hive.settings import DID_BASE_DIR, MONGO_HOST, MONGO_PORT
from hive.util.constants import DID_INFO_DB_NAME, DID_RESOURCE_COL, DID_RESOURCE_NAME, DID_RESOURCE_SCHEMA, \
    DID_RESOURCE_DID, DID_RESOURCE_APP_ID
from hive.util.common import did_tail_part, create_full_path_dir


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
    for field in sort_para.keys():
        if "desc" == sort_para[field]:
            sorts.append((field, pymongo.DESCENDING))
        else:
            sorts.append((field, pymongo.ASCENDING))
    return sorts


# settings must be json string
def add_did_resource_to_db(did, app_id, resource, schema):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]

    did_dic = {DID_RESOURCE_DID: did, DID_RESOURCE_APP_ID: app_id, DID_RESOURCE_NAME: resource,
               DID_RESOURCE_SCHEMA: schema}
    i = col.insert_one(did_dic)
    return i


def update_schema_of_did_resource(did, app_id, resource, schema):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]

    query = {DID_RESOURCE_DID: did, DID_RESOURCE_APP_ID: app_id, DID_RESOURCE_NAME: resource}
    values = {"$set": {DID_RESOURCE_SCHEMA, schema}}
    r = col.update_one(query, values)
    return r


def find_schema_of_did_resource(did, app_id, resource):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]
    query = {DID_RESOURCE_DID: did, DID_RESOURCE_APP_ID: app_id, DID_RESOURCE_NAME: resource}
    data = col.find_one(query)
    if data is None:
        return None
    else:
        return data[DID_RESOURCE_SCHEMA]


def get_all_resource_of_did_app_id(did, app_id):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]
    query = {DID_RESOURCE_DID: did, DID_RESOURCE_APP_ID: app_id}
    resource_list = col.find(query)
    return resource_list


def delete_did_resource_from_db(did, app_id, resource):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_RESOURCE_COL]
    query = {DID_RESOURCE_DID: did, DID_RESOURCE_APP_ID: app_id, DID_RESOURCE_NAME: resource}
    data = col.delete_one(query)
    return data


def gene_mongo_db_name(did, app_id):
    md5 = hashlib.md5()
    md5.update((did + "_" + app_id).encode("utf-8"))
    return "hive_user_db_" + str(md5.hexdigest())


def get_save_mongo_db_path(did, app_id):
    path = Path(DID_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did) / app_id / "mongo_db"
    else:
        path = path.resolve() / did_tail_part(did) / app_id / "mongo_db"
    return path.resolve()


def export_mongo_db(did, app_id):
    save_path = get_save_mongo_db_path(did, app_id)
    if not save_path.exists():
        if not create_full_path_dir(save_path):
            return False

    query = {DID_RESOURCE_DID: did, DID_RESOURCE_APP_ID: app_id}
    # 1. export collection schema data
    line1 = "mongoexport -h %s --port %s  --db=%s --collection=%s -q '%s' -o %s" % (MONGO_HOST,
                                                                                    MONGO_PORT,
                                                                                    DID_INFO_DB_NAME,
                                                                                    DID_RESOURCE_COL,
                                                                                    json.dumps(query),
                                                                                    save_path / DID_RESOURCE_COL)
    subprocess.call(line1, shell=True)

    # 2. dump user data db
    db_name = gene_mongo_db_name(did, app_id)
    line2 = 'mongodump -h %s --port %s  -d %s -o %s' % (MONGO_HOST, MONGO_PORT, db_name, save_path)
    subprocess.call(line2, shell=True)
    return True


def import_mongo_db(did, app_id):
    path = get_save_mongo_db_path(did, app_id)
    if not path.exists():
        return False

    # 1. import collection schema data
    line1 = "mongoimport -h %s --port %s  --db=%s --collection=%s --upsert %s" % (MONGO_HOST,
                                                                                  MONGO_PORT,
                                                                                  DID_INFO_DB_NAME,
                                                                                  DID_RESOURCE_COL,
                                                                                  path / DID_RESOURCE_COL)

    subprocess.call(line1, shell=True)
    # 2. restore user data db
    db_name = gene_mongo_db_name(did, app_id)
    save_path = path / db_name
    line2 = 'mongorestore -h %s --port %s  -d %s --drop %s' % (MONGO_HOST, MONGO_PORT, db_name, save_path)
    subprocess.call(line2, shell=True)
    return True

# if __name__ == '__main__':
#     did_str = "did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6quumnym"
#     app_id = "did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6quumnym"
#     export_mongo_db(did_str, app_id)
#     import_mongo_db(did_str, app_id)

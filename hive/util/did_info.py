import uuid

from pymongo import MongoClient

from hive.util.constants import DID_INFO_DB_NAME, DID_INFO_REGISTER_COL, DID, APP_ID, DID_INFO_NONCE, DID_INFO_TOKEN, \
    DID_INFO_NONCE_EXPIRED, DID_INFO_TOKEN_EXPIRED, APP_INSTANCE_DID
from hive.settings import hive_setting
from hive.util.did_mongo_db_resource import gene_mongo_db_name


def add_did_nonce_to_db(app_instance_did, nonce, expired):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    did_dic = {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce, DID_INFO_NONCE_EXPIRED: expired}
    i = col.insert_one(did_dic)
    return i

# def add_did_info_to_db(did, app_id, nonce, token, expire):
#     if hive_setting.MONGO_USER:
#         uri = f'mongodb://{hive_setting.MONGO_USER}:{hive_setting.MONGO_PASSWORD}@{hive_setting.MONGO_HOST}:{hive_setting.MONGO_PORT}/'
#         connection = MongoClient(uri)
#     else:
#         connection = MongoClient(host=hive_setting.MONGO_HOST, port=hive_setting.MONGO_PORT)
#     db = connection[DID_INFO_DB_NAME]
#     col = db[DID_INFO_REGISTER_COL]
#     did_dic = {DID: did, APP_ID: app_id, DID_INFO_NONCE: nonce, DID_INFO_TOKEN: token, DID_INFO_NONCE_EXPIRED: expire}
#     i = col.insert_one(did_dic)
#     return i

def update_nonce_of_did_info(app_instance_did, nonce, expired):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_NONCE: nonce}
    value = {"$set": {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce, DID_INFO_NONCE_EXPIRED: expired}}
    ret = col.update_one(query, value)
    return ret

def update_did_info_by_app_instance_did(app_instance_did, nonce, expired):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {APP_INSTANCE_DID: app_instance_did}
    value = {"$set": {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce, DID_INFO_NONCE_EXPIRED: expired}}
    ret = col.update_one(query, value)
    return ret

def update_token_of_did_info(did, app_id, app_instance_did, nonce, token, expired):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce}
    value = {"$set": {DID: did, APP_ID: app_id, DID_INFO_TOKEN: token, DID_INFO_TOKEN_EXPIRED: expired}}
    ret = col.update_one(query, value)
    return ret


def get_all_did_info():
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    infos = col.find()
    return infos


def delete_did_info(did, app_id):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did, APP_ID: app_id}
    col.delete_many(query)


def get_all_did_info_by_did(did):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did}
    infos = col.find(query)
    return infos


def get_all_app_dids(user_did: str) -> list[str]:
    """ only for batch 'count_vault_storage_job'

    Same as v2: UserManager.get_all_app_dids()
    """
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]

    # INFO: Must check the existence of some fields
    filter_ = {
        APP_ID: {'$exists': True},
        '$and': [{DID: {'$exists': True}}, {DID: user_did}]
    }

    docs = col.find_many(filter_)
    return list(set(map(lambda d: d[APP_ID], docs)))


def get_did_info_by_nonce(nonce):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_NONCE: nonce}
    info = col.find_one(query)
    return info

def get_did_info_by_app_instance_did(app_instance_did):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {APP_INSTANCE_DID: app_instance_did}
    info = col.find_one(query)
    return info

def get_did_info_by_did_appid(did, app_id):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did, APP_ID: app_id}
    info = col.find_one(query)
    return info


def save_token_to_db(did, app_id, token, expired):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did, APP_ID: app_id}
    value = {"$set": {
        DID_INFO_TOKEN: token,
        DID_INFO_TOKEN_EXPIRED: expired,
        DID_INFO_NONCE: None,
        DID_INFO_NONCE_EXPIRED: None}}
    ret = col.update_one(query, value)
    return ret


def get_did_info_by_token(token):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_TOKEN: token}
    info = col.find_one(query)
    return info

def get_collection(did, app_id, collection):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)
    db_name = gene_mongo_db_name(did, app_id)
    db = connection[db_name]
    col = db[collection]
    return col

def create_token():
    token = uuid.uuid1()
    return str(token)


def create_nonce():
    nonce = uuid.uuid1()
    return str(nonce)

import uuid

from pymongo import MongoClient

from hive.util.constants import DID_INFO_DB_NAME, DID_INFO_REGISTER_COL, DID, APP_ID, DID_INFO_NONCE, DID_INFO_TOKEN, \
    DID_INFO_NONCE_EXPIRED, DID_INFO_TOKEN_EXPIRED, APP_INSTANCE_DID
from hive.settings import MONGO_HOST, MONGO_PORT


def add_did_nonce_to_db(app_instance_did, nonce, expired):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    did_dic = {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce, DID_INFO_NONCE_EXPIRED: expired}
    i = col.insert_one(did_dic)
    return i

# def add_did_info_to_db(did, app_id, nonce, token, expire):
#     connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
#     db = connection[DID_INFO_DB_NAME]
#     col = db[DID_INFO_REGISTER_COL]
#     did_dic = {DID: did, APP_ID: app_id, DID_INFO_NONCE: nonce, DID_INFO_TOKEN: token, DID_INFO_NONCE_EXPIRED: expire}
#     i = col.insert_one(did_dic)
#     return i

def update_nonce_of_did_info(app_instance_did, nonce, expired):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_NONCE: nonce}
    value = {"$set": {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce, DID_INFO_NONCE_EXPIRED: expired}}
    ret = col.update_one(query, value)
    return ret

def update_did_info_by_app_instance_did(app_instance_did, nonce, expired):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {APP_INSTANCE_DID: app_instance_did}
    value = {"$set": {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce, DID_INFO_NONCE_EXPIRED: expired}}
    ret = col.update_one(query, value)
    return ret

def update_token_of_did_info(did, app_id, app_instance_did, nonce, token, expired):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce}
    value = {"$set": {DID: did, APP_ID: app_id, DID_INFO_TOKEN: token, DID_INFO_TOKEN_EXPIRED: expired}}
    ret = col.update_one(query, value)
    return ret


def get_all_did_info():
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    infos = col.find()
    return infos


def delete_did_info(did, app_id):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did, APP_ID: app_id}
    col.delete_many(query)


def get_all_did_info_by_did(did):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did}
    infos = col.find(query)
    return infos


def get_did_info_by_nonce(nonce):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_NONCE: nonce}
    info = col.find_one(query)
    return info

def get_did_info_by_app_instance_did(app_instance_did):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {APP_INSTANCE_DID: app_instance_did}
    info = col.find_one(query)
    return info

def get_did_info_by_did_appid(did, app_id):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did, APP_ID: app_id}
    info = col.find_one(query)
    return info


def save_token_to_db(did, app_id, token, expired):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
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
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_TOKEN: token}
    info = col.find_one(query)
    return info

def get_collection(did, app_id, collection):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
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

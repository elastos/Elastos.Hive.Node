import uuid

from pymongo import MongoClient

from hive.util.constants import DID_INFO_DB_NAME, DID_INFO_REGISTER_COL, DID, APP_ID, DID_INFO_NONCE, DID_INFO_TOKEN, \
    DID_INFO_NONCE_EXPIRE, DID_INFO_TOKEN_EXPIRE


def add_did_info_to_db(did, app_id, nonce, token, expire):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    did_dic = {DID: did, APP_ID: app_id, DID_INFO_NONCE: nonce, DID_INFO_TOKEN: token, DID_INFO_NONCE_EXPIRE: expire}
    i = col.insert_one(did_dic)
    return i


def update_nonce_of_did_info(did, app_id, nonce, token, expire):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did, APP_ID: app_id}
    value = {"$set": {DID_INFO_NONCE: nonce, DID_INFO_TOKEN: token, DID_INFO_NONCE_EXPIRE: expire}}
    ret = col.update_one(query, value)
    return ret


def get_all_did_info():
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    infos = col.find()
    return infos


def get_all_did_info_by_did(did):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did}
    infos = col.find(query)
    return infos


def get_did_info_by_nonce(nonce):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_NONCE: nonce}
    info = col.find_one(query)
    return info


def get_did_info_by_did_appid(did, app_id):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did, APP_ID: app_id}
    info = col.find_one(query)
    return info


def save_token_to_db(did, app_id, token, expire):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID: did, APP_ID: app_id}
    value = {"$set": {
        DID_INFO_TOKEN: token,
        DID_INFO_TOKEN_EXPIRE: expire,
        DID_INFO_NONCE: None,
        DID_INFO_NONCE_EXPIRE: None}}
    ret = col.update_one(query, value)
    return ret


def get_did_info_by_token(token):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_TOKEN: token}
    info = col.find_one(query)
    return info


def create_token():
    token = uuid.uuid1()
    return str(token)


def create_nonce():
    nonce = uuid.uuid1()
    return str(nonce)

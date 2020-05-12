import uuid

from pymongo import MongoClient

from hive.util.constants import DID_INFO_DB_NAME, DID_INFO_REGISTER_COL, DID_INFO_REGISTER_PASSWORD, DID_INFO_REGISTER_TOKEN


def save_did_info_to_db(did, password):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    did_dic = {"_id": did, DID_INFO_REGISTER_PASSWORD: password, DID_INFO_REGISTER_TOKEN: None}
    i = col.insert_one(did_dic)
    return i


def get_did_info_by_did(did):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {"_id": did}
    info = col.find_one(query)
    return info


def save_token_to_db(did, token):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {"_id": did}
    value = {"$set": {DID_INFO_REGISTER_TOKEN: token}}
    ret = col.update_one(query, value)
    return ret


def get_did_info_by_token(token):
    connection = MongoClient()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_REGISTER_TOKEN: token}
    info = col.find_one(query)
    return info


def create_token():
    token = uuid.uuid1()
    return str(token)
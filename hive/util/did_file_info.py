from datetime import datetime

from bson import ObjectId
from pymongo import MongoClient

from hive.util.constants import FILE_INFO_DB_NAME, FILE_INFO_COL, FILE_INFO_BELONG_DID, FILE_INFO_BELONG_APP_ID, \
    FILE_INFO_FILE_NAME, FILE_INFO_FILE_SIZE, FILE_INFO_FILE_CREATE_TIME, FILE_INFO_FILE_MODIFY_TIME


def add_file_info(did, app_id, name, info_dic):
    connection = MongoClient()
    db = connection[FILE_INFO_DB_NAME]
    col = db[FILE_INFO_COL]

    base_dic = {FILE_INFO_BELONG_DID: did,
                FILE_INFO_BELONG_APP_ID: app_id,
                FILE_INFO_FILE_NAME: name,
                FILE_INFO_FILE_CREATE_TIME: datetime.now().timestamp(),
                FILE_INFO_FILE_MODIFY_TIME: datetime.now().timestamp()
                }

    did_dic = dict(base_dic, **info_dic)
    i = col.insert_one(did_dic)
    return i


def update_file_size(did, app_id, name, size):
    connection = MongoClient()
    db = connection[FILE_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {FILE_INFO_BELONG_DID: did, FILE_INFO_BELONG_APP_ID: app_id, FILE_INFO_FILE_NAME: name}
    value = {"$set": {FILE_INFO_FILE_SIZE: size, FILE_INFO_FILE_MODIFY_TIME: datetime.now().timestamp()}}
    ret = col.update_one(query, value)
    return ret


def update_file_info(did, app_id, name, info_dic):
    connection = MongoClient()
    db = connection[FILE_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {FILE_INFO_BELONG_DID: did, FILE_INFO_BELONG_APP_ID: app_id, FILE_INFO_FILE_NAME: name}
    info_dic[FILE_INFO_FILE_MODIFY_TIME] = datetime.now().timestamp()
    value = {"$set": info_dic}
    ret = col.update_one(query, value)
    return ret


def remove_file_info(did, app_id, name):
    connection = MongoClient()
    db = connection[FILE_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {FILE_INFO_BELONG_DID: did, FILE_INFO_BELONG_APP_ID: app_id, FILE_INFO_FILE_NAME: name}
    ret = col.delete_one(query)
    return ret


def get_file_info(did, app_id, name):
    connection = MongoClient()
    db = connection[FILE_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {FILE_INFO_BELONG_DID: did, FILE_INFO_BELONG_APP_ID: app_id, FILE_INFO_FILE_NAME: name}
    info = col.find_one(query)
    return info


def get_file_info_by_id(file_id):
    connection = MongoClient()
    db = connection[FILE_INFO_DB_NAME]
    col = db[FILE_INFO_COL]
    query = {"_id": ObjectId(file_id)}
    info = col.find_one(query)
    return info

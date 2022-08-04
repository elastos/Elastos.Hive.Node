from pymongo import MongoClient

from hive.util.constants import DID, DID_INFO_DB_NAME, DID_SYNC_INFO_COL, DID_SYNC_INFO_STATE, DID_SYNC_INFO_MSG, \
    DID_SYNC_INFO_TIME, DID_SYNC_INFO_DRIVE
from hive.settings import hive_setting

DATA_SYNC_STATE_NONE = "none"
DATA_SYNC_STATE_INIT = "init"
DATA_SYNC_STATE_RUNNING = "running"
DATA_SYNC_STATE_STOP = "stop"

DATA_SYNC_MSG_INIT_SYNC = "init sync"
DATA_SYNC_MSG_INIT_MONGODB = "init mongodb"
DATA_SYNC_MSG_SYNCING = "syncing"
DATA_SYNC_MSG_SUCCESS = "success"
DATA_SYNC_MSG_FAILED = "failed"


def add_did_sync_info(did, time, drive):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URL)

    db = connection[DID_INFO_DB_NAME]
    col = db[DID_SYNC_INFO_COL]
    did_dic = {DID: did, DID_SYNC_INFO_STATE: DATA_SYNC_STATE_NONE,
               DID_SYNC_INFO_MSG: DATA_SYNC_STATE_NONE,
               DID_SYNC_INFO_TIME: time, DID_SYNC_INFO_DRIVE: drive}
    i = col.insert_one(did_dic)
    return i


def update_did_sync_info(did, state, info, sync_time, drive):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URL)

    db = connection[DID_INFO_DB_NAME]
    col = db[DID_SYNC_INFO_COL]
    query = {DID: did}
    value = {"$set": {DID_SYNC_INFO_STATE: state, DID_SYNC_INFO_MSG: info,
                      DID_SYNC_INFO_TIME: sync_time, DID_SYNC_INFO_DRIVE: drive}}
    ret = col.update_one(query, value)
    return ret


def delete_did_sync_info(did):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URL)

    db = connection[DID_INFO_DB_NAME]
    col = db[DID_SYNC_INFO_COL]
    query = {DID: did}
    col.delete_many(query)


def get_did_sync_info(did):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URL)

    db = connection[DID_INFO_DB_NAME]
    col = db[DID_SYNC_INFO_COL]
    query = {DID: did}
    info = col.find_one(query)
    return info


def get_all_did_sync_info():
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URL)

    db = connection[DID_INFO_DB_NAME]
    col = db[DID_SYNC_INFO_COL]
    infos = col.find()
    return infos

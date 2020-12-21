from datetime import datetime

from pymongo import MongoClient

from hive.util.constants import DID, DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, VAULT_BACKUP_INFO_STATE, \
    VAULT_BACKUP_INFO_MSG, VAULT_BACKUP_INFO_TIME, VAULT_BACKUP_INFO_DRIVE, VAULT_BACKUP_INFO_TYPE, \
    VAULT_BACKUP_INFO_DATA

from hive.settings import MONGO_HOST, MONGO_PORT

VAULT_BACKUP_STATE_RESTORE = "restore"
VAULT_BACKUP_STATE_BACKUP = "backup"
VAULT_BACKUP_STATE_STOP = "stop"

VAULT_BACKUP_MSG_SUCCESS = "success"
VAULT_BACKUP_MSG_FAILED = "failed"


def upsert_vault_backup_info(did, backup_type, drive, data=None):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_INFO_COL]
    query = {DID: did}
    did_dic = {"$set": {DID: did, VAULT_BACKUP_INFO_STATE: VAULT_BACKUP_STATE_STOP,
                        VAULT_BACKUP_INFO_TYPE: backup_type,
                        VAULT_BACKUP_INFO_MSG: VAULT_BACKUP_MSG_SUCCESS,
                        VAULT_BACKUP_INFO_TIME: datetime.utcnow(),
                        VAULT_BACKUP_INFO_DRIVE: drive,
                        VAULT_BACKUP_INFO_DATA: data
                        }}
    ret = col.update_one(query, did_dic, upsert=True)
    return ret.upserted_id


def update_vault_backup_state(did, state, msg):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_INFO_COL]
    query = {DID: did}
    value = {"$set": {VAULT_BACKUP_INFO_STATE: state, VAULT_BACKUP_INFO_MSG: msg,
                      VAULT_BACKUP_INFO_TIME: datetime.utcnow()}}
    ret = col.update_one(query, value)
    return ret


def delete_vault_backup_info(did):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_INFO_COL]
    query = {DID: did}
    col.delete_many(query)


def get_vault_backup_info(did):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_INFO_COL]
    query = {DID: did}
    info = col.find_one(query)
    return info

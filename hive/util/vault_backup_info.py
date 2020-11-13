from datetime import datetime

from pymongo import MongoClient

from hive.util.constants import DID, DID_INFO_DB_NAME, VAULT_BACKUP_INFO_COL, VAULT_BACKUP_INFO_STATE, \
    VAULT_BACKUP_INFO_MSG, VAULT_BACKUP_INFO_TIME, VAULT_BACKUP_INFO_DRIVE

from hive.settings import MONGO_HOST, MONGO_PORT

VAULT_BACKUP_STATE_RESTORE = "restore"
VAULT_BACKUP_STATE_BACKUP = "backup"
VAULT_BACKUP_STATE_STOP = "stop"

VAULT_BACKUP_MSG_SUCCESS = "success"
VAULT_BACKUP_MSG_FAILED = "failed"


def add_vault_backup_info(did, drive):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_INFO_COL]
    did_dic = {DID: did, VAULT_BACKUP_INFO_STATE: VAULT_BACKUP_STATE_STOP,
               VAULT_BACKUP_INFO_MSG: VAULT_BACKUP_MSG_SUCCESS,
               VAULT_BACKUP_INFO_TIME: datetime.utcnow(), VAULT_BACKUP_INFO_DRIVE: drive}
    i = col.insert_one(did_dic)
    return i


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



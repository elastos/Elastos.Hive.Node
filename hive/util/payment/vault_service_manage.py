import os
import shutil
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient

from hive.settings import MONGO_HOST, MONGO_PORT, VAULTS_BASE_DIR
from hive.util.common import did_tail_part
from hive.util.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, \
    VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, VAULT_SERVICE_DELETE_TIME, \
    VAULT_SERVICE_EXPIRE_READ, VAULT_SERVICE_STATE, VAULT_ACCESS_WR, VAULT_ACCESS_R, DID, APP_ID, \
    VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, VAULT_SERVICE_MODIFY_TIME, VAULT_STORAGE_FILE

from hive.util.did_file_info import get_dir_size
from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import delete_mongo_database, get_mongo_database_size

VAULT_SERVICE_STATE_RUNNING = "running"
VAULT_SERVICE_STATE_EXPIRE = "expire"
VAULT_SERVICE_STATE_DELETE = "delete"


def setup_vault_service(did, max_storage, delete_expire_days, can_read_expire, service_days):
    # If there has a service, we just update it. complex process latter
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    now = datetime.utcnow().timestamp()
    end_time = now + service_days * 24 * 60 * 60
    delete_time = end_time + delete_expire_days * 24 * 60 * 60

    dic = {VAULT_SERVICE_DID: did,
           VAULT_SERVICE_MAX_STORAGE: max_storage,
           VAULT_SERVICE_FILE_USE_STORAGE: 0.0,
           VAULT_SERVICE_DB_USE_STORAGE: 0.0,
           VAULT_SERVICE_START_TIME: now,
           VAULT_SERVICE_END_TIME: end_time,
           VAULT_SERVICE_DELETE_TIME: delete_time,
           VAULT_SERVICE_EXPIRE_READ: can_read_expire,
           VAULT_SERVICE_MODIFY_TIME: now,
           VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING
           }

    query = {VAULT_SERVICE_DID: did}
    value = {"$set": dic}
    ret = col.update_one(query, value, upsert=True)
    return ret


def get_vault_service(did):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: did}
    service = col.find_one(query)
    return service


def can_write_read(did):
    info = get_vault_service(did)
    if not info:
        return False
    if info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_RUNNING:
        return True
    else:
        return False


def can_read(did):
    info = get_vault_service(did)
    if not info:
        return False
    if info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_RUNNING:
        return True
    elif (info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_EXPIRE) and (info[VAULT_SERVICE_EXPIRE_READ]):
        return True
    else:
        return False


def can_access_vault(did, access_vault):
    if access_vault == VAULT_ACCESS_WR:
        if can_write_read(did):
            return True
        else:
            return False
    elif access_vault == VAULT_ACCESS_R:
        if can_read(did):
            return True
        else:
            return False
    else:
        return False


def get_vault_path(did):
    path = Path(VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did)
    else:
        path = path.resolve() / did_tail_part(did)
    return path.resolve()


def delete_user_vault(did):
    path = get_vault_path(did)
    if path.exists():
        shutil.rmtree(path)


def proc_delete_vault_job():
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_EXPIRE}
    info_list = col.find(query)

    now = datetime.utcnow().timestamp()
    for service in info_list:
        if now > service[VAULT_SERVICE_DELETE_TIME]:
            delete_db_storage(service[VAULT_SERVICE_DID])
            delete_user_vault(service[VAULT_SERVICE_DID])
            query_id = {"_id": service["_id"]}
            value = {"$set": {VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_DELETE,
                              VAULT_SERVICE_FILE_USE_STORAGE: 0.0,
                              VAULT_SERVICE_DB_USE_STORAGE: 0.0,
                              VAULT_SERVICE_MODIFY_TIME: now
                              }}
            col.update_one(query_id, value)


def proc_expire_vault_job():
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING}
    info_list = col.find(query)
    now = datetime.utcnow().timestamp()
    for service in info_list:
        if now > service[VAULT_SERVICE_END_TIME]:
            query_id = {"_id": service["_id"]}
            value = {"$set": {VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_EXPIRE,
                              VAULT_SERVICE_MODIFY_TIME: now
                              }}
            col.update_one(query_id, value)


def count_file_system_storage_size(did):
    vault_path = get_vault_path(did)
    storage_size = 0.0
    storage_size_mb = get_dir_size(vault_path.as_posix(), storage_size)
    return storage_size_mb


def count_db_storage_size(did):
    did_info_list = get_all_did_info_by_did(did)
    total_size = 0.0
    for did_info in did_info_list:
        total_size += get_mongo_database_size(did_info[DID], did_info[APP_ID])
    return total_size


def delete_db_storage(did):
    did_info_list = get_all_did_info_by_did(did)
    for did_info in did_info_list:
        delete_mongo_database(did_info[DID], did_info[APP_ID])


def count_vault_storage_job():
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING}
    info_list = col.find(query)
    for service in info_list:
        file_size = count_file_system_storage_size(service[VAULT_SERVICE_DID])
        db_size = count_db_storage_size(service[VAULT_SERVICE_DID])
        now = datetime.utcnow().timestamp()
        query_id = {"_id": service["_id"]}
        value = {"$set": {VAULT_SERVICE_FILE_USE_STORAGE: file_size,
                          VAULT_SERVICE_DB_USE_STORAGE: db_size,
                          VAULT_SERVICE_MODIFY_TIME: now
                          }}
        col.update_one(query_id, value)


def get_used_storage(did):
    file_size = count_file_system_storage_size(did)
    db_size = count_db_storage_size(did)
    now = datetime.utcnow().timestamp()
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: did}
    value = {"$set": {VAULT_SERVICE_FILE_USE_STORAGE: file_size,
                      VAULT_SERVICE_DB_USE_STORAGE: db_size,
                      VAULT_SERVICE_MODIFY_TIME: now
                      }}
    col.update_one(query, value)
    return (file_size + db_size) / (1000 * 1000)


def less_than_max_storage(did):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: did}
    info = col.find_one(query)
    if info:
        return info[VAULT_SERVICE_MAX_STORAGE] >= (
                info[VAULT_SERVICE_FILE_USE_STORAGE] + info[VAULT_SERVICE_DB_USE_STORAGE]) / (1000 * 1000)
    else:
        return False


def inc_file_use_storage_byte(did, storage_type, size):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    now = datetime.utcnow().timestamp()
    if storage_type == VAULT_STORAGE_FILE:
        dic = {
            VAULT_SERVICE_FILE_USE_STORAGE: size,
            VAULT_SERVICE_MODIFY_TIME: now
        }
    else:
        dic = {
            VAULT_SERVICE_DB_USE_STORAGE: size,
            VAULT_SERVICE_MODIFY_TIME: now
        }

    query = {VAULT_SERVICE_DID: did}
    value = {"$inc": dic}
    ret = col.update_one(query, value)
    return ret

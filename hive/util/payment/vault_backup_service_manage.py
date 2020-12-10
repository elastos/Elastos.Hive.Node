import os
import shutil
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient

from hive.settings import MONGO_HOST, MONGO_PORT, BACKUP_VAULTS_BASE_DIR
from hive.util.common import did_tail_part
from hive.util.constants import DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, VAULT_BACKUP_SERVICE_DID, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME, \
    VAULT_BACKUP_SERVICE_USING, VAULT_ACCESS_WR, DID, APP_ID, VAULT_BACKUP_SERVICE_USE_STORAGE, \
    VAULT_BACKUP_SERVICE_MODIFY_TIME

from hive.util.did_file_info import get_dir_size
from hive.util.did_info import get_all_did_info_by_did
from hive.util.did_mongo_db_resource import delete_mongo_database, get_mongo_database_size
from hive.util.payment.payment_config import PaymentConfig

VAULT_BACKUP_SERVICE_FREE_STATE = "Free"


def setup_vault_backup_service(did, max_storage, service_days, backup_name=VAULT_BACKUP_SERVICE_FREE_STATE):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    now = datetime.utcnow().timestamp()
    if service_days == -1:
        end_time = -1
    else:
        end_time = now + service_days * 24 * 60 * 60

    dic = {VAULT_BACKUP_SERVICE_DID: did,
           VAULT_BACKUP_SERVICE_MAX_STORAGE: max_storage,
           VAULT_BACKUP_SERVICE_USE_STORAGE: 0.0,
           VAULT_BACKUP_SERVICE_START_TIME: now,
           VAULT_BACKUP_SERVICE_END_TIME: end_time,
           VAULT_BACKUP_SERVICE_MODIFY_TIME: now,
           VAULT_BACKUP_SERVICE_USING: backup_name
           }

    query = {VAULT_BACKUP_SERVICE_DID: did}
    value = {"$set": dic}
    ret = col.update_one(query, value, upsert=True)
    return ret


def update_vault_backup_service(did, max_storage, service_days, backup_name):
    # If there has a service, we just update it. complex process latter
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    now = datetime.utcnow().timestamp()
    if service_days == -1:
        end_time = -1
    else:
        end_time = now + service_days * 24 * 60 * 60

    dic = {VAULT_BACKUP_SERVICE_DID: did,
           VAULT_BACKUP_SERVICE_MAX_STORAGE: max_storage,
           VAULT_BACKUP_SERVICE_START_TIME: now,
           VAULT_BACKUP_SERVICE_END_TIME: end_time,
           VAULT_BACKUP_SERVICE_MODIFY_TIME: now,
           VAULT_BACKUP_SERVICE_USING: backup_name
           }

    query = {VAULT_BACKUP_SERVICE_DID: did}
    value = {"$set": dic}
    ret = col.update_one(query, value)
    return ret


def get_vault_backup_service(did):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    query = {VAULT_BACKUP_SERVICE_DID: did}
    service = col.find_one(query)
    return service


def proc_expire_vault_backup_job():
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    query = {VAULT_BACKUP_SERVICE_USING: {"$ne": VAULT_BACKUP_SERVICE_FREE_STATE}}
    info_list = col.find(query)
    now = datetime.utcnow().timestamp()
    for service in info_list:
        if service[VAULT_BACKUP_SERVICE_END_TIME] == -1:
            continue
        elif now > service[VAULT_BACKUP_SERVICE_END_TIME]:
            free_info = PaymentConfig.get_free_vault_info()
            query_id = {"_id": service["_id"]}
            value = {"$set": {VAULT_BACKUP_SERVICE_USING: VAULT_BACKUP_SERVICE_FREE_STATE,
                              VAULT_BACKUP_SERVICE_MAX_STORAGE: free_info["maxStorage"],
                              VAULT_BACKUP_SERVICE_START_TIME: now,
                              VAULT_BACKUP_SERVICE_END_TIME: -1,
                              VAULT_BACKUP_SERVICE_MODIFY_TIME: now
                              }}
            col.update_one(query_id, value)


def get_vault_backup_path(did):
    path = Path(BACKUP_VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did)
    else:
        path = path.resolve() / did_tail_part(did)
    return path.resolve()


def delete_user_backup_vault(did):
    path = get_vault_backup_path(did)
    if path.exists():
        shutil.rmtree(path)


def count_vault_backup_storage_size(did):
    vault_path = get_vault_backup_path(did)
    storage_size = 0.0
    storage_size_mb = get_dir_size(vault_path.as_posix(), storage_size)
    return storage_size_mb


def count_vault_backup_storage_job():
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    info_list = col.find()
    for service in info_list:
        use_size = count_vault_backup_storage_size(service[VAULT_BACKUP_SERVICE_DID])
        now = datetime.utcnow().timestamp()
        query_id = {"_id": service["_id"]}
        value = {"$set": {VAULT_BACKUP_SERVICE_USE_STORAGE: use_size,
                          VAULT_BACKUP_SERVICE_MODIFY_TIME: now
                          }}
        col.update_one(query_id, value)


def get_backup_used_storage(did):
    use_size = count_vault_backup_storage_size(did)
    now = datetime.utcnow().timestamp()
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    query = {VAULT_BACKUP_SERVICE_DID: did}
    value = {"$set": {VAULT_BACKUP_SERVICE_USE_STORAGE: use_size,
                      VAULT_BACKUP_SERVICE_MODIFY_TIME: now
                      }}
    col.update_one(query, value)
    return use_size / (1024 * 1024)


def __less_than_max_storage(did):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    query = {VAULT_BACKUP_SERVICE_DID: did}
    info = col.find_one(query)
    if info:
        return info[VAULT_BACKUP_SERVICE_MAX_STORAGE] >= (info[VAULT_BACKUP_SERVICE_USE_STORAGE] / (1024 * 1024))
    else:
        return False


def inc_backup_use_storage_byte(did, size):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    query = {VAULT_BACKUP_SERVICE_DID: did}
    info = col.find_one(query)
    info[VAULT_BACKUP_SERVICE_USE_STORAGE] = info[VAULT_BACKUP_SERVICE_USE_STORAGE] + size
    now = datetime.utcnow().timestamp()
    info[VAULT_BACKUP_SERVICE_MODIFY_TIME] = now
    query = {VAULT_BACKUP_SERVICE_DID: did}
    value = {"$set": info}
    ret = col.update_one(query, value)
    return ret

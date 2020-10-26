import os
import shutil
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient

from settings import MONGO_HOST, MONGO_PORT, VAULTS_BASE_DIR
from util.common import did_tail_part
from util.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_APP_ID, \
    VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, VAULT_SERVICE_DELETE_TIME, \
    VAULT_SERVICE_EXPIRE_READ, VAULT_SERVICE_STATE, VAULT_ACCESS_WR, VAULT_ACCESS_R
from util.did_mongo_db_resource import delete_mongo_database

VAULT_SERVICE_STATE_RUNNING = "running"
VAULT_SERVICE_STATE_EXPIRE = "expire"
VAULT_SERVICE_STATE_DELETE = "delete"


def setup_vault_service(did, app_id, max_storage, delete_expire_days, can_read_expire, service_days):
    # If there has a service, we just update it. complex process latter
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    start_time = datetime.utcnow().timestamp()
    end_time = start_time + service_days * 24 * 60 * 60
    delete_time = end_time + delete_expire_days * 24 * 60 * 60

    order_dic = {VAULT_SERVICE_DID: did,
                 VAULT_SERVICE_APP_ID: app_id,
                 VAULT_SERVICE_MAX_STORAGE: max_storage,
                 VAULT_SERVICE_START_TIME: start_time,
                 VAULT_SERVICE_END_TIME: end_time,
                 VAULT_SERVICE_DELETE_TIME: delete_time,
                 VAULT_SERVICE_EXPIRE_READ: can_read_expire,
                 VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING
                 }

    query = {VAULT_SERVICE_DID: did, VAULT_SERVICE_APP_ID: app_id}
    value = {"$set": order_dic}
    ret = col.update_one(query, value, upsert=True)
    return ret


def get_vault_service(did, app_id):
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: did, VAULT_SERVICE_APP_ID: app_id}
    service = col.find_one(query)
    return service


def can_write_read(did, app_id):
    info = get_vault_service(did, app_id)
    if not info:
        return False
    if info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_RUNNING:
        return True
    else:
        return False


def can_read(did, app_id):
    info = get_vault_service(did, app_id)
    if not info:
        return False
    if info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_RUNNING:
        return True
    elif (info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_EXPIRE) and (info[VAULT_SERVICE_EXPIRE_READ]):
        return True
    else:
        return False


def can_access_vault(did, app_id, access_vault):
    if access_vault == VAULT_ACCESS_WR:
        if can_write_read(did, app_id):
            return True
        else:
            return False
    elif access_vault == VAULT_ACCESS_R:
        if can_read(did, app_id):
            return True
        else:
            return False
    else:
        return False


def get_vault_path(did, app_id):
    path = Path(VAULTS_BASE_DIR)
    if path.is_absolute():
        path = path / did_tail_part(did) / app_id
    else:
        path = path.resolve() / did_tail_part(did) / app_id
    return path.resolve()


def delete_user_vault(did, app_id):
    path = get_vault_path(did, app_id)
    if path.exists():
        shutil.rmtree(path)


def get_dir_size(path):
    total_size = 0
    path = os.path.abspath(path)
    file_list = os.listdir(path)
    for i in file_list:
        i_path = os.path.join(path, i)
        if os.path.isfile(i_path):
            total_size += os.path.getsize(i_path)
        else:
            try:
                get_dir_size(i_path)
            except RecursionError:
                print('Err too much for get_file_size')
    return total_size


def less_than_max_storage(did, app_id):
    info = get_vault_service(did, app_id)
    vault_path = get_vault_path(did, app_id)
    file_size_mb = get_dir_size(vault_path.as_posix()) / (1000 * 1000)
    return file_size_mb <= info[VAULT_SERVICE_MAX_STORAGE]


def proc_delete_vault_job():
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_EXPIRE}
    info_list = col.find(query)

    now = datetime.utcnow().timestamp()
    for service in info_list:
        if now > service[VAULT_SERVICE_DELETE_TIME]:
            delete_mongo_database(service[VAULT_SERVICE_DID], service[VAULT_SERVICE_APP_ID])
            delete_user_vault(service[VAULT_SERVICE_DID], service[VAULT_SERVICE_APP_ID])
            query_id = {"_id": service["_id"]}
            value = {"$set": {VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_DELETE}}
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
            value = {"$set": {VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_EXPIRE}}
            col.update_one(query_id, value)

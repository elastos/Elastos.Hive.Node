import os
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from pymongo import MongoClient

from hive.settings import MONGO_HOST, MONGO_PORT, BACKUP_VAULTS_BASE_DIR
from hive.util.common import did_tail_part, random_string, create_full_path_dir
from hive.util.constants import DID_INFO_DB_NAME, VAULT_BACKUP_SERVICE_COL, VAULT_BACKUP_SERVICE_DID, \
    VAULT_BACKUP_SERVICE_MAX_STORAGE, VAULT_BACKUP_SERVICE_START_TIME, VAULT_BACKUP_SERVICE_END_TIME, \
    VAULT_BACKUP_SERVICE_USING, VAULT_ACCESS_WR, DID, APP_ID, VAULT_BACKUP_SERVICE_USE_STORAGE, \
    VAULT_BACKUP_SERVICE_MODIFY_TIME, VAULT_BACKUP_SERVICE_FTP

from hive.util.did_file_info import get_dir_size, get_save_files_path
from hive.util.did_mongo_db_resource import gene_mongo_db_name
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
           VAULT_BACKUP_SERVICE_USING: backup_name,
           VAULT_BACKUP_SERVICE_FTP: None
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


def parse_ftp_record(ftp_data):
    ftp_info = ftp_data.split(":")
    return ftp_info[0], ftp_info[1]


def compose_ftp_record(user, passwd):
    return f"{user}:{passwd}"


def gene_vault_backup_ftp_record(did):
    user = random_string(5)
    passwd = random_string(10)
    now = datetime.utcnow().timestamp()

    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    query = {VAULT_BACKUP_SERVICE_DID: did}
    dic = {VAULT_BACKUP_SERVICE_FTP: compose_ftp_record(user, passwd),
           VAULT_BACKUP_SERVICE_MODIFY_TIME: now}
    value = {"$set": dic}
    ret = col.update_one(query, value)
    return user, passwd


def remove_vault_backup_ftp_record(did):
    now = datetime.utcnow().timestamp()
    connection = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_BACKUP_SERVICE_COL]
    query = {VAULT_BACKUP_SERVICE_DID: did}
    dic = {VAULT_BACKUP_SERVICE_FTP: None,
           VAULT_BACKUP_SERVICE_MODIFY_TIME: now}
    value = {"$set": dic}
    ret = col.update_one(query, value)


def get_vault_backup_ftp_record(did):
    info = get_vault_backup_service(did)
    if not info:
        return None, None
    else:
        return parse_ftp_record(info[VAULT_BACKUP_SERVICE_FTP])


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


def get_vault_backup_mongodb_path(did, app_id):
    path = get_vault_backup_path(did)
    return path / app_id / "mongo_db"


def get_vault_backup_file_path(did, app_id):
    path = get_vault_backup_path(did)
    return path / app_id / "files"


def get_vault_backup_relative_path(did):
    return did_tail_part(did)


def delete_user_backup_vault(did):
    path = get_vault_backup_path(did)
    if path.exists():
        shutil.rmtree(path)


def import_files_from_backup(did, app_id):
    src_path = get_vault_backup_file_path(did, app_id)
    if not src_path.exists():
        return False
    dst_path = get_save_files_path(did, app_id)
    if not dst_path.exists():
        create_full_path_dir(dst_path)
    shutil.copytree(src_path.as_posix(), dst_path.as_posix())
    return True


def import_mongo_db_from_backup(did, app_id):
    path = get_vault_backup_mongodb_path(did, app_id)
    if not path.exists():
        return False
    db_name = gene_mongo_db_name(did, app_id)
    save_path = path / db_name
    line2 = 'mongorestore -h %s --port %s  -d %s --drop %s' % (MONGO_HOST, MONGO_PORT, db_name, save_path)
    subprocess.call(line2, shell=True)
    return True


def count_vault_backup_storage_size(did):
    vault_path = get_vault_backup_path(did)
    storage_size = 0.0
    storage_size = get_dir_size(vault_path.as_posix(), storage_size)
    return storage_size


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


def less_than_max_storage(did):
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

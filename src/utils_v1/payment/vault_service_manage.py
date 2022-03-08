import shutil
from datetime import datetime

from src.utils_v1.constants import DID_INFO_DB_NAME, VAULT_SERVICE_COL, VAULT_SERVICE_DID, VAULT_SERVICE_STATE, \
    VAULT_SERVICE_MAX_STORAGE, VAULT_SERVICE_START_TIME, VAULT_SERVICE_END_TIME, VAULT_SERVICE_PRICING_USING, \
    VAULT_ACCESS_WR, USER_DID, APP_ID, VAULT_SERVICE_FILE_USE_STORAGE, VAULT_SERVICE_DB_USE_STORAGE, \
    VAULT_SERVICE_MODIFY_TIME, VAULT_ACCESS_DEL

from src.utils_v1.did_file_info import get_dir_size, get_vault_path
from src.utils_v1.did_info import get_all_did_info_by_did
from src.utils_v1.did_mongo_db_resource import delete_mongo_database, get_mongo_database_size, create_db_client
from src.utils_v1.error_code import NOT_FOUND, LOCKED, NOT_ENOUGH_SPACE, SUCCESS, METHOD_NOT_ALLOWED
from src.utils_v1.payment.payment_config import PaymentConfig
from src.utils_v1.payment.vault_backup_service_manage import get_vault_backup_service

VAULT_SERVICE_FREE = "Free"
VAULT_SERVICE_STATE_RUNNING = "running"
VAULT_SERVICE_STATE_FREEZE = "freeze"


def setup_vault_service(did, max_storage, service_days, pricing_name=VAULT_SERVICE_FREE):
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    now = datetime.utcnow().timestamp()
    if service_days == -1:
        end_time = -1
    else:
        end_time = now + service_days * 24 * 60 * 60

    dic = {VAULT_SERVICE_DID: did,
           VAULT_SERVICE_MAX_STORAGE: max_storage,
           VAULT_SERVICE_FILE_USE_STORAGE: 0.0,
           VAULT_SERVICE_DB_USE_STORAGE: 0.0,
           VAULT_SERVICE_START_TIME: now,
           VAULT_SERVICE_END_TIME: end_time,
           VAULT_SERVICE_MODIFY_TIME: now,
           VAULT_SERVICE_STATE: VAULT_SERVICE_STATE_RUNNING,
           VAULT_SERVICE_PRICING_USING: pricing_name
           }

    query = {VAULT_SERVICE_DID: did}
    value = {"$set": dic}
    ret = col.update_one(query, value, upsert=True)
    return ret


def update_vault_service(did, max_storage, service_days, pricing_name):
    # If there has a service, we just update it. complex process latter
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    now = datetime.utcnow().timestamp()
    if service_days == -1:
        end_time = -1
    else:
        end_time = now + service_days * 24 * 60 * 60

    dic = {VAULT_SERVICE_DID: did,
           VAULT_SERVICE_MAX_STORAGE: max_storage,
           VAULT_SERVICE_START_TIME: now,
           VAULT_SERVICE_END_TIME: end_time,
           VAULT_SERVICE_MODIFY_TIME: now,
           VAULT_SERVICE_PRICING_USING: pricing_name
           }

    query = {VAULT_SERVICE_DID: did}
    value = {"$set": dic}
    ret = col.update_one(query, value)
    return ret


def remove_vault_service(did):
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: did}
    col.delete_many(query)


def freeze_vault(did):
    update_vault_service_state(did, VAULT_SERVICE_STATE_FREEZE)


def unfreeze_vault(did):
    update_vault_service_state(did, VAULT_SERVICE_STATE_RUNNING)


def update_vault_service_state(did, state):
    # If there has a service, we just update it. complex process latter
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    now = datetime.utcnow().timestamp()

    dic = {VAULT_SERVICE_DID: did,
           VAULT_SERVICE_MODIFY_TIME: now,
           VAULT_SERVICE_STATE: state
           }

    query = {VAULT_SERVICE_DID: did}
    value = {"$set": dic}
    ret = col.update_one(query, value)
    return ret


def get_vault_service(did):
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: did}
    service = col.find_one(query)
    return service


def can_access_vault(did, access_vault):
    info = get_vault_service(did)
    if not info:
        return NOT_FOUND, "vault does not exist."

    if access_vault == VAULT_ACCESS_WR:
        if (VAULT_SERVICE_STATE in info) and (info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_FREEZE):
            return LOCKED, "vault have been freeze, can not write"
        elif not __less_than_max_storage(did):
            return NOT_ENOUGH_SPACE, "not enough storage space"
        else:
            return SUCCESS, None
    elif access_vault == VAULT_ACCESS_DEL:
        if (VAULT_SERVICE_STATE in info) and (info[VAULT_SERVICE_STATE] == VAULT_SERVICE_STATE_FREEZE):
            return LOCKED, "vault have been freeze, can not write"
        else:
            return SUCCESS, None
    else:
        return SUCCESS, None


def can_access_backup(did):
    info = get_vault_backup_service(did)
    if not info:
        return METHOD_NOT_ALLOWED, "No backup service."
    else:
        return SUCCESS, None


def delete_user_vault_data(did):
    path = get_vault_path(did)
    if path.exists():
        shutil.rmtree(path)
    delete_db_storage(did)


def delete_user_vault(did):
    delete_user_vault_data(did)
    remove_vault_service(did)


def proc_expire_vault_job():
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_PRICING_USING: {"$ne": VAULT_SERVICE_FREE}}
    info_list = col.find(query)
    now = datetime.utcnow().timestamp()
    for service in info_list:
        if service[VAULT_SERVICE_END_TIME] == -1:
            continue
        elif now > service[VAULT_SERVICE_END_TIME]:
            free_info = PaymentConfig.get_free_vault_info()
            query_id = {"_id": service["_id"]}
            value = {"$set": {VAULT_SERVICE_PRICING_USING: VAULT_SERVICE_FREE,
                              VAULT_SERVICE_MAX_STORAGE: free_info["maxStorage"],
                              VAULT_SERVICE_START_TIME: now,
                              VAULT_SERVICE_END_TIME: -1,
                              VAULT_SERVICE_MODIFY_TIME: now
                              }}
            col.update_one(query_id, value)


def count_file_system_storage_size(did):
    vault_path = get_vault_path(did)
    if not vault_path.exists() or vault_path.is_file():
        return 0.0
    return get_dir_size(vault_path.as_posix(), 0.0)


def count_db_storage_size(did):
    did_info_list = get_all_did_info_by_did(did)
    total_size = 0.0
    for did_info in did_info_list:
        total_size += get_mongo_database_size(did_info[USER_DID], did_info[APP_ID])
    return total_size


def delete_db_storage(did):
    did_info_list = get_all_did_info_by_did(did)
    for did_info in did_info_list:
        delete_mongo_database(did_info[USER_DID], did_info[APP_ID])


def get_vault_used_storage(did):
    file_size = count_file_system_storage_size(did)
    db_size = count_db_storage_size(did)
    now = datetime.utcnow().timestamp()
    connection = create_db_client()

    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: did}
    value = {"$set": {VAULT_SERVICE_FILE_USE_STORAGE: file_size,
                      VAULT_SERVICE_DB_USE_STORAGE: db_size,
                      VAULT_SERVICE_MODIFY_TIME: now
                      }}
    col.update_one(query, value)
    return (file_size + db_size) / (1024 * 1024)


def __less_than_max_storage(did):
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: did}
    info = col.find_one(query)
    if info:
        return info[VAULT_SERVICE_MAX_STORAGE] >= (
                info[VAULT_SERVICE_FILE_USE_STORAGE] + info[VAULT_SERVICE_DB_USE_STORAGE]) / (1024 * 1024)
    else:
        return False


"""
# update the total used amount for files data in the vault owned by specific user did.
# user_did: user did who owns vault data;
# varied_amount: varying amount in byte, could be negative value, which means data is being removed.
"""
def update_used_storage_for_files_data(user_did, varying_size, is_reset=False):
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: user_did}
    info = col.find_one(query)
    info[VAULT_SERVICE_FILE_USE_STORAGE] = varying_size if is_reset else (info[VAULT_SERVICE_FILE_USE_STORAGE] + varying_size)
    now = datetime.utcnow().timestamp()
    info[VAULT_SERVICE_MODIFY_TIME] = now
    query = {VAULT_SERVICE_DID: user_did}
    value = {"$set": info}
    ret = col.update_one(query, value)
    return ret


"""
# update the total used amount for database data in the vault owned by specific user did.
# user_did: user did who owns vault data;
# varied_amount: varying amount in byte, could be negative value, which means data is being removed.
"""
def update_used_storage_for_mongodb_data(user_did, varying_size):
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_SERVICE_COL]
    query = {VAULT_SERVICE_DID: user_did}
    now = datetime.utcnow().timestamp()
    dic = {
        VAULT_SERVICE_DB_USE_STORAGE: varying_size,
        VAULT_SERVICE_MODIFY_TIME: now
    }
    value = {"$set": dic}
    ret = col.update_one(query, value)
    return ret

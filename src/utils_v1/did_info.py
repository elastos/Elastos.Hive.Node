import uuid

from src.utils_v1.constants import DID_INFO_DB_NAME, DID_INFO_REGISTER_COL, USER_DID, \
    APP_ID, DID_INFO_NONCE, DID_INFO_TOKEN, DID_INFO_TOKEN_EXPIRED, APP_INSTANCE_DID
from src.utils_v1.did_mongo_db_resource import gene_mongo_db_name, create_db_client


def update_token_of_did_info(did, app_did, app_instance_did, nonce, token, expired):
    """ Used in auth, maybe can remove this """
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {APP_INSTANCE_DID: app_instance_did, DID_INFO_NONCE: nonce}
    value = {"$set": {USER_DID: did, APP_ID: app_did, DID_INFO_TOKEN: token, DID_INFO_TOKEN_EXPIRED: expired}}
    ret = col.update_one(query, value)
    return ret


def get_auth_info_by_nonce(nonce):
    """ used by auth to handle challenge response """
    connection = create_db_client()
    db = connection[DID_INFO_DB_NAME]
    col = db[DID_INFO_REGISTER_COL]
    query = {DID_INFO_NONCE: nonce}
    info = col.find_one(query)
    return info


def get_collection(did, app_did, collection):
    connection = create_db_client()
    db_name = gene_mongo_db_name(did, app_did)
    db = connection[db_name]
    col = db[collection]
    return col


def create_token():
    token = uuid.uuid1()
    return str(token)


def create_nonce():
    nonce = uuid.uuid1()
    return str(nonce)

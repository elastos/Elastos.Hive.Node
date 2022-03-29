import hashlib
from datetime import datetime

from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from hive.settings import hive_setting
from hive.util.constants import DID_INFO_DB_NAME, PUB_CHANNEL_COLLECTION, PUB_CHANNEL_PUB_DID, \
    PUB_CHANNEL_PUB_APPID, PUB_CHANNEL_NAME, PUB_CHANNEL_MODIFY_TIME, PUB_CHANNEL_ID, \
    PUB_CHANNEL_SUB_DID, PUB_CHANNEL_SUB_APPID


# publisher: create channel, list channels, subscribe, push messages
def pub_setup_channel(pub_did, pub_appid, channel_name):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[PUB_CHANNEL_COLLECTION]
    _id = pubsub_get_channel_id(pub_did, pub_appid, channel_name)
    dic = {
        "_id": _id,
        PUB_CHANNEL_PUB_DID: pub_did,
        PUB_CHANNEL_PUB_APPID: pub_appid,
        PUB_CHANNEL_NAME: channel_name,
        PUB_CHANNEL_MODIFY_TIME: datetime.utcnow().timestamp()
    }
    try:
        ret = col.insert_one(dic)
    except DuplicateKeyError:
        return None

    channel_id = ret.inserted_id
    return channel_id


def pub_remove_channel(pub_did, pub_appid, channel_name):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[PUB_CHANNEL_COLLECTION]
    query = {
        PUB_CHANNEL_PUB_DID: pub_did,
        PUB_CHANNEL_PUB_APPID: pub_appid,
        PUB_CHANNEL_NAME: channel_name,
    }
    col.delete_many(query)


def pubsub_get_channel_id(did, app_id, channel_name):
    md5 = hashlib.md5()
    md5.update(f"{did}_{app_id}_{channel_name}".encode("utf-8"))
    return str(md5.hexdigest())


def pub_get_channel(pub_did, pub_appid, channel_name):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[PUB_CHANNEL_COLLECTION]
    channel_id = pubsub_get_channel_id(pub_did, pub_appid, channel_name)
    dic = {
        "_id": channel_id
    }

    info = col.find_one(dic)
    return info


def pub_get_pub_channels(pub_did, pub_appid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[PUB_CHANNEL_COLLECTION]
    query = {
        PUB_CHANNEL_PUB_DID: pub_did,
        PUB_CHANNEL_PUB_APPID: pub_appid,
        PUB_CHANNEL_SUB_DID: {"$exists": False},
        PUB_CHANNEL_SUB_APPID: {"$exists": False}
    }

    info = col.find(query)
    return info


def pub_get_sub_channels(sub_did, sub_appid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[PUB_CHANNEL_COLLECTION]
    query = {
        PUB_CHANNEL_SUB_DID: sub_did,
        PUB_CHANNEL_SUB_APPID: sub_appid
    }

    info = col.find(query)
    return info


def pubsub_get_subscribe_id(pub_did, pub_appid, channel_name, sub_did, sub_appid):
    md5 = hashlib.md5()
    md5.update(f"{pub_did}_{pub_appid}_{channel_name}_{sub_did}_{sub_appid}".encode("utf-8"))
    return str(md5.hexdigest())


def pub_add_subscriber(pub_did, pub_appid, channel_name, sub_did, sub_appid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[PUB_CHANNEL_COLLECTION]
    _id = pubsub_get_subscribe_id(pub_did, pub_appid, channel_name, sub_did, sub_appid)
    dic = {
        "_id": _id,
        PUB_CHANNEL_PUB_DID: pub_did,
        PUB_CHANNEL_PUB_APPID: pub_appid,
        PUB_CHANNEL_NAME: channel_name,
        PUB_CHANNEL_SUB_DID: sub_did,
        PUB_CHANNEL_SUB_APPID: sub_appid,
        PUB_CHANNEL_MODIFY_TIME: datetime.utcnow().timestamp()
    }
    try:
        ret = col.insert_one(dic)
    except DuplicateKeyError:
        return None

    subscribe_id = ret.inserted_id
    return subscribe_id


def pub_remove_subscribe(pub_did, pub_appid, channel_name, sub_did, sub_appid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[PUB_CHANNEL_COLLECTION]
    _id = pubsub_get_subscribe_id(pub_did, pub_appid, channel_name, sub_did, sub_appid)
    query = {
        "_id": _id
    }
    col.delete_one(query)


def pub_get_subscriber(pub_did, pub_appid, channel_name, sub_did, sub_appid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[PUB_CHANNEL_COLLECTION]
    subscribe_id = pubsub_get_subscribe_id(pub_did, pub_appid, channel_name, sub_did, sub_appid)
    dic = {
        "_id": subscribe_id
    }

    info = col.find_one(dic)
    return info


def pub_get_subscriber_list(pub_did, pub_appid, channel_name):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[PUB_CHANNEL_COLLECTION]
    query = {
        PUB_CHANNEL_PUB_DID: pub_did,
        PUB_CHANNEL_PUB_APPID: pub_appid,
        PUB_CHANNEL_NAME: channel_name,
        PUB_CHANNEL_SUB_DID: {"$exists": True},
        PUB_CHANNEL_SUB_APPID: {"$exists": True}
    }

    info_list = col.find(query)
    return info_list

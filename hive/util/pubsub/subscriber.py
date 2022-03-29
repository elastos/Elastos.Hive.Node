from datetime import datetime

import pymongo
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from hive.settings import hive_setting
from hive.util.constants import DID_INFO_DB_NAME, SUB_MESSAGE_COLLECTION, SUB_MESSAGE_PUB_DID, \
    SUB_MESSAGE_PUB_APPID, SUB_MESSAGE_CHANNEL_NAME, SUB_MESSAGE_SUB_DID, SUB_MESSAGE_SUB_APPID, \
    SUB_MESSAGE_MODIFY_TIME, SUB_MESSAGE_DATA, SUB_MESSAGE_TIME, SUB_MESSAGE_SUBSCRIBE_ID
from hive.util.pubsub.publisher import pubsub_get_subscribe_id


def sub_setup_message_subscriber(pub_did, pub_appid, channel_name, sub_did, sub_appid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[SUB_MESSAGE_COLLECTION]
    _id = pubsub_get_subscribe_id(pub_did, pub_appid, channel_name, sub_did, sub_appid)
    dic = {
        "_id": _id,
        SUB_MESSAGE_PUB_DID: pub_did,
        SUB_MESSAGE_PUB_APPID: pub_appid,
        SUB_MESSAGE_CHANNEL_NAME: channel_name,
        SUB_MESSAGE_SUB_DID: sub_did,
        SUB_MESSAGE_SUB_APPID: sub_appid,
        SUB_MESSAGE_MODIFY_TIME: datetime.utcnow().timestamp()
    }
    try:
        ret = col.insert_one(dic)
    except DuplicateKeyError:
        return None

    subscribe_id = ret.inserted_id
    return subscribe_id


def sub_remove_message_subscriber(pub_did, pub_appid, channel_name, sub_did, sub_appid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[SUB_MESSAGE_COLLECTION]
    query = {
        SUB_MESSAGE_PUB_DID: pub_did,
        SUB_MESSAGE_PUB_APPID: pub_appid,
        SUB_MESSAGE_CHANNEL_NAME: channel_name,
        SUB_MESSAGE_SUB_DID: sub_did,
        SUB_MESSAGE_SUB_APPID: sub_appid,
    }
    col.delete_many(query)


def sub_get_message_subscriber(pub_did, pub_appid, channel_name, sub_did, sub_appid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[SUB_MESSAGE_COLLECTION]
    _id = pubsub_get_subscribe_id(pub_did, pub_appid, channel_name, sub_did, sub_appid)
    query = {
        "_id": _id
    }
    info = col.find_one(query)
    return info


def sub_add_message(pub_did, pub_appid, channel_name, sub_did, sub_appid, message, message_time):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[SUB_MESSAGE_COLLECTION]
    _id = pubsub_get_subscribe_id(pub_did, pub_appid, channel_name, sub_did, sub_appid)
    dic = {
        SUB_MESSAGE_SUBSCRIBE_ID: _id,
        SUB_MESSAGE_PUB_DID: pub_did,
        SUB_MESSAGE_PUB_APPID: pub_appid,
        SUB_MESSAGE_CHANNEL_NAME: channel_name,
        SUB_MESSAGE_SUB_DID: sub_did,
        SUB_MESSAGE_SUB_APPID: sub_appid,
        SUB_MESSAGE_DATA: message,
        SUB_MESSAGE_TIME: message_time
    }
    ret = col.insert_one(dic)
    return ret


def sub_pop_messages(pub_did, pub_appid, channel_name, sub_did, sub_appid, limit):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[SUB_MESSAGE_COLLECTION]
    _id = pubsub_get_subscribe_id(pub_did, pub_appid, channel_name, sub_did, sub_appid)
    query = {
        SUB_MESSAGE_SUBSCRIBE_ID: _id,
    }
    cursor = col.find(query).sort(SUB_MESSAGE_TIME, pymongo.ASCENDING).limit(limit)
    message_list = list()
    message_ids = list()

    for message in cursor:
        data = {
            "message": message[SUB_MESSAGE_DATA],
            "time": message[SUB_MESSAGE_TIME]
        }
        message_list.append(data)
        message_ids.append(message["_id"])
    if message_ids:
        __remove_messages(message_ids)
    return message_list


def __remove_messages(message_ids):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[SUB_MESSAGE_COLLECTION]
    col.delete_many({"_id": {"$in": message_ids}})

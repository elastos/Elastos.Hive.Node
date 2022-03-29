import json
import logging

from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime
import requests

from hive.util.payment.payment_config import PaymentConfig

from hive.settings import hive_setting
from hive.util.constants import *
from hive.util.payment.vault_backup_service_manage import get_vault_backup_service, setup_vault_backup_service, \
    update_vault_backup_service
from hive.util.payment.vault_service_manage import update_vault_service, get_vault_service, setup_vault_service

VAULT_ORDER_STATE_WAIT_PAY = "wait_pay"
VAULT_ORDER_STATE_WAIT_TX = "wait_tx"
VAULT_ORDER_STATE_WAIT_PAY_TIMEOUT = "wait_pay_timeout"
VAULT_ORDER_STATE_WAIT_TX_TIMEOUT = "wait_tx_timeout"
VAULT_ORDER_STATE_FAILED = "failed"
VAULT_ORDER_STATE_SUCCESS = "success"
VAULT_ORDER_STATE_CANCELED = "canceled"
VAULT_ORDER_TYPE_VAULT = "vault"
VAULT_ORDER_TYPE_BACKUP = "backup"

logger = logging.getLogger("vault_order")


def create_order_info(did, app_id, package_info, order_type=VAULT_ORDER_TYPE_VAULT):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_ORDER_COL]

    order_dic = {VAULT_ORDER_DID: did,
                 VAULT_ORDER_APP_ID: app_id,
                 VAULT_ORDER_PACKAGE_INFO: package_info,
                 VAULT_ORDER_TXIDS: [],
                 VAULT_ORDER_STATE: VAULT_ORDER_STATE_WAIT_PAY,
                 VAULT_ORDER_TYPE: order_type,
                 VAULT_ORDER_CREATE_TIME: datetime.utcnow().timestamp(),
                 VAULT_ORDER_MODIFY_TIME: datetime.utcnow().timestamp()
                 }
    ret = col.insert_one(order_dic)
    order_id = ret.inserted_id
    return order_id


def find_txid(txid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_ORDER_COL]
    query = {VAULT_ORDER_TXIDS: txid}
    ret = col.find(query)
    return ret


def find_canceled_order_by_txid(did, txid):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_ORDER_COL]
    query = {
        VAULT_ORDER_DID: did,
        VAULT_ORDER_TXIDS: txid,
        VAULT_ORDER_STATE: VAULT_ORDER_STATE_CANCELED
    }
    ret = col.find(query)
    return ret


def update_order_info(_id, info_dic):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_ORDER_COL]
    query = {"_id": _id}
    info_dic[VAULT_ORDER_MODIFY_TIME] = datetime.utcnow().timestamp()
    value = {"$set": info_dic}
    ret = col.update_one(query, value)
    return ret


def get_order_info_by_id(_id):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_ORDER_COL]
    query = {"_id": _id}
    info = col.find_one(query)
    return info


def get_order_info_list(did, app_id):
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_ORDER_COL]
    query = {VAULT_ORDER_DID: did, VAULT_ORDER_APP_ID: app_id}
    info_list = col.find(query)
    return info_list


def get_tx_info(tx, target_address):
    param = {
        "method": "getrawtransaction",
        "params": [tx, True]
    }
    try:
        r = requests.post(hive_setting.ESC_RESOLVER_URL, json=param, headers={"Content-Type": "application/json"})
    except Exception as e:
        logger.error("get_tx_info exception, tx:" + tx + " address:" + target_address)
        return None, None

    if r.status_code != 200:
        logger.error("get_tx_info, tx:" + tx + " address:" + target_address + "error code:" + str(r.status_code))
        return None, None
    else:
        ret = r.json()
        if not ret['error']:
            block_time = ret['result']['time']
            if block_time < 1:
                return None, None
            out_list = ret['result']["vout"]
            for out in out_list:
                value = float(out['value'])
                address = out['address']
                if target_address == address:
                    return value, block_time

        return None, None


def deal_order_tx(info):
    address = PaymentConfig.get_payment_address()
    amount = info[VAULT_ORDER_PACKAGE_INFO]["amount"]
    create_time = info[VAULT_ORDER_CREATE_TIME]

    for tx in info[VAULT_ORDER_TXIDS]:
        value, block_time = get_tx_info(tx, address)
        if value:
            amount -= value
            # If the txid blocktime is more earlier than order create time one week
            if create_time > (block_time + 60 * 60 * 24 * 7):
                info_cursor = find_canceled_order_by_txid(info[VAULT_ORDER_DID], tx)
                print(f"count is :{info_cursor.count()}")
                if info_cursor.count() == 0:
                    logger.error(
                        "deal_order_tx failed. tx:" + tx + " block_time:" + str(block_time) + " creat_time" + str(
                            create_time))
                    info[VAULT_ORDER_STATE] = VAULT_ORDER_STATE_FAILED
                    update_order_info(info["_id"], info)
                    return info[VAULT_ORDER_STATE]

    if amount < 0.001:
        info[VAULT_ORDER_STATE] = VAULT_ORDER_STATE_SUCCESS
    else:
        # Just be compatible
        if VAULT_ORDER_PAY_TIME not in info:
            info[VAULT_ORDER_PAY_TIME] = info[VAULT_ORDER_MODIFY_TIME]
        pay_time = info[VAULT_ORDER_PAY_TIME]
        now = datetime.utcnow().timestamp()
        if (now - pay_time) > (PaymentConfig.get_tx_timeout() * 60):
            info[VAULT_ORDER_STATE] = VAULT_ORDER_STATE_WAIT_TX_TIMEOUT

    update_order_info(info["_id"], info)
    return info[VAULT_ORDER_STATE]


def check_pay_order_timeout_job():
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_ORDER_COL]
    query = {VAULT_ORDER_STATE: VAULT_ORDER_STATE_WAIT_PAY}
    info_list = col.find(query)
    now = datetime.utcnow().timestamp()
    for info in info_list:
        create_time = info[VAULT_ORDER_CREATE_TIME]
        if (now - create_time) > (PaymentConfig.get_payment_timeout() * 60):
            info[VAULT_ORDER_STATE] = VAULT_ORDER_STATE_WAIT_PAY_TIMEOUT
            update_order_info(info["_id"], info)


def check_wait_order_tx_job():
    if hive_setting.MONGO_URI:
        uri = hive_setting.MONGO_URI
        connection = MongoClient(uri)
    else:
        connection = MongoClient(hive_setting.MONGODB_URI)

    db = connection[DID_INFO_DB_NAME]
    col = db[VAULT_ORDER_COL]
    query = {VAULT_ORDER_STATE: VAULT_ORDER_STATE_WAIT_TX}
    info_list = col.find(query)
    for info in info_list:
        state = deal_order_tx(info)
        if state == VAULT_ORDER_STATE_SUCCESS:
            # Be compatible
            if VAULT_ORDER_TYPE not in info:
                vault_order_success(info)
            else:
                if info[VAULT_ORDER_TYPE] == VAULT_ORDER_TYPE_VAULT:
                    vault_order_success(info)
                elif info[VAULT_ORDER_TYPE] == VAULT_ORDER_TYPE_BACKUP:
                    vault_backup_order_success(info)
                else:
                    logger.error("check_wait_order_tx_job not support type:" + info[VAULT_ORDER_TYPE])


def vault_order_success(info):
    service = get_vault_service(info[VAULT_ORDER_DID])
    if not service:
        setup_vault_service(info[VAULT_ORDER_DID],
                            info[VAULT_ORDER_PACKAGE_INFO]["maxStorage"],
                            info[VAULT_ORDER_PACKAGE_INFO]["serviceDays"],
                            info[VAULT_ORDER_PACKAGE_INFO]["name"])
    else:
        update_vault_service(info[VAULT_ORDER_DID],
                             info[VAULT_ORDER_PACKAGE_INFO]["maxStorage"],
                             info[VAULT_ORDER_PACKAGE_INFO]["serviceDays"],
                             info[VAULT_ORDER_PACKAGE_INFO]["name"])


def vault_backup_order_success(info):
    service = get_vault_backup_service(info[VAULT_ORDER_DID])
    if not service:
        setup_vault_backup_service(info[VAULT_ORDER_DID],
                                   info[VAULT_ORDER_PACKAGE_INFO]["maxStorage"],
                                   info[VAULT_ORDER_PACKAGE_INFO]["serviceDays"],
                                   info[VAULT_ORDER_PACKAGE_INFO]["name"])
    else:
        update_vault_backup_service(info[VAULT_ORDER_DID],
                                    info[VAULT_ORDER_PACKAGE_INFO]["maxStorage"],
                                    info[VAULT_ORDER_PACKAGE_INFO]["serviceDays"],
                                    info[VAULT_ORDER_PACKAGE_INFO]["name"])

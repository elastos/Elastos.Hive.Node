import logging

from flask import request

from hive.util.error_code import BAD_REQUEST, NOT_FOUND
from hive.util.payment.vault_order import *
from hive.util.payment.vault_service_manage import get_vault_service, setup_vault_service, delete_user_vault, \
    freeze_vault, unfreeze_vault
from hive.util.payment.vault_backup_service_manage import get_vault_backup_service, setup_vault_backup_service
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc, pre_proc, get_pre_proc


class HivePayment:
    def __init__(self):
        self.app = None
        self.response = ServerResponse("HivePayment")

    def init_app(self, app):
        self.app = app
        PaymentConfig.init_config()

    def get_version(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err
        version = PaymentConfig.get_version()
        return self.response.response_ok({"version": version})

    def get_vault_package_info(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err
        data = PaymentConfig.get_all_package_info()
        return self.response.response_ok(data)

    def get_vault_pricing_plan(self):
        did, app_id, content, err = get_pre_proc(self.response, "name")
        if err:
            return err

        data = PaymentConfig.get_pricing_plan(content["name"])
        if data:
            return self.response.response_ok(data)
        else:
            return self.response.response_err(NOT_FOUND, "not found pricing name of:" + content["name"])

    def get_vault_backup_plan(self):
        did, app_id, content, err = get_pre_proc(self.response, "name")
        if err:
            return err

        data = PaymentConfig.get_backup_plan(content["name"])
        if data:
            return self.response.response_ok(data)
        else:
            return self.response.response_err(BAD_REQUEST, "not found backup name of:" + content["name"])

    def create_vault_package_order(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response)
        if err:
            return err

        if "pricing_name" in content:
            package_info = PaymentConfig.get_pricing_plan(content["pricing_name"])
            if not package_info:
                return self.response.response_err(NOT_FOUND, "not found pricing_name of:" + content["pricing_name"])
            order_id = create_order_info(did, app_id, package_info, order_type=VAULT_ORDER_TYPE_VAULT)
            return self.response.response_ok({"order_id": str(order_id)})
        elif "backup_name" in content:
            backup_info = PaymentConfig.get_backup_plan(content["backup_name"])
            if not backup_info:
                return self.response.response_err(NOT_FOUND, "not found backup_name of:" + content["backup_name"])
            order_id = create_order_info(did, app_id, backup_info, order_type=VAULT_ORDER_TYPE_BACKUP)
            return self.response.response_ok({"order_id": str(order_id)})
        else:
            return self.response.response_err(BAD_REQUEST, "parameter pricing_name and backup_name is null")

    def pay_vault_package_order(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "order_id", "pay_txids")
        if err:
            return err

        # if the order is success or have been put txid no more pay again
        info = get_order_info_by_id(ObjectId(content["order_id"]))
        if info:
            if info[VAULT_ORDER_STATE] == VAULT_ORDER_STATE_SUCCESS:
                return self.response.response_ok({"message": "order has been effective"})
            if info[VAULT_ORDER_TXIDS]:
                return self.response.response_ok({"message": "order has been payed no need to pay again"})

        # check whether txids have been used by other order which not be canceled
        for txid in content["pay_txids"]:
            info_cursor = find_txid(txid)
            for info_c in info_cursor:
                if (info_c["_id"] != content["order_id"]) \
                        and ((info_c[VAULT_ORDER_STATE] != VAULT_ORDER_STATE_CANCELED) \
                             or (info_c[VAULT_ORDER_DID] != did)):
                    return self.response.response_err(BAD_REQUEST, "txid:" + txid + " has been used")

        info[VAULT_ORDER_TXIDS] = content["pay_txids"]
        info[VAULT_ORDER_STATE] = VAULT_ORDER_STATE_WAIT_TX
        info[VAULT_ORDER_PAY_TIME] = datetime.utcnow().timestamp()
        update_order_info(info["_id"], info)
        return self.response.response_ok()

    def __id_to_order_id(self, info):
        info["order_id"] = str(info["_id"])
        del info["_id"]
        return info

    def get_vault_package_order(self):
        did, app_id, content, err = get_pre_proc(self.response, "order_id")
        if err is not None:
            return err

        order_id = content['order_id']

        info = get_order_info_by_id(ObjectId(order_id))
        self.__id_to_order_id(info)
        return self.response.response_ok({"order_info": info})

    def get_vault_package_order_list(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err
        info_list = list(get_order_info_list(did, app_id))
        for info in info_list:
            self.__id_to_order_id(info)
        return self.response.response_ok({"order_info_list": info_list})

    def cancel_vault_package_order(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "order_id")
        if err:
            return err
        order_id = content['order_id']
        info = get_order_info_by_id(ObjectId(order_id))
        if info[VAULT_ORDER_STATE] == VAULT_ORDER_STATE_WAIT_TX \
                or info[VAULT_ORDER_STATE] == VAULT_ORDER_STATE_WAIT_PAY:
            info[VAULT_ORDER_STATE] = VAULT_ORDER_STATE_CANCELED

    def create_free_vault(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err

        service = get_vault_service(did)
        if service:
            data = {"existing": True}
            return self.response.response_ok(data)

        free_info = PaymentConfig.get_free_vault_info()

        setup_vault_service(did, free_info["maxStorage"], free_info["serviceDays"])
        return self.response.response_ok()

    def remove_vault(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err
        delete_user_vault(did)
        return self.response.response_ok()

    def freeze_vault(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err
        freeze_vault(did)
        return self.response.response_ok()

    def unfreeze_vault(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err
        unfreeze_vault(did)
        return self.response.response_ok()

    def get_vault_service_info(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err
        info = get_vault_service(did)
        if not info:
            return self.response.response_err(NOT_FOUND, "vault service not found")
        else:
            del info["_id"]
            data = dict()
            # compatible with v2 (unit Byte), but v1 (unit MB)
            info[VAULT_SERVICE_MAX_STORAGE] = int(info[VAULT_SERVICE_MAX_STORAGE]) \
                if info[VAULT_SERVICE_MAX_STORAGE] < 1024 * 1024 \
                else int(info[VAULT_SERVICE_MAX_STORAGE] / (1024 * 1024))
            info[VAULT_SERVICE_FILE_USE_STORAGE] = info[VAULT_SERVICE_FILE_USE_STORAGE] / (1024 * 1024)
            info[VAULT_SERVICE_DB_USE_STORAGE] = info[VAULT_SERVICE_DB_USE_STORAGE] / (1024 * 1024)
            data["vault_service_info"] = info

            return self.response.response_ok(data)

    def create_free_vault_backup(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err

        service = get_vault_backup_service(did)
        if service:
            data = {"existing": True}
            return self.response.response_ok(data)

        free_info = PaymentConfig.get_free_backup_info()

        setup_vault_backup_service(did, free_info["maxStorage"], free_info["serviceDays"])
        return self.response.response_ok()

    def get_vault_backup_service_info(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err
        info = get_vault_backup_service(did)
        if not info:
            return self.response.response_err(NOT_FOUND, "vault backup service not found")
        else:
            del info["_id"]
            data = dict()
            info[VAULT_BACKUP_SERVICE_USE_STORAGE] = info[VAULT_BACKUP_SERVICE_USE_STORAGE] / (1024 * 1024)
            data["vault_service_info"] = info
            return self.response.response_ok(data)

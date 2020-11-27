import logging

from flask import request

from hive.util.payment.vault_order import *
from hive.util.payment.vault_service_manage import get_vault_service, setup_vault_service
from hive.util.server_response import ServerResponse
from hive.main.interceptor import post_json_param_pre_proc, pre_proc, get_pre_proc


class HivePayment:
    def __init__(self):
        self.app = None
        self.response = ServerResponse("HivePayment")
        PaymentConfig.init_config()

    def init_app(self, app):
        self.app = app

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
            return self.response.response_err(400, "not found pricing name of:" + content["name"])

    def create_vault_package_order(self):
        did, app_id, content, err = post_json_param_pre_proc(self.response, "pricing_name")
        if err:
            return err
        package_info = PaymentConfig.get_pricing_plan(content["pricing_name"])
        if not package_info:
            return self.response.response_err(400, "not found pricing_name of:" + content["pricing_name"])
        order_id = create_order_info(did, app_id, package_info)
        return self.response.response_ok({"order_id": str(order_id)})

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

        # check whether txids have been used by other order
        for txid in content["pay_txids"]:
            info_cursor = find_txid(txid)
            if info_cursor.count() != 0:
                return self.response.response_err(400, "txid:" + txid + " has been used")

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

    def create_vault(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err

        service = get_vault_service(did)
        if service:
            return self.response.response_ok()

        free_info = PaymentConfig.get_free_trial_info()

        setup_vault_service(did, free_info["maxStorage"], free_info["serviceDays"])
        return self.response.response_ok()

    def get_vault_service_info(self):
        did, app_id, err = pre_proc(self.response)
        if err:
            return err
        info = get_vault_service(did)
        if not info:
            return self.response.response_ok()
        else:
            del info["_id"]
            data = dict()
            info[VAULT_SERVICE_FILE_USE_STORAGE] = info[VAULT_SERVICE_FILE_USE_STORAGE] / (1024 * 1024)
            info[VAULT_SERVICE_DB_USE_STORAGE] = info[VAULT_SERVICE_DB_USE_STORAGE] / (1024 * 1024)
            data["vault_service_info"] = info

            return self.response.response_ok(data)


import json
import logging

from hive.settings import HIVE_PAYMENT_CONFIG


class PaymentConfig:
    config_info = None

    @staticmethod
    def init_config():
        with open(HIVE_PAYMENT_CONFIG, 'r')as fp:
            json_data = json.load(fp)
            PaymentConfig.config_info = json_data
            # print(json_data)
            logging.getLogger("Hive Payment").info("Load payment config file:" + HIVE_PAYMENT_CONFIG)

    @staticmethod
    def get_all_package_info():
        return PaymentConfig.config_info

    @staticmethod
    def get_version():
        return PaymentConfig.config_info["version"]

    @staticmethod
    def get_free_vault_info():
        return PaymentConfig.get_pricing_plan("Free")

    @staticmethod
    def get_free_backup_info():
        return PaymentConfig.get_backup_plan("Free")

    @staticmethod
    def get_payment_address():
        return PaymentConfig.config_info["paymentSettings"]["receivingELAAddress"]

    @staticmethod
    def get_payment_timeout():
        return PaymentConfig.config_info["paymentSettings"]["wait_payment_timeout"]

    @staticmethod
    def get_tx_timeout():
        return PaymentConfig.config_info["paymentSettings"]["wait_tx_timeout"]

    @staticmethod
    def get_pricing_plan(name):
        pricing_plan_list = PaymentConfig.config_info["pricingPlans"]

        for pricing_plan in pricing_plan_list:
            p_name = pricing_plan["name"]
            if p_name == name:
                return pricing_plan

        return None

    @staticmethod
    def get_backup_plan(name):
        backup_plan_list = PaymentConfig.config_info["backupPlans"]

        for backup_plan in backup_plan_list:
            p_name = backup_plan["name"]
            if p_name == name:
                return backup_plan

        return None

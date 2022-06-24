import json
import logging
import os
from pathlib import Path

from hive.settings import hive_setting

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, '../../..')


class PaymentConfig:
    config_info = None

    @staticmethod
    def init_config():
        path = os.path.join(SRC_DIR, hive_setting.PAYMENT_PATH)
        config_file = Path(path)
        if not config_file.exists():
            logging.getLogger('v1 PaymentConfig').info("hive_setting.HIVE_PAYMENT_CONFIG dose not exist")
        else:
            logging.getLogger('v1 PaymentConfig').info("hive_setting.HIVE_PAYMENT_CONFIG: " + hive_setting.PAYMENT_PATH)
        with open(path, 'r')as fp:
            json_data = json.load(fp)
            PaymentConfig.config_info = json_data
            logging.getLogger("Hive Payment").info("Load payment config file:" + hive_setting.PAYMENT_PATH)

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
        if "pricingPlans" not in PaymentConfig.config_info:
            return None

        pricing_plan_list = PaymentConfig.config_info["pricingPlans"]
        for pricing_plan in pricing_plan_list:
            p_name = pricing_plan["name"]
            if p_name == name:
                return pricing_plan

        return None

    @staticmethod
    def get_backup_plan(name):
        if "backupPlans" not in PaymentConfig.config_info:
            return None

        backup_plan_list = PaymentConfig.config_info["backupPlans"]
        for backup_plan in backup_plan_list:
            p_name = backup_plan["name"]
            if p_name == name:
                return backup_plan

        return None

import json
import logging
from datetime import datetime
from pathlib import Path

from src.settings import hive_setting


class PaymentConfig:
    config_info = None

    @staticmethod
    def init_config():
        config_file = Path(hive_setting.PAYMENT_PATH)
        if not config_file.exists():
            print("hive_setting.HIVE_PAYMENT_CONFIG dose not exist")
        else:
            print("hive_setting.HIVE_PAYMENT_CONFIG:" + hive_setting.PAYMENT_PATH)
        with open(hive_setting.PAYMENT_PATH, 'r')as fp:
            json_data = json.load(fp)
            print(fp)
            PaymentConfig.config_info = json_data
            # print(json_data)
            logging.getLogger("Hive Payment").info("Load payment config file:" + hive_setting.PAYMENT_PATH)

    @staticmethod
    def get_all_package_info():
        return PaymentConfig.config_info

    @staticmethod
    def get_version():
        return PaymentConfig.config_info["version"]

    @staticmethod
    def get_free_vault_plan():
        return PaymentConfig.get_pricing_plan("Free")

    @staticmethod
    def is_free_plan(name: str):
        return name == 'Free'

    @staticmethod
    def get_free_backup_plan():
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

    @staticmethod
    def get_current_plan_remain_days(src_plan: dict, dst_end_timestamp, dst_plan: dict):
        """ Get the remaining days if the plan from 'src_plan' to 'dst_plan' """
        now = datetime.now().timestamp()

        # current end timestamp expired
        if dst_end_timestamp <= now:
            return 0

        # check if the current plan is free
        if src_plan['amount'] < 0.01 or src_plan['serviceDays'] == -1 or dst_end_timestamp == -1:
            return 0

        # destination plan is also free
        if dst_plan['amount'] < 0.01 or dst_plan['serviceDays'] == -1:
            return 0

        # other, take current plan as destination one by the ratio of amounts.
        days = (dst_end_timestamp - now) / (24 * 60 * 60)
        return days * src_plan['amount'] / dst_plan['amount']

    @staticmethod
    def get_plan_period(src_plan: dict, src_end_timestamp, dst_plan: dict):
        """ Get the period after move plan from 'src_plan' to 'dst_plan' """
        now = int(datetime.now().timestamp())
        remain_days = PaymentConfig.get_current_plan_remain_days(src_plan, src_end_timestamp, dst_plan)
        end_time = -1 if dst_plan['serviceDays'] <= 0 else now + (dst_plan['serviceDays'] + remain_days) * 24 * 60 * 60
        return now, int(end_time)

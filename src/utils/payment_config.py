import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.utils.http_exception import PricePlanNotFoundException
from src.settings import hive_setting


class PaymentConfig:
    config_info = None

    @staticmethod
    def init_config():
        config_file = Path(hive_setting.PAYMENT_CONFIG_PATH)
        if not config_file.exists():
            logging.getLogger('PaymentConfig').info("hive_setting.HIVE_PAYMENT_CONFIG dose not exist")
        else:
            logging.getLogger('PaymentConfig').info("hive_setting.HIVE_PAYMENT_CONFIG: " + hive_setting.PAYMENT_CONFIG_PATH)
        with open(hive_setting.PAYMENT_CONFIG_PATH, 'r')as fp:
            json_data = json.load(fp)
            PaymentConfig.config_info = json_data
            logging.getLogger("PaymentConfig").info("Load payment config file:" + hive_setting.PAYMENT_CONFIG_PATH)

    @staticmethod
    def get_all_package_info():
        return PaymentConfig.config_info

    @staticmethod
    def get_version():
        return PaymentConfig.config_info["version"]

    @staticmethod
    def get_free_vault_plan():
        return PaymentConfig.get_vault_plan("Free")

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
    def get_vault_plan(name) -> Optional[dict]:
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

    @staticmethod
    def get_price_plans(subscription, name):
        all_plans = PaymentConfig.get_all_package_info()
        result = {'version': all_plans.get('version', '1.0')}

        def filter_plans_by_name(plans):
            if not name:
                return plans
            return list(filter(lambda p: p.get('name') == name, plans))

        if subscription == 'all':
            result['backupPlans'] = filter_plans_by_name(all_plans.get('backupPlans', []))
            result['pricingPlans'] = filter_plans_by_name(all_plans.get('pricingPlans', []))
            if not result['backupPlans'] and not result['pricingPlans']:
                raise PricePlanNotFoundException()
        elif subscription == 'vault':
            result['pricingPlans'] = filter_plans_by_name(all_plans.get('pricingPlans', []))
            if not result['pricingPlans']:
                raise PricePlanNotFoundException()
        elif subscription == 'backup':
            result['backupPlans'] = filter_plans_by_name(all_plans.get('backupPlans', []))
            if not result['backupPlans']:
                raise PricePlanNotFoundException()
        return result

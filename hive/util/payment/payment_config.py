import json
import logging

from settings import HIVE_PAYMENT_CONFIG


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
    def get_free_trial_info():
        return PaymentConfig.config_info["Trial"]

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
    def get_package_info(name, price_name):
        packages = PaymentConfig.config_info["vaultPackages"]
        for package in packages:
            if name == package["name"]:
                pk = dict()
                pk["name"] = package["name"]
                pk["maxStorage"] = package["maxStorage"]
                pk["deleteIfUnpaidAfterDays"] = package["deleteIfUnpaidAfterDays"]
                pk["canReadIfUnpaid"] = package["canReadIfUnpaid"]
                for price in package["pricing"]:
                    if price_name == price["price_name"]:
                        pk["price_name"] = price["price_name"]
                        pk["amount"] = price["amount"]
                        pk["serviceDays"] = price["serviceDays"]
                        pk["currency"] = price["currency"]
                        return pk
        return None

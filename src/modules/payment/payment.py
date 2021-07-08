# -*- coding: utf-8 -*-

"""
The entrance for payment module.
"""
from src.modules.subscription.subscription import VaultSubscription
from src.utils.http_response import hive_restful_response


class Payment:
    def __init__(self):
        self.vault_subscription = VaultSubscription()

    @hive_restful_response
    def get_version(self):
        return {'version': self.vault_subscription.get_price_plans_version()}

    @hive_restful_response
    def place_order(self, json_body):
        pass

    @hive_restful_response
    def pay_order(self, order_id, json_body):
        pass

    @hive_restful_response
    def get_orders(self, subscription, order_id):
        pass

    @hive_restful_response
    def get_receipt_info(self, order_id):
        pass

# -*- coding: utf-8 -*-

"""
The entrance for payment module.
"""
from src.utils.http_response import hive_restful_response


class Payment:
    def __init__(self):
        pass

    @hive_restful_response
    def get_version(self):
        pass

    @hive_restful_response
    def place_order(self, json_body):
        pass

    @hive_restful_response
    def pay_order(self, order_id, json_body):
        pass

    @hive_restful_response
    def get_orders(self, subscription, order_id):
        pass

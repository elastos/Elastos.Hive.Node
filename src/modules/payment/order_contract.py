import os
import json
import typing as t

from web3 import Web3

from src import hive_setting


BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class OrderContract:
    def __init__(self):
        self.url = hive_setting.PAYMENT_CONTRACT_URL
        self.address = Web3.toChecksumAddress(hive_setting.PAYMENT_CONTRACT_ADDRESS)
        assert self.url and self.address and 'Please set payment url and address on the .env file.'
        with open(os.path.join(BASE_DIR, 'order_abi.json')) as f:
            self.abi = json.load(f)

    def __get_contract(self):
        web3 = Web3(Web3.HTTPProvider(self.url))
        return web3.eth.contract(address=self.address, abi=self.abi)

    def get_order(self, order_id) -> t.Optional[dict]:
        order = self.__get_contract().functions.getOrder(order_id).call()
        if not order:
            return None
        return {
            'orderId': order_id,
            'to': order.to,
            'memo': order.memo,
            'amount': order.amount
        }

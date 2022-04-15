# -*- coding: utf-8 -*-

"""
Testing file for the payment module.
"""

import unittest

from tests.utils.http_client import HttpClient
from tests import init_test


class PaymentTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/payment')
        self.order_id = '60ee8c056fdd17b16bb5b4c2'
        self.transaction_id = '280a24034bfb241c31b5a73c792c9d05df2b1f79bb98733c5358aeb909c27010'

    @staticmethod
    def _subscribe():
        HttpClient(f'/api/v2').put('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_get_version(self):
        response = self.cli.get('/version')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('version' in response.json())

    @unittest.skip
    def test02_place_order(self):
        response = self.cli.put('/order', body={'subscription': 'vault', 'pricing_name': 'Rookie'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue('order_id' in response.json())
        self.order_id = response.json().get('order_id')

    @unittest.skip
    def test03_pay_order(self):
        response = self.cli.post(f'/order/{self.order_id}', body={'transaction_id': self.transaction_id})
        self.assertEqual(response.status_code, 201)
        self.assertTrue('receipt_id' in response.json())
        self.assertTrue('order_id' in response.json())

    @unittest.skip
    def test04_get_orders(self):
        response = self.cli.get('/order?subscription=vault')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('orders' in response.json())

    @unittest.skip
    def test05_get_receipt(self):
        response = self.cli.get(f'/receipt?order_id={self.order_id}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('order_id' in response.json())
        self.assertTrue('receipt_id' in response.json())

# -*- coding: utf-8 -*-

"""
Testing file for payment module.
"""

import unittest

from tests.utils.http_client import HttpClient, TestConfig
from tests import init_test


class PaymentTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.test_config = TestConfig()
        self.cli = HttpClient(f'{self.test_config.host_url}/api/v2/payment')
        self.order_id = '60ed0f41a25b959b19a6acfb'
        self.transaction_id = '3e1465e1ad3519e8e7ded3078d03a7133840e876eb5eb5598fc221a9c183a778'

    @staticmethod
    def _subscribe():
        HttpClient(f'{TestConfig().host_url}/api/v2').put('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_get_version(self):
        response = self.cli.get('/version')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('version' in response.json())

    def test02_place_order(self):
        response = self.cli.put('/order', body={'subscription': 'vault', 'pricing_name': 'Rookie'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue('order_id' in response.json())
        self.order_id = response.json().get('order_id')

    def test03_pay_order(self):
        response = self.cli.post(f'/order/{self.order_id}', body={'transaction_id': self.transaction_id})
        self.assertEqual(response.status_code, 201)
        self.assertTrue('receipt_id' in response.json())
        self.assertTrue('order_id' in response.json())

    def test04_get_orders(self):
        response = self.cli.get('/order?subscription=vault')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('orders' in response.json())

    def test05_get_receipt(self):
        response = self.cli.get(f'/receipt?order_id={self.order_id}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('order_id' in response.json())
        self.assertTrue('receipt_id' in response.json())

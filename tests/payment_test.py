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

    def test01_get_version(self):
        response = self.cli.get('/version')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('version' in response.json())

    def test02_place_order(self):
        response = self.cli.put('/order', body={'subscription': 'vault', 'pricing_name': 'Rookie'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue('order_id' in response.json())

    def test03_pay_order(self):
        order_id = '60ecea45e8a83c0c31bf4e33'
        transaction_id = ''
        response = self.cli.post(f'/order/{order_id}', body={'subscription': 'vault', 'pricing_name': 'Rookie'})
        self.assertEqual(response.status_code, 201)
        self.assertTrue('order_id' in response.json())


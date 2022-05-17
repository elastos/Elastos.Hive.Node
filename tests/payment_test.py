# -*- coding: utf-8 -*-

"""
Testing file for the payment module.
"""

import unittest
from datetime import datetime

from src.modules.payment.order_contract import OrderContract
from src.utils.did.did_wrapper import JWT
from tests.utils.http_client import HttpClient
from tests import init_test


class PaymentTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/payment')

    @classmethod
    def setUpClass(cls):
        # subscript a vault if not exists
        HttpClient(f'/api/v2').put('/subscription/vault')

    def test01_get_version(self):
        response = self.cli.get('/version')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('version' in response.json())
        self.assertEqual(response.json()['version'], '1.0')

    @unittest.skip
    def test02_place_order(self):
        response = self.cli.put('/order', body={'subscription': 'vault', 'pricing_name': 'Rookie'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue('proof' in response.json())
        proof = response.json().get('proof')
        print(f'PROOF: {proof}')
        jwt = JWT.parse(proof)
        self.assertEqual(jwt.get_issuer(), self.cli.remote_resolver.get_node_did())
        self.assertEqual(jwt.get_audience(), self.cli.remote_resolver.get_current_user_did_str())
        self.assertTrue(jwt.get_expiration() > datetime.utcnow().timestamp())

    @unittest.skip
    def test03_get_contract_order(self):
        # To pay the order on contract, please use other script.
        # Here is for testing the contract to getting order information.
        contract = OrderContract()
        order = contract.get_order(4)
        print(f'get a contract order: {order}')

    @unittest.skip
    def test04_settle_order(self):
        contract_order_id = 4
        response = self.cli.post(f'/order/{contract_order_id}')
        self.assertEqual(response.status_code, 201)
        self.assertTrue('receipt_proof' in response.json())

    @unittest.skip
    def test05_get_orders(self):
        response = self.cli.get('/order?subscription=vault')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('orders' in response.json())

    @unittest.skip
    def test06_get_receipt(self):
        response = self.cli.get(f'/receipt?order_id={self.order_id}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('order_id' in response.json())
        self.assertTrue('receipt_id' in response.json())

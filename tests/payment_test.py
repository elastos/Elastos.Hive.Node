# -*- coding: utf-8 -*-

"""
Testing file for the payment module.
"""

import unittest
from datetime import datetime

from src.modules.payment.order_contract import OrderContract
from src.utils.did.did_wrapper import JWT
from tests.utils.http_client import HttpClient
from tests import init_test, test_log


class PaymentTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/payment')

    @classmethod
    def setUpClass(cls):
        # subscribe a vault if not exists
        HttpClient(f'/api/v2').put('/subscription/vault')
        # subscribe a backup if not exists
        HttpClient(f'/api/v2', is_backup_node=True).put('/subscription/backup')

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
        test_log(f'PROOF: {proof}')
        jwt = JWT.parse(proof)
        self.assertEqual(jwt.get_issuer(), self.cli.remote_resolver.get_node_did())
        self.assertEqual(jwt.get_audience(), self.cli.remote_resolver.get_current_user_did_str())
        self.assertTrue(jwt.get_expiration() > datetime.utcnow().timestamp())

    @unittest.skip
    def test02_place_order_backup(self):
        response = self.cli.put('/order', body={'subscription': 'backup', 'pricing_name': 'Rookie'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue('proof' in response.json())
        proof = response.json().get('proof')
        test_log(f'PROOF: {proof}')
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
        test_log(f'get a contract order: {order}')

    @unittest.skip
    def test04_settle_order(self):
        contract_order_id = 6
        response = self.cli.post(f'/order/{contract_order_id}')
        self.assertEqual(response.status_code, 201)
        self.assertTrue('receipt_proof' in response.json())
        proof = response.json().get('receipt_proof')
        test_log(f'RECEIPT PROOF: {proof}')
        jwt = JWT.parse(proof)
        self.assertEqual(jwt.get_issuer(), self.cli.remote_resolver.get_node_did())
        self.assertEqual(jwt.get_audience(), self.cli.remote_resolver.get_current_user_did_str())

    @unittest.skip
    def test05_get_orders(self):
        response = self.cli.get('/order?subscription=vault')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('orders' in response.json())
        test_log(f'orders: {response.json()["orders"]}')

    @unittest.skip
    def test06_get_receipts(self):
        contract_order_id = 6
        response = self.cli.get(f'/receipt?order_id={contract_order_id}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('receipts' in response.json())
        test_log(f'receipts: {response.json()["receipts"]}')

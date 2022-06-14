# -*- coding: utf-8 -*-

"""
Testing file for the payment module.
"""
import json
import unittest
from datetime import datetime

from src.modules.payment.order_contract import OrderContract
from src.utils.did.did_wrapper import JWT
from tests.utils.http_client import HttpClient
from tests import init_test, test_log
from tests.utils.resp_asserter import RA, DictAsserter


class UpgradeChecker(unittest.TestCase):
    """ Check the info in before and after upgrading. """

    def __init__(self, is_backup_node=False):
        super().__init__('runTest')
        self.client = HttpClient(f'/api/v2', is_backup_node=is_backup_node)
        self.link = '/subscription/vault' if not is_backup_node else '/subscription/backup'

    def __enter__(self):
        response = self.client.get(self.link)
        RA(response).assert_status(200)
        self.last_pricing_plan = RA(response).body().get('pricing_plan', str)
        self.last_storage_quota = RA(response).body().get('storage_quota', int)
        self.last_storage_used = RA(response).body().get('storage_used', int)
        end_time = RA(response).body().get('end_time', int)
        self.last_end_time = datetime.now().timestamp() if end_time <= 0 else end_time
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        response = self.client.get(self.link)
        RA(response).assert_status(200)
        pricing_plan = RA(response).body().get('pricing_plan', str)
        storage_quota = RA(response).body().get('storage_quota', int)
        storage_used = RA(response).body().get('storage_used', int)
        end_time = RA(response).body().get('end_time', int)
        self.assertEqual(pricing_plan, 'Rookie')
        self.assertEqual(storage_quota, 2000 * 1024 * 1024)
        self.assertEqual(storage_used, self.last_storage_used)
        self.assertLess(abs(end_time - self.last_end_time - 30 * 24 * 3600), 5 * 60)


class PaymentTestCase(unittest.TestCase):
    # TODO: change this to verify vault or backup
    IS_BACKUP_NODE = False

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/payment', is_backup_node=PaymentTestCase.IS_BACKUP_NODE)
        self.user_did = self.cli.get_current_did()

    @classmethod
    def setUpClass(cls):
        # make sure vault and backup exists
        if not PaymentTestCase.IS_BACKUP_NODE:
            HttpClient(f'/api/v2').put('/subscription/vault')
        else:
            HttpClient(f'/api/v2', is_backup_node=True).put('/subscription/backup')

    def test01_get_version(self):
        response = self.cli.get('/version')
        RA(response).assert_status(200)
        RA(response).body().assert_equal('version', '1.0')

    @unittest.skip
    def test02_place_order(self):
        subscription = 'vault' if not PaymentTestCase.IS_BACKUP_NODE else 'backup'

        def assert_info(info):
            info.assert_true('interim_orderid', str)
            info.assert_equal('subscription', subscription)
            info.assert_equal('pricing_plan', 'Rookie')
            info.assert_equal('paying_did', self.user_did)
            info.assert_equal('payment_amount', 2.5 if not PaymentTestCase.IS_BACKUP_NODE else 1.5)
            info.assert_greater('create_time', 0)
            info.assert_greater('expiration_time', 0)
            info.assert_true('receiving_address', str)
            info.assert_equal('state', 'normal')

        response = self.cli.put('/order', body={'subscription': subscription, 'pricing_name': 'Rookie'})
        RA(response).assert_status(200)
        assert_info(RA(response).body())

        jwt = JWT.parse(RA(response).body().get('proof', str))
        self.assertEqual(jwt.get_issuer(), self.cli.remote_resolver.get_node_did())
        self.assertEqual(jwt.get_audience(), self.user_did)
        self.assertTrue(jwt.get_expiration() > datetime.now().timestamp())
        assert_info(DictAsserter(**json.loads(jwt.get_claim_as_json('order'))))

    @unittest.skip
    def test03_get_contract_order(self):
        # To pay the order on contract, please use other script.
        # Here is for testing the contract to getting order information.
        contract = OrderContract()
        order = contract.get_order(0)  # TODO:
        test_log(f'get a contract order: {order}')

    @unittest.skip
    def test04_settle_order(self):
        contract_order_id = 1  # TODO:

        def assert_info(info):
            info.assert_true('receipt_id', str)
            info.assert_equal('order_id', contract_order_id)
            info.assert_equal('subscription', 'vault' if not PaymentTestCase.IS_BACKUP_NODE else 'backup')
            info.assert_equal('pricing_plan', 'Rookie')
            info.assert_equal('payment_amount', 2.5 if not PaymentTestCase.IS_BACKUP_NODE else 1.5)
            info.assert_equal('paid_did', self.user_did)
            info.assert_greater('create_time', 0)
            info.assert_true('receiving_address', str)

        with UpgradeChecker(is_backup_node=PaymentTestCase.IS_BACKUP_NODE) as checker:
            response = self.cli.post(f'/order/{contract_order_id}')
            RA(response).assert_status(201)
            assert_info(RA(response).body())

            jwt = JWT.parse(RA(response).body().get('receipt_proof', str))
            self.assertEqual(jwt.get_issuer(), self.cli.remote_resolver.get_node_did())
            self.assertEqual(jwt.get_audience(), self.user_did)
            assert_info(DictAsserter(**json.loads(jwt.get_claim_as_json('receipt'))))

    @unittest.skip
    def test05_get_orders(self):
        subscription = 'vault' if not PaymentTestCase.IS_BACKUP_NODE else 'backup'
        response = self.cli.get(f'/order?subscription={subscription}')
        RA(response).assert_status(200)
        orders = RA(response).body().get('orders', list)
        self.assertGreater(len(orders), 0)

        info = DictAsserter(**orders[0])
        order_id = info['order_id']
        self.assertTrue(order_id is None or order_id >= 0)
        info.assert_true('interim_orderid', str)
        info.assert_equal('subscription', subscription)
        info.assert_equal('pricing_plan', 'Rookie')
        info.assert_equal('paying_did', self.user_did)
        info.assert_equal('payment_amount', 2.5 if not PaymentTestCase.IS_BACKUP_NODE else 1.5)
        info.assert_greater('create_time', 0)
        info.assert_greater('expiration_time', 0)
        info.assert_true('receiving_address', str)
        info.assert_in('state', ['normal', 'expired', 'paid', 'archive'])
        info.assert_true('proof', str)

    @unittest.skip
    def test06_get_receipts(self):
        contract_order_id = 2  # TODO: same as settleOrder()
        response = self.cli.get(f'/receipt?order_id={contract_order_id}')
        RA(response).assert_status(200)
        receipts = RA(response).body().get('receipts', list)
        self.assertTrue(len(receipts), 1)

        info = DictAsserter(**receipts[0])
        info.assert_true('receipt_id', str)
        info.assert_equal('order_id', contract_order_id)
        info.assert_equal('subscription', 'vault' if not PaymentTestCase.IS_BACKUP_NODE else 'backup')
        info.assert_equal('pricing_plan', 'Rookie')
        info.assert_equal('payment_amount', 2.5 if not PaymentTestCase.IS_BACKUP_NODE else 1.5)
        info.assert_equal('paid_did', self.user_did)
        info.assert_greater('create_time', 0)
        info.assert_true('receiving_address', str)
        info.assert_true('receipt_proof', str)

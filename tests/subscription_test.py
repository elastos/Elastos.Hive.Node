# -*- coding: utf-8 -*-

"""
Testing file for scripting module.
"""

import unittest

from tests.utils.http_client import HttpClient
from tests import init_test


class SubscriptionTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2')
        self.backup_cli = HttpClient(f'/api/v2', is_backup_node=True)

    def test01_vault_subscribe_free(self):
        response = self.cli.put('/subscription/vault')
        self.assertTrue(response.status_code in [200, 455])

    @unittest.skip
    def test02_vault_activate(self):
        response = self.cli.post('/subscription/vault?op=activation')
        self.assertEqual(response.status_code, 201)

    def test03_vault_get_info(self):
        response = self.cli.get('/subscription/vault')
        self.assertEqual(response.status_code, 200)

    @unittest.skip
    def test04_vault_deactivate(self):
        response = self.cli.post('/subscription/vault?op=deactivation')
        self.assertEqual(response.status_code, 201)

    @unittest.skip
    def test05_vault_unsubscribe(self):
        response = self.cli.delete('/subscription/vault')
        self.assertEqual(response.status_code, 204)

    def test06_price_plan(self):
        response = self.cli.get('/subscription/pricing_plan?subscription=all&name=Free')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('backupPlans' in response.json())
        self.assertTrue('pricingPlans' in response.json())

    def test07_backup_subscribe_free(self):
        response = self.backup_cli.put('/node-subscription/backup')
        self.assertTrue(response.status_code in [200, 455])

    def test08_backup_get_info(self):
        response = self.backup_cli.get('/node-subscription/backup')
        self.assertEqual(response.status_code, 200)

    def test09_backup_unsubscribe(self):
        response = self.backup_cli.delete('/node-subscription/backup')
        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()

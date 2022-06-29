# -*- coding: utf-8 -*-

"""
Testing file for the scripting module.
"""

import unittest

from tests.utils.http_client import HttpClient
from tests import init_test, test_log


class SubscriptionTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest', is_did2=False):
        """ MUST add params at the end of the list, or error from test engine """
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2', is_did2=is_did2)
        self.backup_cli = HttpClient(f'/api/v2', is_did2=is_did2, is_backup_node=True)

    def test01_vault_subscribe(self):
        response = self.cli.put('/subscription/vault')
        self.assertIn(response.status_code, [200, 455])

    def test02_vault_activate(self):
        response = self.cli.post('/subscription/vault?op=activation')
        self.assertEqual(response.status_code, 201)

    def test03_vault_get_info(self):
        response = self.cli.get('/subscription/vault')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.json(), dict))
        test_log(f'vault info: {response.json()}')

    def test04_vault_get_app_stats(self):
        response = self.cli.get('/subscription/vault/app_stats')
        self.assertTrue(response.status_code in [200, 404])

    def test05_vault_deactivate(self):
        response = self.cli.post('/subscription/vault?op=deactivation')
        self.assertEqual(response.status_code, 201)

    def test06_vault_unsubscribe(self):
        response = self.cli.delete('/subscription/vault')
        self.assertIn(response.status_code, [204, 404])

    def test07_price_plan(self):
        response = self.cli.get('/subscription/pricing_plan?subscription=all&name=Free')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('backupPlans' in response.json())
        self.assertTrue('pricingPlans' in response.json())

    def test08_backup_subscribe(self):
        response = self.backup_cli.put('/subscription/backup')
        self.assertIn(response.status_code, [200, 455])

    def test09_backup_get_info(self):
        response = self.backup_cli.get('/subscription/backup')
        self.assertEqual(response.status_code, 200)

    def test10_backup_unsubscribe(self):
        response = self.backup_cli.delete('/subscription/backup')
        self.assertIn(response.status_code, [204, 404])


if __name__ == '__main__':
    unittest.main()

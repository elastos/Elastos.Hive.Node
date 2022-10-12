# -*- coding: utf-8 -*-

"""
Testing file for the scripting module.
"""

import unittest

from tests.utils.http_client import HttpClient
from tests import init_test, test_log, RA, HttpCode


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
        RA(response).body().assert_greater_equal('app_count', 1)

    def test02_vault_activate(self):
        response = self.cli.post('/subscription/vault?op=activation')
        self.assertEqual(response.status_code, 201)

    def test03_vault_get_info(self):
        response = self.cli.get('/subscription/vault')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.json(), dict))
        test_log(f'vault info: {response.json()}')
        RA(response).body().assert_greater_equal('app_count', 1)

    def test04_vault_get_app_stats(self):
        response = self.cli.get('/subscription/vault/app_stats')
        self.assertTrue(response.status_code in [200, 404])

    def test05_vault_deactivate(self):
        response = self.cli.post('/subscription/vault?op=deactivation')
        self.assertEqual(response.status_code, 201)

    def test06_vault_unsubscribe(self):
        response = self.cli.delete('/subscription/vault?force=true')
        self.assertIn(response.status_code, [204, 404])

    def test07_vault_unsubscribe_without_force(self):
        """ if unsubscribe without force, the data will keep until next subscribing """

        # subscribe
        response = self.cli.put('/subscription/vault')
        RA(response).assert_status(HttpCode.OK)

        # upload a file
        file_name, file_content = 'abc.txt', '1234567890'
        response = self.cli.put(f'/vault/files/{file_name}', file_content.encode(), is_json=False)
        RA(response).assert_status(HttpCode.OK)

        # unsubscribe without force
        response = self.cli.delete('/subscription/vault?force=false')
        RA(response).assert_status(HttpCode.NO_CONTENT)

        # get the info. of the vault
        response = self.cli.get('/subscription/vault')
        RA(response).assert_status(HttpCode.NOT_FOUND)

        # subscribe again
        response = self.cli.put('/subscription/vault')
        RA(response).assert_status(HttpCode.OK)

        # download file
        response = self.cli.get(f'/vault/files/{file_name}')
        RA(response).assert_status(HttpCode.OK)
        self.assertEqual(response.text, file_content)

        # unsubscribe with force
        response = self.cli.delete('/subscription/vault?force=true')
        RA(response).assert_status(HttpCode.NO_CONTENT)

    def test10_price_plan(self):
        response = self.cli.get('/subscription/pricing_plan?subscription=all&name=Free')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('backupPlans' in response.json())
        self.assertTrue('pricingPlans' in response.json())

    def test20_backup_subscribe(self):
        response = self.backup_cli.put('/subscription/backup')
        self.assertIn(response.status_code, [200, 455])

    def test21_backup_get_info(self):
        response = self.backup_cli.get('/subscription/backup')
        self.assertEqual(response.status_code, 200)

    def test22_backup_unsubscribe(self):
        response = self.backup_cli.delete('/subscription/backup')
        self.assertIn(response.status_code, [204, 404])


if __name__ == '__main__':
    unittest.main()

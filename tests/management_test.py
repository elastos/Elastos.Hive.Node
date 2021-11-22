# -*- coding: utf-8 -*-

"""
Testing file for the management module.
"""
import unittest

from tests.utils.http_client import HttpClient
from tests import init_test


class ManagementTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/management')
        self.cli_owner = HttpClient(f'/api/v2/management', is_owner=True)
        self.backup_cli_owner = HttpClient(f'/api/v2/management', is_owner=True, is_backup_node=True)

    @staticmethod
    def _subscribe():
        col_name = 'test_management'
        vault_cli = HttpClient(f'/api/v2')
        response = vault_cli.put('/subscription/vault')
        response = vault_cli.put(f'/vault/db/collections/{col_name}')
        response = vault_cli.post(f'/vault/db/collection/{col_name}', body={
            "document": [{
                "author": "john doe1",
                "title": "Eve for Dummies1"
            }],
            "options": {
                "bypass_document_validation": False,
                "ordered": True
            }})
        HttpClient(f'/api/v2', is_backup_node=True).put('/subscription/backup')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_get_vaults(self):
        response = self.cli_owner.get(f'/node/vaults')
        self.assertEqual(response.status_code, 200)

    def test02_get_backups(self):
        response = self.backup_cli_owner.get(f'/node/backups')
        self.assertEqual(response.status_code, 200)

    def test03_get_users(self):
        response = self.cli_owner.get(f'/node/users')
        self.assertEqual(response.status_code, 200)

    def test04_get_payments(self):
        response = self.cli_owner.get(f'/node/payments')
        self.assertTrue(response.status_code in [200, 404])

    @unittest.skip
    def test05_delete_vaults(self):
        response = self.cli_owner.delete(f'/node/vaults', body={"ids": ["6195afc60d16358a597586ce", ]}, is_json=True)
        self.assertEqual(response.status_code, 204)

    @unittest.skip
    def test06_delete_backups(self):
        response = self.cli_owner.delete(f'/node/backups', body={"ids": ["6195aff13e58141a70bf8f0b", ]}, is_json=True)
        self.assertEqual(response.status_code, 204)

    def test07_get_apps(self):
        response = self.cli.get(f'/vault/apps')
        self.assertEqual(response.status_code, 200)

    @unittest.skip
    def test08_delete_apps(self):
        response = self.cli.delete(f'/vault/apps', is_json=True,
                                   body={"app_dids": ["did:elastos:ienWaA6sfWETz6gVzX78SNytx8VUwDzxai", ]})
        self.assertEqual(response.status_code, 200)

# -*- coding: utf-8 -*-

"""
Testing file for the provider module.
"""
import unittest

from tests.utils.http_client import HttpClient
from tests import init_test


class ProviderTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli_owner = HttpClient(f'/api/v2/provider', is_owner=True)
        self.cli_node = HttpClient(f'/api/v2/node', is_owner=False)
        self.backup_cli_owner = HttpClient(f'/api/v2/provider', is_owner=True, is_backup_node=True)

    @staticmethod
    def _subscribe():
        HttpClient(f'/api/v2').put('/subscription/vault')
        HttpClient(f'/api/v2', is_backup_node=True).put('/subscription/backup')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_get_vaults(self):
        response = self.cli_owner.get(f'/vaults')
        self.assertEqual(response.status_code, 200)

    def test02_get_backups(self):
        response = self.backup_cli_owner.get(f'/backups')
        self.assertEqual(response.status_code, 200)

    def test03_get_filled_orders(self):
        response = self.cli_owner.get(f'/filled_orders')
        self.assertTrue(response.status_code in [200, 404])

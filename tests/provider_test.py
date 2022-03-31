# -*- coding: utf-8 -*-

"""
Testing file for the provider module.
"""
import json
import unittest

from src.utils_v1.did.eladid import ffi, lib
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

    def test01_get_node_info(self):
        response = self.cli_node.get(f'/info')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json().get('service_did'))
        self.assertTrue(response.json().get('owner_did'))
        self.verify_ownership_presentation(response.json().get('ownership_presentation'))
        self.assertTrue(response.json().get('version'))
        self.assertTrue(response.json().get('last_commit_id'))

    def verify_ownership_presentation(self, presentation: any):
        if type(presentation) is not dict:
            self.assertTrue(False, 'the ownership presentation is invalid.')
        presentation_str = json.dumps(presentation)
        vp = lib.Presentation_FromJson(presentation_str.encode())
        self.assertEqual(lib.Presentation_IsValid(vp), 1)

    def test02_get_vaults(self):
        response = self.cli_owner.get(f'/vaults')
        self.assertEqual(response.status_code, 200)

    def test03_get_backups(self):
        response = self.backup_cli_owner.get(f'/backups')
        self.assertEqual(response.status_code, 200)

    def test04_get_filled_orders(self):
        response = self.cli_owner.get(f'/filled_orders')
        self.assertTrue(response.status_code in [200, 404])

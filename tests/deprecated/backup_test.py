# -*- coding: utf-8 -*-

"""
Testing file for the backup module.
"""
import unittest

from tests import init_test
from tests.utils.http_client import HttpClient


@unittest.skip
class BackupTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2')

    @staticmethod
    def _subscribe():
        HttpClient(f'/api/v2').put('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_get_state(self):
        r = self.cli.get('/vault-deprecated/content')
        self.assertEqual(r.status_code, 200)

    @unittest.skip
    def test02_backup(self):
        self.backup(self.cli.get_backup_credential())

    @unittest.skip
    def test03_restore(self):
        self.restore(self.cli.get_backup_credential())

    def backup(self, credential):
        r = self.cli.post('/vault-deprecated/content?to=hive_node', body={'credential': credential})
        self.assertEqual(r.status_code, 201)

    def restore(self, credential):
        r = self.cli.post('/vault-deprecated/content?from=hive_node', body={'credential': credential})
        self.assertEqual(r.status_code, 201)

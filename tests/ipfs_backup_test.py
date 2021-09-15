# -*- coding: utf-8 -*-

"""
Testing file for ipfs-backup module.
"""

import unittest

from tests import init_test
from tests.utils.http_client import HttpClient


class IpfsBackupTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2')
        self.backup_cli = HttpClient(f'/api/v2', is_backup_node=True)

    @staticmethod
    def _subscribe():
        HttpClient(f'/api/v2').put('/subscription/vault')
        HttpClient(f'/api/v2', is_backup_node=True).put('/subscription/backup')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_backup(self):
        self.backup(self.cli.get_backup_credential())

    @unittest.skip
    def test02_restore(self):
        self.restore(self.cli.get_backup_credential())

    def backup(self, credential):
        r = self.cli.post('/ipfs-vault/content?to=hive_node', body={'credential': credential})
        self.assertEqual(r.status_code, 201)

    def restore(self, credential):
        r = self.cli.post('/ipfs-vault/content?from=hive_node', body={'credential': credential})
        self.assertEqual(r.status_code, 201)

    @unittest.skip
    def test03_promotion(self):
        # PREPARE: backup and remove the vault for local test.
        r = self.backup_cli.post('/ipfs-backup/promotion')
        self.assertEqual(r.status_code, 201)


if __name__ == '__main__':
    unittest.main()

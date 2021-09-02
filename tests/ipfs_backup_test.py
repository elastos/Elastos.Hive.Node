# -*- coding: utf-8 -*-

"""
Testing file for ipfs-backup module.
"""

import unittest

from tests import init_test
from tests.utils.http_client import TestConfig, HttpClient, RemoteResolver


class IpfsBackupTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.test_config = TestConfig()
        self.cli = HttpClient(f'{self.test_config.host_url}/api/v2')
        self.remote_resolver = RemoteResolver()

    @staticmethod
    def _subscribe():
        HttpClient(f'{TestConfig().host_url}/api/v2').put('/subscription/backup')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_backup(self):
        self.backup(self.remote_resolver.get_backup_credential(self.test_config.host_url))

    @unittest.skip
    def test02_restore(self):
        self.restore(self.remote_resolver.get_backup_credential(self.test_config.host_url))

    def backup(self, credential):
        r = self.cli.post('/ipfs-vault/content?to=hive_node', body={'credential': credential})
        self.assertEqual(r.status_code, 201)

    def restore(self, credential):
        r = self.cli.post('/ipfs-vault/content?from=hive_node', body={'credential': credential})
        self.assertEqual(r.status_code, 201)

    @unittest.skip
    def test03_promotion(self):
        # PREPARE: backup and remove the vault for local test.
        r = self.cli.post('/ipfs-backup/promotion')
        self.assertEqual(r.status_code, 201)


if __name__ == '__main__':
    unittest.main()

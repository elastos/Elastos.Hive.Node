# -*- coding: utf-8 -*-

"""
Testing file for ipfs-backup module.
"""
import time
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

    @staticmethod
    def _unsubscribe():
        HttpClient(f'/api/v2', is_backup_node=True).delete('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_subscribe(self):
        response = self.backup_cli.put('/ipfs-subscription/backup')
        self.assertTrue(response.status_code in [200, 455])

    def test02_get_info(self):
        response = self.backup_cli.get('/ipfs-subscription/backup')
        self.assertEqual(response.status_code, 200)

    def test03_backup(self):
        r = self.cli.post('/ipfs-vault/content?to=hive_node',
                          body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)
        time.sleep(10)

    @unittest.skip
    def test03_backup_force(self):
        r = self.cli.post('/ipfs-vault/content?to=hive_node&is_force=True',
                          body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)

    def test04_state(self):
        r = self.cli.get('/ipfs-vault/content')
        self.assertEqual(r.status_code, 200)

    def test05_restore(self):
        r = self.cli.post('/ipfs-vault/content?from=hive_node',
                          body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)
        time.sleep(10)

    @unittest.skip
    def test05_restore_force(self):
        r = self.cli.post('/ipfs-vault/content?from=hive_node&is_force=True',
                          body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)

    @unittest.skip
    def test06_promotion(self):
        # PREPARE: backup and remove the vault for local test.
        self.__class__._unsubscribe()
        r = self.backup_cli.post('/ipfs-backup/promotion')
        self.assertEqual(r.status_code, 201)

    @unittest.skip
    def test07_unsubscribe(self):
        response = self.backup_cli.delete('/ipfs-subscription/backup')
        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()

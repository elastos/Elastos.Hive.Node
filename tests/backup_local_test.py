# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-backup module.
INFO: To run this on travis which needs support mongodb dump first.
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
    def _subscribe_vault():
        HttpClient(f'/api/v2').put('/subscription/vault')

    @staticmethod
    def _subscribe_backup():
        HttpClient(f'/api/v2', is_backup_node=True).put('/subscription/backup')

    @staticmethod
    def _unsubscribe_vault_on_backup_node():
        HttpClient(f'/api/v2', is_backup_node=True).delete('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe_vault()
        cls._subscribe_backup()

    def check_result_success(self):
        # waiting for the backup process to end
        max_timestamp = time.time() + 60
        while time.time() < max_timestamp:
            r = self.cli.get('/vault/content')
            self.assertEqual(r.status_code, 200)
            self.assertTrue('result' in r.json())
            if r.json()['result'] == 'process':
                continue
            elif r.json()['result'] == 'failed':
                self.assertTrue(False, r.json()['message'])
            elif r.json()['result'] == 'success':
                break
            else:
                self.assertTrue(False, f'Unknown result {r.json()["result"]} for the backup process.')
            time.sleep(5)

    def test01_backup(self):
        r = self.cli.post('/vault/content?to=hive_node',
                          body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)
        self.check_result_success()

    def test02_restore(self):
        r = self.cli.post('/vault/content?from=hive_node',
                          body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)
        self.check_result_success()


if __name__ == '__main__':
    unittest.main()

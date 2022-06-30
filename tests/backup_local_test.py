# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-backup module.
INFO: To run this on travis which needs support mongodb dump first.
"""
import time
import unittest

from tests import init_test, test_log, HttpCode
from tests.database_test import DatabaseTestCase
from tests.utils.http_client import HttpClient
from tests.subscription_test import SubscriptionTestCase
from tests.files_test import IpfsFilesTestCase


class IpfsBackupTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        """
        TODO: only run on local because travis does not support mongo dump command.
        """

        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2')
        self.backup_cli = HttpClient(f'/api/v2', is_backup_node=True)
        self.subscription = SubscriptionTestCase()

    @classmethod
    def setUpClass(cls):
        SubscriptionTestCase().test06_vault_unsubscribe()

    def check_result(self, failed_message=None):
        # waiting for the backup process to end
        max_timestamp = time.time() + 60
        while time.time() < max_timestamp:
            r = self.cli.get('/vault/content')
            self.assertEqual(r.status_code, 200)

            self.assertTrue('result' in r.json())
            if r.json()['result'] == 'failed':
                if failed_message is not None:
                    self.assertIn(failed_message, r.json()["message"])
                test_log(f'failed with message: {r.json()["message"]}')
                break
            elif r.json()['result'] == 'success':
                if failed_message is not None:
                    self.assertTrue(False, 'result state should not be successful')
                test_log(f'backup or restore successfully')
                break

            test_log(f'backup & restore is in progress ("{r.json()["result"]}", {r.json()["message"]}), wait')
            time.sleep(1)

    def test01_backup_restore_failed(self):
        # prepare vault
        self.subscription.test01_vault_subscribe()

        # backup without backup service
        self.subscription.test10_backup_unsubscribe()
        r = self.cli.post('/vault/content?to=hive_node', body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, HttpCode.BAD_REQUEST)

        # prepare backup service
        self.subscription.test08_backup_subscribe()

        # restore without backup data of backup service
        r = self.cli.post('/vault/content?from=hive_node', body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, HttpCode.BAD_REQUEST)

    def test02_backup(self):
        self.subscription.test01_vault_subscribe()
        self.subscription.test08_backup_subscribe()

        # prepare documents and files.
        database_test, files_test = DatabaseTestCase(), IpfsFilesTestCase()
        database_test.test01_create_collection()
        database_test.test02_insert()
        database_test.test02_insert_with_options()
        files_test.test01_upload_file()

        # do backup and make sure successful
        r = self.cli.post('/vault/content?to=hive_node', body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)
        self.check_result()

    def test03_restore(self):
        self.subscription.test06_vault_unsubscribe()
        self.subscription.test01_vault_subscribe()

        # do restore and make sure successful
        r = self.cli.post('/vault/content?from=hive_node', body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)
        self.check_result()

        # check files and documents
        database_test, files_test = DatabaseTestCase(), IpfsFilesTestCase()
        database_test.test05_find()
        files_test.test02_download_file()


if __name__ == '__main__':
    unittest.main()

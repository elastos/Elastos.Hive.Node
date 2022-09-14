# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-backup module.
INFO: To run this on travis which needs support mongodb dump first.
"""
import time
import unittest

from tests import init_test, test_log, HttpCode, RA
from tests.utils.http_client import HttpClient


class IpfsBackupTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        """
        TODO: only run on local because travis does not support mongo dump command.
        """

        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2')
        self.backup_cli = HttpClient(f'/api/v2', is_backup_node=True)

        # documents
        self.collection_name = 'backup_collection'

        # for uploading, and copying back
        self.src_file_name = 'ipfs_src_file.node.txt'
        self.src_file_content = 'File Content: 12345678' + ('9' * 200)

    def vault_subscribe(self):
        response = self.cli.put('/subscription/vault')
        self.assertIn(response.status_code, [200, 455])

    def vault_unsubscribe(self):
        response = self.cli.delete('/subscription/vault')
        self.assertIn(response.status_code, [204, 404])

    def backup_subscribe(self):
        response = self.backup_cli.put('/subscription/backup')
        self.assertIn(response.status_code, [200, 455])

    def backup_unsubscribe(self):
        response = self.backup_cli.delete('/subscription/backup')
        self.assertIn(response.status_code, [204, 404])

    def prepare_documents(self):
        response = self.cli.put(f'/vault/db/collections/{self.collection_name}')
        RA(response).assert_status(200, 455)

        def create_doc(index):
            return {'author': 'Alice',
                    'title': f'The Metrix {index}',
                    'words_count': 10000 * index}

        response = self.cli.post(f'/vault/db/collection/{self.collection_name}', body={
            'document': [create_doc(i+1) for i in range(2)]
        })
        RA(response).assert_status(201)

    def prepare_files(self):
        file_name, file_content = self.src_file_name, self.src_file_content.encode()
        response = self.cli.put(f'/vault/files/{file_name}', file_content, is_json=False)
        self.assertEqual(response.status_code, 200)

    def verify_documents(self):
        response = self.cli.get(f'/vault/db/{self.collection_name}' + '?filter={"author":"Alice"}')
        RA(response).assert_status(200)
        self.assertEqual(len(RA(response).body().get('items', list)), 2)

        response = self.cli.delete(f'/vault/db/{self.collection_name}')
        RA(response).assert_status(204)

    def verify_files(self):
        response = self.cli.get(f'/vault/files/{self.src_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.src_file_content)

        response = self.cli.delete(f'/vault/files/{self.src_file_name}')
        self.assertTrue(response.status_code in [204, 404])

    def check_result(self):
        # waiting for the backup process to end
        max_timestamp = time.time() + 60
        while time.time() < max_timestamp:
            r = self.cli.get('/vault/content')
            self.assertEqual(r.status_code, 200)

            self.assertTrue('result' in r.json())
            if r.json()['result'] == 'failed':
                self.assertTrue(False, f'Backup & restore failed: {r.json()["message"]}')
                test_log(f'failed with message: {r.json()["message"]}')
                break
            elif r.json()['result'] == 'success':
                test_log(f'backup or restore successfully')
                break

            test_log(f'backup & restore is in progress ("{r.json()["result"]}", {r.json()["message"]}), wait')
            time.sleep(1)

    def test01_backup_restore_failed(self):
        # prepare vault
        self.vault_subscribe()

        # backup without backup service
        self.backup_unsubscribe()
        r = self.cli.post('/vault/content?to=hive_node', body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, HttpCode.BAD_REQUEST)

        # prepare backup service
        self.backup_subscribe()
        r = self.cli.post('/vault/content?from=hive_node', body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, HttpCode.BAD_REQUEST)

    def test02_backup(self):
        self.vault_unsubscribe()
        self.vault_subscribe()
        self.backup_subscribe()

        self.prepare_documents()
        self.prepare_files()

        # do backup and make sure successful
        r = self.cli.post('/vault/content?to=hive_node', body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)
        self.check_result()

    def test03_restore(self):
        self.vault_unsubscribe()
        self.vault_subscribe()

        # do restore and make sure successful
        r = self.cli.post('/vault/content?from=hive_node', body={'credential': self.cli.get_backup_credential()})
        self.assertEqual(r.status_code, 201)
        self.check_result()

        self.verify_files()
        self.verify_documents()


if __name__ == '__main__':
    unittest.main()

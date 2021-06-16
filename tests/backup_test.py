# -*- coding: utf-8 -*-

"""
Testing file for backup module.
"""
import unittest

from tests import init_test
from tests.utils.http_client import HttpClient, RemoteResolver


class BackupTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.host_url = 'http://localhost:5000'
        self.cli = HttpClient(f'{self.host_url}/api/v2')
        self.remote_resolver = RemoteResolver()

    def test01_get_state(self):
        r = self.cli.get('/vault/content')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['state'], 'stop')
        self.assertEqual(r.json()['result'], 'success')

    def test02_backup(self):
        # self.create_backup_vault()
        # self.prepare_backup_files()
        self.backup(self.remote_resolver.get_backup_credential(self.host_url))

    def test03_restore(self):
        # self.create_backup_vault()
        # self.prepare_restore_files()
        self.restore(self.remote_resolver.get_backup_credential())

    def create_backup_vault(self):
        response = self.cli.put('/subscription/backup')
        is_success = response.status_code == 200
        is_exist = response.status_code == 455
        self.assertTrue(is_success or is_exist)

    def prepare_backup_files(self):
        # TODO: add data to database.
        files = {
            'test0.txt': 'this is a test 0 file',
            'f1/test1.txt': 'this is a test 1 file',
            'f1/test1_2.txt': 'this is a test 1_2 file',
            'f2/f1/test2.txt': 'this is a test 2 file',
            'f2/f1/test2_2.txt': 'this is a test 2_2 file'
        }
        for name, content in files.items():
            self.upload_file(name, content)

    def prepare_restore_files(self):
        # TODO: add data to database.
        files = {
            'test1.txt': 'this is a test 0 file by restore',
            "f1/test1.txt": "this is a test 1 file by restore",
            "f2/f1/test2.txt": "this is a test 2 file by restore"
        }
        for name, content in files.items():
            self.upload_file(name, content)

        delete_files = ['test0.txt', 'f1/test1_2.txt', 'f2/f1/test2_2.txt']
        for name in delete_files:
            self.__delete_file(name)

    def __delete_file(self, file_name):
        response = self.cli.delete(f'/files/{file_name}')
        self.assertEqual(response.status_code, 204)

    def upload_file(self, name, content):
        response = self.cli.put(f'/vault/files/{name}',
                                content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), name)
        self.__check_remote_file_exist(name)

    def __check_remote_file_exist(self, file_name):
        response = self.cli.get(f'/vault/files/{file_name}?comp=metadata')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), file_name)
        return response.json()

    def backup(self, credential):
        r = self.cli.post('/vault/content?to=hive_node', body={'credential': credential}, is_json=True)
        self.assertEqual(r.status_code, 201)

    def restore(self, credential):
        r = self.cli.post('/vault/content?from=hive_node', body={'credential': credential}, is_json=True)
        self.assertEqual(r.status_code, 201)

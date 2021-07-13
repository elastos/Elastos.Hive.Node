# -*- coding: utf-8 -*-

"""
Testing file for scripting module.
"""

import unittest
import json

from tests.utils.http_client import HttpClient, TestConfig
from tests import init_test
from tests_v1 import test_common


class ScriptingTestCase(unittest.TestCase):
    collection_name = 'script_database'

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.test_config = TestConfig()
        self.cli = HttpClient(f'{self.test_config.host_url}/api/v2/vault')
        self.file_name = 'test.txt'
        self.file_content = 'File Content: 12345678'
        self.did = 'did:elastos:ioRn3eEopRjA7CBRrrWQWzttAfXAjzvKMx'
        self.app_did = test_common.app_id

    @staticmethod
    def _subscribe():
        HttpClient(f'{TestConfig().host_url}/api/v2').put('/subscription/vault')

    @staticmethod
    def _create_collection():
        HttpClient(f'{TestConfig().host_url}/api/v2/vault').put(f'/db/collections/{ScriptingTestCase.collection_name}')

    @staticmethod
    def _delete_collection():
        HttpClient(f'{TestConfig().host_url}/api/v2/vault').delete(f'/db/{ScriptingTestCase.collection_name}')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()
        cls._delete_collection()
        cls._create_collection()

    @classmethod
    def tearDownClass(cls):
        ScriptingTestCase._delete_collection()

    def __register_script(self, script_name, body):
        response = self.cli.put(f'/scripting/{script_name}', body)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.text)

    def __call_script(self, script_name, body, is_raw=False):
        response = self.cli.patch(f'/scripting/{script_name}', body)
        self.assertEqual(response.status_code, 200)
        return response.text if is_raw else json.loads(response.text)

    def test01_register_script(self):
        self.__register_script('database_insert', {
            "executable": {
                "output": True,
                "name": "database_insert",
                "type": "insert",
                "body": {
                    "collection": self.collection_name,
                    "document": {
                        "author": "$params.author",
                        "content": "$params.content"
                    },
                    "options": {
                        "ordered": True,
                        "bypass_document_validation": False
                    }
                }
            }
        })

    def test02_call_script(self):
        self.__call_script('database_insert', {
            "params": {
                "author": "John",
                "content": "message"
            }
        })

    def test03_call_script_url(self):
        response = self.cli.get('/scripting/database_insert/@'
                                '/%7B%22author%22%3A%22John2%22%2C%22content%22%3A%22message2%22%7D')
        self.assertEqual(response.status_code, 200)

    def __call_script_for_transaction_id(self, script_name):
        response_body = self.__call_script(script_name, {
            "params": {
                "path": self.file_name
            }
        })
        self.assertEqual(type(response_body), dict)
        self.assertTrue(script_name in response_body)
        self.assertEqual(type(response_body[script_name]), dict)
        self.assertTrue('transaction_id' in response_body[script_name])
        return response_body[script_name]['transaction_id']

    def test04_find_with_default_output(self):
        name = 'database_find'
        col_filter = {'author': '$params.author'}
        body = self.__set_and_call_script(name, {'condition': {
                'name': 'verify_user_permission',
                'type': 'queryHasResults',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            }, 'executable': {
                'name': name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            }}, {'context': {
                'target_did': self.did,
                'target_app_did': self.app_did,
            }, 'params': {
                'author': 'John'}})
        self.assertIsNotNone(body)

    def test05_update(self):
        name = 'database_update'
        col_filter = {'author': '$params.author'}
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'update',
            'output': True,
            'body': {
                'collection': self.collection_name,
                'filter': col_filter,
                'update': {
                    '$set': {
                        'author': '$params.author',
                        'content': '$params.content'
                    }
                }, 'options': {
                    'bypass_document_validation': False,
                    'upsert': True
                }
            }}}, {'context': {
                'target_did': self.did,
                'target_app_did': self.app_did,
            }, 'params': {
                'author': 'John',
                'content': 'message2'}})
        self.assertIsNotNone(body)

    def test06_file_upload(self):
        name = 'upload_file'
        self.__register_script(name, {
            "executable": {
                "output": True,
                "name": name,
                "type": "fileUpload",
                "body": {
                    "path": "$params.path"
                }
            }
        })
        response = self.cli.put(f'/scripting/stream/{self.__call_script_for_transaction_id(name)}',
                                self.file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)

    def test07_file_download(self):
        name = 'download_file'
        self.__register_script(name, {
            "executable": {
                "output": True,
                "name": name,
                "type": "fileDownload",
                "body": {
                    "path": "$params.path"
                }
            }
        })
        response = self.cli.get(f'/scripting/stream/{self.__call_script_for_transaction_id(name)}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.file_content)

    def test08_delete(self):
        name = 'database_delete'
        col_filter = {'author': '$params.author'}
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'delete',
            'output': True,
            'body': {
                'collection': self.collection_name,
                'filter': col_filter
            }}}, {'context': {
                'target_did': self.did,
                'target_app_did': self.app_did,
            }, 'params': {
                'author': 'John'}})
        self.assertIsNotNone(body)

    def test09_file_properties_without_params(self):
        name = 'file_properties'
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'fileProperties',
            'output': True,
            'body': {
                'path': self.file_name
            }}}, None)
        self.assertIsNotNone(body)

    def test10_file_hash(self):
        name = 'file_hash'
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'fileHash',
            'output': True,
            'body': {
                'path': '$params.path'
            }}}, {'params': {
                'path': self.file_name}})
        self.assertIsNotNone(body)

    def test11_delete_script(self):
        response = self.cli.delete('/scripting/database_insert')
        self.assertEqual(response.status_code, 204)

    def __set_and_call_script(self, name, set_data, run_data):
        self.__register_script(name, set_data)
        return self.__call_script(name, run_data)


if __name__ == '__main__':
    unittest.main()

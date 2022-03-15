# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-scripting module.
"""
import unittest
import json

from tests.utils.http_client import HttpClient
from tests import init_test
from tests.utils_v1 import test_common


class IpfsScriptingTestCase(unittest.TestCase):
    collection_name = 'script_database'

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/vault')
        self.cli2 = HttpClient(f'/api/v2/vault', is_did2=True)
        self.file_name = 'ipfs-scripting/test.txt'
        self.file_content = 'File Content: 1234567890'
        self.name_not_exist = 'name_not_exist'
        # Owner's did and application did.
        self.did = self.cli.get_current_did()
        self.app_did = test_common.app_id

    @staticmethod
    def _subscribe():
        HttpClient(f'/api/v2').put('/subscription/vault')
        HttpClient(f'/api/v2', is_did2=True).put('/subscription/vault')

    def _delete_collection(self):
        HttpClient(f'/api/v2/vault').delete(f'/db/{self.collection_name}')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()
        HttpClient(f'/api/v2/vault').put(f'/db/collections/{cls.collection_name}')

    @classmethod
    def tearDownClass(cls):
        pass

    def __register_script(self, script_name, body):
        response = self.cli.put(f'/scripting/{script_name}', body)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.text)

    def __call_script(self, script_name, body=None, is_raw=False):
        if body is None:
            body = dict()
        body['context'] = {
            'target_did': self.did,
            'target_app_did': self.app_did,
        }
        response = self.cli2.patch(f'/scripting/{script_name}', body)
        self.assertEqual(response.status_code, 200)
        return response.text if is_raw else json.loads(response.text)

    def __set_and_call_script(self, name, set_data, run_data):
        self.__register_script(name, set_data)
        return self.__call_script(name, run_data)

    def __call_script_for_transaction_id(self, script_name, check_anonymous=False):
        response_body = self.__call_script(script_name, {
            "params": {
                "path": self.file_name
            }
        })
        self.assertEqual(type(response_body), dict)
        self.assertTrue(script_name in response_body)
        self.assertEqual(type(response_body[script_name]), dict)
        self.assertTrue('transaction_id' in response_body[script_name])
        if check_anonymous:
            self.assertTrue('anonymous_url' in response_body[script_name])
            self.assertTrue(response_body[script_name]['anonymous_url'])
        return response_body[script_name]['transaction_id']

    def test01_register_script_insert(self):
        self.__register_script('ipfs_database_insert', {"executable": {
            "output": True,
            "name": "database_insert",
            "type": "insert",
            "body": {
                "collection": self.collection_name,
                "document": {
                    "author": "$params.author",
                    "content": "$params.content",
                    "words_count": "$params.words_count"
                },
                "options": {
                    "ordered": True,
                    "bypass_document_validation": False
                }
            }
        }})

    def test02_call_script_insert(self):
        self.__call_script('ipfs_database_insert', {
            "params": {
                "author": "John",
                "content": "message",
                "words_count": 10000
            }
        })

    def test03_call_script_url_insert(self):
        response = self.cli2.get(f'/scripting/ipfs_database_insert/{self.did}@{self.app_did}'
                                 '/%7B%22author%22%3A%22John2%22%2C%22content%22%3A%22message2%22%2C%22'
                                 'words_count%22%3A%2010000%7D')
        self.assertEqual(response.status_code, 200)

    def test04_find_with_default_output_find(self):
        name = 'ipfs_database_find'
        condition_filter = {'author': '$params.author'}
        col_filter = {'author': '$params.author', "words_count": {"$gt": "$params.start", "$lt": "$params.end"}}
        body = self.__set_and_call_script(name, {'condition': {
                'name': 'verify_user_permission',
                'type': 'queryHasResults',
                'body': {
                    'collection': self.collection_name,
                    'filter': condition_filter
                }
            }, 'executable': {
                'name': name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            }}, {'params': {'author': 'John', 'start': 5000, 'end': 15000}})
        self.assertIsNotNone(body)

    def test04_find_with_multiple_conditions(self):
        name = 'ipfs_database_find_multiple_conditions'
        col_filter = {'author': '$params.author'}
        query_condition = {
            'name': 'verify_user_permission',
            'type': 'queryHasResults',
            'body': {
                'collection': self.collection_name,
                'filter': col_filter
            }
        }
        body = self.__set_and_call_script(name, {'condition': {
                'name': 'multiple_conditions',
                'type': 'and',
                'body': [query_condition, {
                        'name': 'multiple_conditions2',
                        'type': 'and',
                        'body': [query_condition, query_condition]
                    }
                ]
            }, 'executable': {
                'name': name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            }}, {'params': {'author': 'John'}})
        self.assertIsNotNone(body)

    def test04_find_with_anonymous(self):
        name = 'ipfs_database_find2'
        col_filter = {'author': '$params.author'}
        script_body = {
            'condition': {
                'name': 'verify_user_permission',
                'type': 'queryHasResults',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            },
            'executable': {
                'name': name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            },
            "allowAnonymousUser": True,
            "allowAnonymousApp": True
        }
        run_body = {'params': {
            'author': 'John'
        }}
        body = self.__set_and_call_script(name, script_body, run_body)
        self.assertIsNotNone(body)

    def test05_update(self):
        name = 'ipfs_database_update'
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
            }}}, {'params': {
                'author': 'John',
                'content': 'message2'
        }})
        self.assertIsNotNone(body)

    def test06_file_upload(self):
        name = 'ipfs_file_upload'
        self.__register_script(name, {"executable": {
                "output": True,
                "name": name,
                "type": "fileUpload",
                "body": {
                    "path": "$params.path"
                }
            }
        })
        response = self.cli2.put(f'/scripting/stream/{self.__call_script_for_transaction_id(name)}',
                                 self.file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)

    def test07_file_download(self):
        name = 'ipfs_file_download'
        self.__register_script(name, {"executable": {
                "output": True,
                "name": name,
                "type": "fileDownload",
                "body": {
                    "path": "$params.path"
                }
            }
        })
        response = self.cli2.get(f'/scripting/stream/{self.__call_script_for_transaction_id(name)}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.file_content)

    def test08_file_properties_without_params(self):
        name = 'ipfs_file_properties'
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'fileProperties',
            'output': True,
            'body': {
                'path': self.file_name
            }}}, None)
        self.assertTrue(name in body)
        self.assertEqual(body[name]['size'], len(self.file_content))

    def test09_file_hash(self):
        name = 'ipfs_file_hash'
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'fileHash',
            'output': True,
            'body': {
                'path': '$params.path'
            }}}, {'params': {
                'path': self.file_name}})
        self.assertIsNotNone(body)

    def test09_file_hash2(self):
        name = 'ipfs_file_hash'
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'fileHash',
            'output': True,
            'body': {
                'path': 'ipfs-scripting/$params.path'
            }}}, {'params': {
                'path': 'test.txt'}})
        self.assertIsNotNone(body)

    def test09_file_hash3(self):
        name = 'ipfs_file_hash'
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'fileHash',
            'output': True,
            'body': {
                'path': 'ipfs-scripting/${params.path}.txt'
            }}}, {'params': {
                'path': 'test'}})
        self.assertIsNotNone(body)

    def test10_get_anonymous_file(self):
        name = 'ipfs_get_anonymous_file'
        self.__register_script(name, {"executable": {
                "output": True,
                "name": name,
                "type": "fileDownload",
                "body": {
                    "path": "$params.path"
                }
            },
            "allowAnonymousUser": True,
            "allowAnonymousApp": True
        })
        # This will keep transaction for anyone accessing the file by 'anonymous_url'.
        trans_id = self.__call_script_for_transaction_id(name, check_anonymous=True)
        # Execute normal download to remove the transaction.
        response = self.cli2.get(f'/scripting/stream/{trans_id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.file_content)

    def test10_delete(self):
        name = 'ipfs_database_delete'
        col_filter = {'author': '$params.author'}
        body = self.__set_and_call_script(name, {'executable': {
            'name': name,
            'type': 'delete',
            'output': True,
            'body': {
                'collection': self.collection_name,
                'filter': col_filter
            }}}, {'params': {'author': 'John'}})
        self.assertIsNotNone(body)

    def test11_aggregated(self):
        name = 'ipfs_aggregated'
        self.__register_script(name, {
            "executable": {
                "output": True,
                "name": name,
                "type": "aggregated",
                "body": [
                    {
                        "output": True,
                        "name": name,
                        "type": "fileDownload",
                        "body": {
                            "path": "$params.path"
                        }
                    }
                ]},
            "allowAnonymousUser": True,
            "allowAnonymousApp": True
        })
        response = self.cli2.get(f'/scripting/stream/{self.__call_script_for_transaction_id(name)}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.file_content)

    def test11_delete_script_not_exist(self):
        response = self.cli.delete(f'/scripting/{self.name_not_exist}')
        self.assertEqual(response.status_code, 404)

    def test11_delete_script(self):
        response = self.cli.delete('/scripting/ipfs_database_insert')
        self.assertEqual(response.status_code, 204)
        response = self.cli.delete('/scripting/ipfs_database_find')
        response = self.cli.delete('/scripting/ipfs_database_find2')
        response = self.cli.delete('/scripting/ipfs_database_update')
        response = self.cli.delete('/scripting/ipfs_database_delete')
        response = self.cli.delete('/scripting/ipfs_aggregated')
        response = self.cli.delete('/scripting/ipfs_file_upload')
        response = self.cli.delete('/scripting/ipfs_file_download')
        response = self.cli.delete('/scripting/ipfs_file_properties')
        response = self.cli.delete('/scripting/ipfs_file_hash')
        response = self.cli.delete('/scripting/ipfs_get_anonymous_file')
        response = self.cli.delete(f'/files/{self.file_name}')
        self._delete_collection()


if __name__ == '__main__':
    unittest.main()

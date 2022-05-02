# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-scripting module.
"""
import unittest
import json
import urllib.parse
import typing as t
import pymongo

from tests.utils.http_client import HttpClient
from tests import init_test
from tests.utils_v1.hive_auth_test_v1 import AppDID


class IpfsScriptingTestCase(unittest.TestCase):
    collection_name = 'script_database'
    file_name = 'ipfs-scripting/test.txt'
    file_content = 'File Content: 1234567890'
    name_not_exist = 'name_not_exist'

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/vault')
        self.cli2 = HttpClient(f'/api/v2/vault', is_did2=True)
        # Owner's did and application did.
        self.did = self.cli.get_current_did()
        self.app_did = AppDID.app_did

    @classmethod
    def setUpClass(cls):
        # subscribe for user_did
        HttpClient(f'/api/v2').put('/subscription/vault')
        # unsubscribe for caller_did whose vault is not necessary.
        HttpClient(f'/api/v2', is_did2=True).delete('/subscription/vault')
        # the collection for database script testing.
        HttpClient(f'/api/v2/vault').put(f'/db/collections/{cls.collection_name}')

    @classmethod
    def tearDownClass(cls):
        # clean the testing collection.
        HttpClient(f'/api/v2/vault').delete(f'/db/{cls.collection_name}')
        # clean the testing file.
        response = HttpClient(f'/api/v2/vault').delete(f'/files/{cls.file_name}')

    def __register_script(self, script_name, body):
        response = self.cli.put(f'/scripting/{script_name}', body)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.text)

    def __call_script(self, script_name, body=None, executable_name=None):
        executable_name = executable_name if executable_name else script_name
        body = body if body else dict()
        body['context'] = {
            'target_did': self.did,
            'target_app_did': self.app_did,
        }
        return self.__check_call_response(self.cli2.patch(f'/scripting/{script_name}', body), executable_name)

    def __check_call_response(self, response, executable_name):
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.text)
        self.assertTrue(isinstance(body, dict))
        names = executable_name if type(executable_name) in [list, tuple] else [executable_name, ]
        for name in names:
            self.assertTrue(name in body)
            self.assertTrue(isinstance(body[name], dict))
        return body

    def __register_and_call_script(self, script_name, reg_body, call_body, executable_name=None):
        self.__register_script(script_name, reg_body)
        return self.__call_script(script_name, call_body, executable_name=executable_name)

    def call_and_stream(self, script_name, path: t.Optional[str],
                        executable_name=None, is_download=True, check_anonymous=False, file_content=None):
        executable_name = executable_name if executable_name else script_name
        body = self.__call_script(script_name, {"params": {"path": path}}, executable_name=executable_name)
        self.assertTrue('transaction_id' in body[executable_name])
        self.assertTrue(body[executable_name]['transaction_id'])
        if check_anonymous:
            self.assertTrue('anonymous_url' in body[executable_name])
            self.assertTrue(body[executable_name]['anonymous_url'])
        if not is_download:
            response = self.cli2.put(f'/scripting/stream/{body[executable_name]["transaction_id"]}',
                                     self.file_content.encode(), is_json=False)
        else:
            response = self.cli2.get(f'/scripting/stream/{body[executable_name]["transaction_id"]}')
        self.assertEqual(response.status_code, 200)
        if is_download:
            self.assertEqual(response.text, file_content if file_content else self.file_content)
        else:
            # nothing returned
            pass

    def __register_call_and_stream(self, script_name, reg_body, path: str,
                                   executable_name=None, is_download=True, check_anonymous=False, file_content=None):
        self.__register_script(script_name, reg_body)
        self.call_and_stream(script_name, path, executable_name=executable_name,
                             is_download=is_download, check_anonymous=check_anonymous, file_content=file_content)

    def delete_script(self, script_name: str, expect_status=204):
        response = self.cli.delete(f'/scripting/{script_name}')
        self.assertEqual(response.status_code, expect_status)

    def test01_insert(self):
        script_name, executable_name = 'ipfs_database_insert', 'database_insert'
        # normal calling.
        self.__register_and_call_script(script_name, {"executable": {
            "output": True,
            "name": executable_name,
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
        }}, {
            "params": {
                "author": "John",
                "content": "message",
                "words_count": 10000
            }
        }, executable_name=executable_name)
        # calling by url.
        url_params = f'/{self.did}@{self.app_did}/' + urllib.parse.quote_plus('{"author":"John","content":"message2","words_count":5000}')
        body = self.__check_call_response(self.cli2.get(f'/scripting/{script_name}{url_params}'), executable_name)
        self.assertTrue(body[executable_name].get('inserted_id'))
        # remove script
        self.delete_script(script_name)

    def test02_find_with_default_output(self):
        script_name, executable_name, condition_filter = 'ipfs_database_find', 'database_find', {'author': '$params.author'}
        col_filter = {'author': '$params.author', "words_count": {"$gt": "$params.start", "$lt": "$params.end"}}
        body = self.__register_and_call_script(script_name, {'condition': {
                'name': 'verify_user_permission',
                'type': 'queryHasResults',
                'body': {
                    'collection': self.collection_name,
                    'filter': condition_filter
                }
            }, 'executable': {
                'name': executable_name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter,
                    'options': {
                        'sort': [['author', pymongo.ASCENDING]]  # sort with mongodb style.
                    }
                }
            }}, {'params': {'author': 'John', 'start': 0, 'end': 15000}}, executable_name=executable_name)

        self.assertTrue('items' in body.get(executable_name))
        ids = list(map(lambda i: i['author'], body.get(executable_name)['items']))
        self.assertTrue(all(ids[i] <= ids[i + 1] for i in range(len(ids) - 1)))

        self.delete_script(script_name)

    def test02_find_with_multiple_conditions(self):
        script_name, executable_name, col_filter = 'ipfs_database_find', 'database_find', {'author': '$params.author'}
        query_condition = {
            'name': 'verify_user_permission',
            'type': 'queryHasResults',
            'body': {
                'collection': self.collection_name,
                'filter': col_filter
            }
        }
        body = self.__register_and_call_script(script_name, {'condition': {
                'name': 'multiple_conditions',
                'type': 'and',
                'body': [query_condition, {
                        'name': 'multiple_conditions2',
                        'type': 'and',
                        'body': [query_condition, query_condition]
                    }
                ]
            }, 'executable': {
                'name': executable_name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter
                }
            }}, {'params': {'author': 'John'}}, executable_name=executable_name)
        self.delete_script(script_name)

    def test02_find_with_anonymous(self):
        script_name, executable_name, col_filter = 'ipfs_database_find', 'database_find', {'author': '$params.author'}
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
                'name': executable_name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': col_filter,
                    'options': {
                        'sort': {'author': pymongo.DESCENDING}  # sort with hive style.
                    }
                }
            },
            "allowAnonymousUser": True,
            "allowAnonymousApp": True
        }
        run_body = {'params': {
            'author': 'John'
        }}
        body = self.__register_and_call_script(script_name, script_body, run_body, executable_name=executable_name)

        self.assertTrue('items' in body.get(executable_name))
        ids = list(map(lambda i: i['author'], body.get(executable_name)['items']))
        self.assertTrue(all(ids[i] >= ids[i + 1] for i in range(len(ids) - 1)))

        self.delete_script(script_name)

    def test03_aggregated_find(self):
        script_name, col_filter = 'ipfs_aggregated', {'author': '$params.author'}
        run_body = {'params': {
            'author': 'John'
        }}
        body = self.__register_and_call_script(script_name, {
            "executable": {
                "output": True,
                "name": script_name,
                "type": "aggregated",
                "body": [
                    {
                        'name': "ipfs_find_1",
                        'type': 'find',
                        'body': {
                            'collection': self.collection_name,
                            'filter': col_filter,
                            'options': {
                                'sort': {'author': pymongo.DESCENDING}  # sort with hive style.
                            }
                        }
                    }, {
                        'name': "ipfs_find_2",
                        'type': 'find',
                        'body': {
                            'collection': self.collection_name,
                            'filter': col_filter,
                            'options': {
                                'sort': {'author': pymongo.ASCENDING}  # sort with hive style.
                            }
                        }
                    },
                ]},
            "allowAnonymousUser": False,
            "allowAnonymousApp": False
        }, run_body, executable_name=['ipfs_find_1', 'ipfs_find_2'])

        self.delete_script(script_name)

    def test04_update(self):
        script_name, executable_name, col_filter = 'ipfs_database_update', 'database_update', {'author': '$params.author'}
        body = self.__register_and_call_script(script_name, {'executable': {
            'name': executable_name,
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
        }}, executable_name=executable_name)
        self.assertTrue('matched_count' in body.get(executable_name))
        self.assertTrue('modified_count' in body.get(executable_name))
        self.assertTrue('upserted_id' in body.get(executable_name))
        self.delete_script(script_name)

    def test05_delete(self):
        script_name, executable_name = 'ipfs_database_delete', 'database_delete'
        body = self.__register_and_call_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'delete',
            'output': True,
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'}
            }}}, {'params': {'author': 'John'}}, executable_name=executable_name)
        self.assertTrue('deleted_count' in body.get(executable_name))
        self.delete_script(script_name)

    def test06_file_upload(self):
        script_name, executable_name = 'ipfs_file_upload', 'file_upload'
        self.__register_call_and_stream(script_name, {"executable": {
                "output": True,
                "name": executable_name,
                "type": "fileUpload",
                "body": {
                    "path": "$params.path"
                }
            }
        }, self.file_name, executable_name=executable_name, is_download=False)
        self.delete_script(script_name)

    def test07_file_download(self):
        script_name, executable_name = 'ipfs_file_download', 'file_download'
        self.__register_call_and_stream(script_name, {"executable": {
                "output": True,
                "name": executable_name,
                "type": "fileDownload",
                "body": {
                    "path": "$params.path"
                }
            }
        }, self.file_name, executable_name=executable_name)
        self.delete_script(script_name)

    def test07_file_download_anonymous_file(self):
        script_name, executable_name = 'ipfs_file_download', 'file_download'
        self.__register_call_and_stream(script_name, {"executable": {
                "output": True,
                "name": executable_name,
                "type": "fileDownload",
                "body": {
                    "path": "$params.path"
                }
            },
            "allowAnonymousUser": True,
            "allowAnonymousApp": True
        }, self.file_name, executable_name=executable_name, check_anonymous=True)
        self.delete_script(script_name)

    def test08_file_properties_without_params(self):
        script_name, executable_name = 'ipfs_file_properties', 'file_properties'
        body = self.__register_and_call_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'fileProperties',
            'output': True,
            'body': {
                'path': self.file_name
            }}}, None, executable_name=executable_name)
        self.assertEqual(body[executable_name]['size'], len(self.file_content))
        self.assertEqual(body[executable_name]['name'], self.file_name)
        self.assertTrue('type' in body[executable_name])
        self.assertTrue('last_modify' in body[executable_name])
        self.delete_script(script_name)

    def test09_file_hash(self):
        script_name, executable_name = 'ipfs_file_hash', 'file_hash'
        body = self.__register_and_call_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'fileHash',
            'output': True,
            'body': {
                'path': '$params.path'
            }}}, {'params': {'path': self.file_name}}, executable_name=executable_name)
        self.assertTrue(body[executable_name].get('SHA256'))
        self.delete_script(script_name)

    def test09_file_hash_with_part_params(self):
        script_name, executable_name = 'ipfs_file_hash', 'file_hash'
        body = self.__register_and_call_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'fileHash',
            'output': True,
            'body': {
                'path': 'ipfs-scripting/$params.path'
            }}}, {'params': {'path': 'test.txt'}}, executable_name=executable_name)
        self.assertTrue(body[executable_name].get('SHA256'))
        self.delete_script(script_name)

    def test09_file_hash_with_part_params_2(self):
        script_name, executable_name = 'ipfs_file_hash', 'file_hash'
        body = self.__register_and_call_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'fileHash',
            'output': True,
            'body': {
                'path': 'ipfs-scripting/${params.path}.txt'
            }}}, {'params': {'path': 'test'}}, executable_name=executable_name)
        self.assertTrue(body[executable_name].get('SHA256'))
        self.delete_script(script_name)

    def test10_aggregated_download(self):
        script_name, executable_name = 'ipfs_aggregated', 'aggregated_download'
        self.__register_call_and_stream(script_name, {"executable": {
            "output": True,
            "name": executable_name,
            "type": "fileDownload",
            "body": {"path": "$params.path"}}
        }, self.file_name, executable_name=executable_name)
        self.delete_script(script_name)

    def test11_delete_script_not_exist(self):
        self.delete_script(self.name_not_exist, expect_status=404)


if __name__ == '__main__':
    unittest.main()

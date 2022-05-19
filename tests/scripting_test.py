# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-scripting module.
"""
import pymongo
import unittest
import typing as t
import urllib.parse

from tests import init_test
from tests.utils.dict_asserter import DictAsserter
from tests.utils.http_client import HttpClient
from tests.utils_v1.hive_auth_test_v1 import AppDID


class IpfsScriptingTestCase(unittest.TestCase):
    """ All test case are registering by owner, calling by caller (different user DID)

    Two types of test cases: functional testing, feature testing.

    functional testing
        Just make sure the relating function work, such as insert document.

    feature testing
        Show the features supported by scription service, such as anonymously calling, $params on options, etc

    """
    collection_name = 'script_database'
    file_name = 'ipfs-scripting/test.txt'
    file_content = 'File Content: 1234567890'
    file_sha256 = '161d165c6b49616cc82846814ccb2bbaa0928b8570bac7f6ba642c65d6006cfe'
    name_not_exist = 'name_not_exist'

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()

        # owner client.
        self.cli = HttpClient(f'/api/v2/vault')

        # caller client.
        self.cli2 = HttpClient(f'/api/v2/vault', is_did2=True)

        # Owner's did and application did.
        self.target_did = self.cli.get_current_did()
        self.target_app_did = AppDID.app_did

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
        """ clean """
        # clean the testing collection.
        HttpClient(f'/api/v2/vault').delete(f'/db/{cls.collection_name}')
        # clean the testing file.
        response = HttpClient(f'/api/v2/vault').delete(f'/files/{cls.file_name}')

    def __register_script(self, script_name, body):
        """
        :return: the response body (dict) of registering.
        """
        response = self.cli.put(f'/scripting/{script_name}', body)
        self.assertEqual(response.status_code, 200)
        # check update existing one or insert a new one
        body = DictAsserter(response.json())
        self.assertTrue(body.get_int('modified_count') == 1 or body.get_str('upserted_id'))
        return body.data

    def __call_script(self, script_name, body=None, except_error=200, need_token=True):
        """ Call script successfully

        :return: the response body (dict) of calling.
        """
        body = body if body else {}
        body['context'] = {
            'target_did': self.target_did,
            'target_app_did': self.target_app_did,
        }
        response = self.cli2.patch(f'/scripting/{script_name}', body, need_token=need_token)
        self.assertEqual(response.status_code, except_error)
        return DictAsserter(response.json()).data if except_error == 200 else None

    def call_and_execute_transaction(self, script_name, executable_name,
                                     path: t.Optional[str] = None, is_download=True, download_content=None):
        """ Call uploading or downloading script and run relating transaction.

        Also, for files service testing.

        :path: used for 'params', default is 'self.file_name'
        :is_download: True, download file, else upload file.
        :download_content: for files service.
        """
        # call the script for uploading or downloading
        body = self.__call_script(script_name, {"params": {"path": path if path else self.file_name}})
        self.assertTrue(DictAsserter(body).check_dict(executable_name).get_str('transaction_id'))

        # call relating transaction
        if is_download:
            response = self.cli2.get(f'/scripting/stream/{body[executable_name]["transaction_id"]}')
        else:
            response = self.cli2.put(f'/scripting/stream/{body[executable_name]["transaction_id"]}',
                                     self.file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)

        # check the result
        if is_download:
            self.assertEqual(response.text, download_content if download_content else self.file_content)
        else:
            # nothing returned
            pass

    def delete_script(self, script_name: str, expect_status=204):
        """ delete a script

        Also, for files service testing.

        :param script_name: script name
        :param expect_status: for error checking, such as 404
        """
        response = self.cli.delete(f'/scripting/{script_name}')
        self.assertEqual(response.status_code, expect_status)

    def test01_insert(self):
        """ test insert and insert """
        script_name, executable_name = 'ipfs_database_insert', 'database_insert'
        self.__register_script(script_name, {"executable": {
            "name": executable_name,
            "type": "insert",
            "body": {
                "collection": self.collection_name,
                "document": {
                    "author": "$params.author",  # key of 'find'
                    "content": "$params.content",
                    "words_count": "$params.words_count"
                },
                "options": {
                    "bypass_document_validation": False
                }
            }
        }})

        # insert multiple documents for further testing
        def insert_document(content: str, words_count: int):
            body = self.__call_script(script_name, body={
                "params": {
                    "author": "John",
                    "content": content,
                    "words_count": words_count
                }
            })
            self.assertTrue(DictAsserter(body).check_dict(executable_name).get_str('inserted_id'))

        insert_document('message1', 10000)
        insert_document('message3', 30000)
        insert_document('message5', 50000)
        insert_document('message7', 70000)
        insert_document('message9', 90000)
        insert_document('message2', 20000)
        insert_document('message4', 40000)
        insert_document('message6', 60000)
        insert_document('message8', 80000)

        # remove script
        self.delete_script(script_name)

    def test02_find(self):
        script_name, executable_name = 'ipfs_database_find', 'database_find'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'}
            }
        }})

        body = self.__call_script(script_name, {"params": {"author": "John"}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('total'), 9)
        items = executable.get_list('items')
        self.assertEqual(len(items), 9)
        self.assertTrue(all([a['author'] == 'John' for a in items]))
        self.assertEqual(len(list(filter(lambda a: a['content'] == 'message1', items))), 1)
        self.assertEqual(len(list(filter(lambda a: a['content'] == 'message2', items))), 1)
        self.assertEqual(len(list(filter(lambda a: a['content'] == 'message3', items))), 1)
        self.assertEqual(len(list(filter(lambda a: a['content'] == 'message4', items))), 1)
        self.assertEqual(len(list(filter(lambda a: a['content'] == 'message5', items))), 1)
        self.assertEqual(len(list(filter(lambda a: a['content'] == 'message6', items))), 1)
        self.assertEqual(len(list(filter(lambda a: a['content'] == 'message7', items))), 1)
        self.assertEqual(len(list(filter(lambda a: a['content'] == 'message8', items))), 1)
        self.assertEqual(len(list(filter(lambda a: a['content'] == 'message9', items))), 1)

        self.delete_script(script_name)

    def test03_find_with_only_url(self):
        script_name, executable_name = 'ipfs_database_find_with_only_url', 'database_find'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author', 'content': '$params.content'}
            }
        }})

        # calling by url.
        url_params = f'/{self.target_did}@{self.target_app_did}/' + urllib.parse.quote_plus('{"author":"John","content":"message1"}')
        response = self.cli2.get(f'/scripting/{script_name}{url_params}')
        self.assertEqual(response.status_code, 200)
        executable = DictAsserter(response.json()).check_dict(executable_name)
        self.assertEqual(executable.get_int('total'), 1)
        items = executable.get_list('items')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['author'], 'John')
        self.assertEqual(items[0]['content'], 'message1')
        self.assertEqual(items[0]['words_count'], 10000)

        self.delete_script(script_name)

    def test03_find_with_gt_lt(self):
        script_name, executable_name = 'ipfs_database_find_with_gt_lt', 'database_find'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author', "words_count": {"$gt": "$params.start", "$lt": "$params.end"}}
            }
        }})

        body = self.__call_script(script_name, {"params": {"author": "John", "start": 5000, "end": 15000}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('total'), 1)
        items = executable.get_list('items')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['author'], 'John')
        self.assertEqual(items[0]['content'], 'message1')
        self.assertEqual(items[0]['words_count'], 10000)

        self.delete_script(script_name)

    def test03_find_with_condition(self):
        script_name, executable_name = 'ipfs_database_find_with_condition', 'database_find'

        self.__register_script(script_name, {'condition': {
                'name': 'verify_user_permission',
                'type': 'queryHasResults',
                'body': {
                    'collection': self.collection_name,
                    'filter': {'author': '$params.condition_author'}
                }
            }, 'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {
                'collection': self.collection_name,
                'filter': {'content': '$params.content'}
            }
        }})

        # not match checking
        self.__call_script(script_name, {"params": {"condition_author": "Andersen", "content": "message1"}}, except_error=400)

        # match checking
        body = self.__call_script(script_name, {"params": {"condition_author": "John", "content": "message1"}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('total'), 1)
        items = executable.get_list('items')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['author'], 'John')
        self.assertEqual(items[0]['content'], 'message1')
        self.assertEqual(items[0]['words_count'], 10000)

        self.delete_script(script_name)

    def test03_find_with_multi_conditions(self):
        script_name, executable_name = 'ipfs_database_find_with_multi_conditions', 'database_find'
        condition = {
            'name': 'verify_user_permission',
            'type': 'queryHasResults',
            'body': {'collection': self.collection_name, 'filter': {'author': '$params.condition_author'}}
        }

        self.__register_script(script_name, {'condition': {
                'name': 'verify_user_permission',
                'type': 'or',
                'body': [condition, condition, {
                    'name': 'verify_user_permission',
                    'type': 'and',
                    'body': [condition, condition]
                }, {
                    'name': 'verify_user_permission',
                    'type': 'and',
                    'body': [condition, condition]
                }]
            }, 'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {'collection': self.collection_name, 'filter': {'content': '$params.content'}}
        }})

        # match checking
        body = self.__call_script(script_name, {"params": {"condition_author": "John", "content": "message1"}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('total'), 1)
        items = executable.get_list('items')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['author'], 'John')
        self.assertEqual(items[0]['content'], 'message1')
        self.assertEqual(items[0]['words_count'], 10000)

        self.delete_script(script_name)

    def test03_find_with_sort(self):
        script_name, executable_name = 'ipfs_database_find_with_sort', 'database_find'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'},
                'options': {'sort': '$params.sort'}
            }
        }})

        # sort with pymongo.ASCENDING on mongo style.
        body = self.__call_script(script_name, {"params": {"author": "John", 'sort': [['words_count', pymongo.ASCENDING]]}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('total'), 9)
        # check the order is pymongo.ASCENDING
        counts = list(map(lambda i: i['words_count'], executable.get_list('items')))
        self.assertTrue(all(counts[i] < counts[i + 1] for i in range(len(counts) - 1)))

        # sort with pymongo.ASCENDING on hive style.
        body = self.__call_script(script_name, {"params": {"author": "John", 'sort': {'words_count': pymongo.DESCENDING}}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('total'), 9)
        # check the order is pymongo.DESCENDING
        counts = list(map(lambda i: i['words_count'], executable.get_list('items')))
        self.assertTrue(all(counts[i] > counts[i + 1] for i in range(len(counts) - 1)))

        self.delete_script(script_name)

    def test03_find_with_anonymous(self):
        script_name, executable_name = 'ipfs_database_find_with_anonymous', 'database_find'

        self.__register_script(script_name, {'condition': {
            'name': 'verify_user_permission',
            'type': 'queryHasResults',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.condition_author'}
            }
        }, 'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {
                'collection': self.collection_name,
                'filter': {'content': '$params.content'}
            }
        }, 'allowAnonymousUser': True, 'allowAnonymousApp': True})

        # not match checking without token
        self.__call_script(script_name, {"params": {"condition_author": "Andersen", "content": "message1"}}, need_token=False, except_error=400)

        # not match checking with token
        self.__call_script(script_name, {"params": {"condition_author": "Andersen", "content": "message1"}}, need_token=True, except_error=400)

        def validate_body(b):
            executable = DictAsserter(b).check_dict(executable_name)
            self.assertEqual(executable.get_int('total'), 1)
            items = executable.get_list('items')
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]['author'], 'John')
            self.assertEqual(items[0]['content'], 'message1')
            self.assertEqual(items[0]['words_count'], 10000)

        # match checking without token
        body = self.__call_script(script_name, {"params": {"condition_author": "John", "content": "message1"}}, need_token=False)
        validate_body(body)

        # match checking with token
        body = self.__call_script(script_name, {"params": {"condition_author": "John", "content": "message1"}}, need_token=True)
        validate_body(body)

        self.delete_script(script_name)

    def test03_find_with_aggregated(self):
        script_name, executable_name = 'ipfs_database_find_with_aggregated', 'database_find'
        executable_count = 5

        def get_executable(index: str):
            return {
                'name': executable_name + index,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': {'content': '$params.content' + index}
                }
            }

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'aggregated',
            'body': [get_executable(str(i)) for i in range(1, executable_count + 1)]
        }})

        params = {'content' + str(i): 'message' + str(i) for i in range(1, executable_count + 1)}
        body = self.__call_script(script_name, {"params": params})
        executables = DictAsserter(body)

        def assert_executable(index: str):
            executable = executables.check_dict(executable_name + index)
            self.assertEqual(executable.get_int('total'), 1)
            items = executable.get_list('items')
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]['author'], 'John')
            self.assertEqual(items[0]['content'], f'message{index}')
            self.assertEqual(items[0]['words_count'], int(f'{index}0000'))

        [assert_executable(str(i)) for i in range(1, executable_count + 1)]

        self.delete_script(script_name)

    def test04_update(self):
        script_name, executable_name = 'ipfs_database_update', 'database_update'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'update',
            'body': {
                'collection': self.collection_name,
                'filter': {'content': '$params.content'},
                'update': {
                    '$set': {
                        'words_count': '$params.words_count'
                    }
                }
            }
        }})

        body = self.__call_script(script_name, {"params": {"content": "message9", "words_count": 100000}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('modified_count'), 1)

        body = self.__call_script(script_name, {"params": {"content": "message9", "words_count": 90000}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('modified_count'), 1)

        self.delete_script(script_name)

    def test05_delete(self):
        script_name, executable_name = 'ipfs_database_delete', 'database_delete'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'delete',
            'body': {
                'collection': self.collection_name,
                'filter': {'content': '$params.content'}
            }}
        })

        body = self.__call_script(script_name, {"params": {"content": "message9"}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('deleted_count'), 1)

        self.delete_script(script_name)

    def test06_file_upload(self):
        script_name, executable_name = 'ipfs_file_upload', 'file_upload'

        self.__register_script(script_name, {"executable": {
            "name": executable_name,
            "type": "fileUpload",
            "body": {
                "path": "$params.path"
            }}
        })

        self.call_and_execute_transaction(script_name, executable_name, is_download=False)

        self.delete_script(script_name)

    def test07_file_download(self):
        script_name, executable_name = 'ipfs_file_download', 'file_download'

        self.__register_script(script_name, {"executable": {
            "name": executable_name,
            "type": "fileDownload",
            "body": {
                "path": "$params.path"
            }}
        })

        self.call_and_execute_transaction(script_name, executable_name)

        self.delete_script(script_name)

    def test08_file_properties(self):
        script_name, executable_name = 'ipfs_file_properties', 'file_properties'

        self.__register_script(script_name, {"executable": {
            "name": executable_name,
            "type": "fileProperties",
            "body": {
                "path": "$params.path"
            }}
        })

        body = self.__call_script(script_name, {'params': {'path': self.file_name}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_int('size'), len(self.file_content))
        self.assertEqual(executable.get_str('name'), self.file_name)
        self.assertIn('type', executable.data)
        self.assertIn('last_modify', executable.data)

        self.delete_script(script_name)

    def test09_file_hash(self):
        script_name, executable_name = 'ipfs_file_hash', 'file_hash'

        self.__register_script(script_name, {"executable": {
            "name": executable_name,
            "type": "fileHash",
            "body": {
                "path": "$params.path"
            }}
        })

        body = self.__call_script(script_name, {'params': {'path': self.file_name}})
        executable = DictAsserter(body).check_dict(executable_name)
        self.assertEqual(executable.get_str('SHA256'), self.file_sha256)

        self.delete_script(script_name)

    def test09_file_hash_with_part_params(self):
        script_name, executable_name = 'ipfs_file_hash_with_part_params', 'file_hash'

        def register_hash(path_pattern: str):
            self.__register_script(script_name, {"executable": {
                "name": executable_name,
                "type": "fileHash",
                "body": {
                    "path": path_pattern
                }}
            })

        def validate_call(path_value: str):
            body = self.__call_script(script_name, {'params': {'path': path_value}})
            executable = DictAsserter(body).check_dict(executable_name)
            self.assertEqual(executable.get_str('SHA256'), self.file_sha256)

        # 'ipfs-scripting/test.txt'
        register_hash('ipfs-scripting/$params.path')
        validate_call('test.txt')

        register_hash('$params.path/test.txt')
        validate_call('ipfs-scripting')

        register_hash('ipfs-scripting/${params.path}.txt')
        validate_call('test')

        self.delete_script(script_name)

    def test11_delete_script_not_exist(self):
        self.delete_script(self.name_not_exist, expect_status=404)


if __name__ == '__main__':
    unittest.main()

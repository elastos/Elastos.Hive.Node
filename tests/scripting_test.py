# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-scripting module.
"""
import pymongo
import unittest
import typing as t
import urllib.parse

from tests import init_test, is_valid_object_id
from tests.utils.http_client import HttpClient, AppDID
from tests.utils.resp_asserter import RA
from tests.files_test import VaultFilesUsageChecker, IpfsFilesTestCase


class IpfsScriptingTestCase(unittest.TestCase):
    """ All test case are registering by owner, calling by caller (different user DID)

    Two types of test cases: functional testing, feature testing.

    functional testing
        Just make sure the relating function work, such as insert document.

    feature testing
        Show the features supported by scription service, such as anonymously calling, $params on options, etc

    """
    collection_name = 'script_database'

    # for files scripts
    file_name = 'ipfs_scripting/test.node.txt'
    file_content = 'File Content: 1234567890'
    file_content_sha256 = '161d165c6b49616cc82846814ccb2bbaa0928b8570bac7f6ba642c65d6006cfe'

    # not existing script name
    name_not_exist = 'name_not_exist'

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.files_test = IpfsFilesTestCase()

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
        RA(response).assert_status(200)
        body = RA(response).body()
        # check update existing one or insert a new one
        self.assertTrue(body.get('modified_count', int) == 1 or body.get('upserted_id', str))
        return body

    def __call_script(self, script_name, body=None, except_error=200, need_token=True, need_context=True):
        """ Call script successfully

        :return: the response body (dict) of calling.
        """
        body = body if body else {}
        if need_context:
            body['context'] = {
                'target_did': self.target_did,
                'target_app_did': self.target_app_did,
            }
        response = self.cli2.patch(f'/scripting/{script_name}', body, need_token=need_token)
        RA(response).assert_status(except_error)
        return RA(response).body() if except_error == 200 else None

    def call_and_execute_transaction(self, script_name, executable_name,
                                     path: t.Optional[str] = None, is_download=True, download_content=None, need_token=True):
        """ Call uploading or downloading script and run relating transaction.

        Also, for files service testing.

        :path: used for 'params', default is 'self.file_name'
        :is_download: True, download file, else upload file.
        :download_content: for files service.
        """
        # call the script for uploading or downloading
        body = self.__call_script(script_name, {"params": {"path": path if path else self.file_name}}, need_token=need_token)
        body.get(executable_name).assert_true('transaction_id', str)

        # call relating transaction
        if is_download:
            response = self.cli2.get(f'/scripting/stream/{body[executable_name]["transaction_id"]}', need_token=need_token)
        else:
            response = self.cli2.put(f'/scripting/stream/{body[executable_name]["transaction_id"]}',
                                     self.file_content.encode(), is_json=False, need_token=need_token)
        RA(response).assert_status(200)

        # check the result
        if is_download:
            RA(response).text_equal(download_content if download_content else self.file_content)
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
        RA(response).assert_status(expect_status)

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
            body.get(executable_name).assert_true('inserted_id', str)

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

    def test02_count(self):
        script_name, executable_name = 'ipfs_database_count', 'database_count'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'count',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'}
            }
        }})

        body = self.__call_script(script_name, {"params": {"author": "John"}})
        body.get(executable_name).assert_equal('count', 9)

        self.delete_script(script_name)

    def test02_count_with_anonymous(self):
        script_name, executable_name = 'ipfs_database_count', 'database_count'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'count',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'}
            }
        }, 'allowAnonymousUser': True, 'allowAnonymousApp': True})

        body = self.__call_script(script_name, {"params": {"author": "John"}}, need_token=False)
        body.get(executable_name).assert_equal('count', 9)

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
        body.get(executable_name).assert_equal('total', 9)
        items = body.get(executable_name).get('items', list)

        # assert items.
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

    def test03_find_with_output(self):
        script_name, executable_name = 'ipfs_database_find_with_output', 'database_find'

        def register_with_is_out(output):
            self.__register_script(script_name, {'executable': {
                'name': executable_name,
                'type': 'find',
                'output': output,
                'body': {
                    'collection': self.collection_name,
                    'filter': {'author': '$params.author'}
                }
            }})

        # check with 'is_out' = True
        register_with_is_out(True)
        body = self.__call_script(script_name, {"params": {"author": "John"}})
        body.get(executable_name).assert_equal('total', 9)
        items = body.get(executable_name).get('items', list)

        # assert items
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

        # check with 'is_out' = False
        register_with_is_out(False)
        body = self.__call_script(script_name, {"params": {"author": "John"}})
        self.assertFalse(body)

        self.delete_script(script_name)

    def test03_find_with_limit_skip(self):
        script_name, executable_name = 'ipfs_database_find_with_limit_skip', 'database_find'

        def register(limit, skip):
            self.__register_script(script_name, {'executable': {
                'name': executable_name,
                'type': 'find',
                'body': {
                    'collection': self.collection_name,
                    'filter': {'author': '$params.author'},
                    'options': {
                        'limit': limit,
                        'skip': skip,
                        'sort': [['words_count', pymongo.ASCENDING]]
                    }
                }
            }})

        def check_result(items_count, first_content, extra_params=None):
            request_body = {"params": {"author": "John"}}
            if extra_params:
                request_body['params'].update(extra_params)
            body = self.__call_script(script_name, request_body)
            body.get(executable_name).assert_equal('total', 9)
            items = body.get(executable_name).get('items', list)

            # assert items
            self.assertEqual(len(items), items_count)
            self.assertEqual(items[0]['content'], first_content)

        # total 9
        register(3, 0), check_result(3, 'message1')
        register(5, 3), check_result(5, 'message4')
        register(7, 5), check_result(4, 'message6')

        # options also support $params
        register('$params.limit', '$params.skip'), check_result(2, 'message3', extra_params={'limit': 2, 'skip': 2})

        self.delete_script(script_name)

    def test03_find_without_context(self):
        script_name, executable_name = 'ipfs_database_find_without_context', 'database_find'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'}
            }
        }})

        self.__call_script(script_name, {"params": {"author": "John"}}, need_context=False, except_error=400)

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
        RA(response).assert_status(200)
        RA(response).body().get(executable_name).assert_equal('total', 1)
        items = RA(response).body().get(executable_name).get('items', list)

        # assert items
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
        body.get(executable_name).assert_equal('total', 1)
        items = body.get(executable_name).get('items', list)

        # assert items
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
        body.get(executable_name).assert_equal('total', 1)
        items = body.get(executable_name).get('items', list)

        # assert items
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
        body.get(executable_name).assert_equal('total', 1)
        items = body.get(executable_name).get('items', list)

        # assert items
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
        body.get(executable_name).assert_equal('total', 9)
        items = body.get(executable_name).get('items', list)
        # check the order is pymongo.ASCENDING
        counts = list(map(lambda i: i['words_count'], items))
        self.assertTrue(all(counts[i] < counts[i + 1] for i in range(len(counts) - 1)))

        # sort with pymongo.ASCENDING on hive style.
        body = self.__call_script(script_name, {"params": {"author": "John", 'sort': {'words_count': pymongo.DESCENDING}}})
        body.get(executable_name).assert_equal('total', 9)
        items = body.get(executable_name).get('items', list)
        # check the order is pymongo.DESCENDING
        counts = list(map(lambda i: i['words_count'], items))
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
            b.get(executable_name).assert_equal('total', 1)
            items = b.get(executable_name).get('items', list)
            # assert items
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
        # executables = ADictAsserter(body)

        def assert_executable(index: str):
            body.get(executable_name + index).assert_equal('total', 1)
            items = body.get(executable_name + index).get('items', list)
            # assert items
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
        body.get(executable_name).assert_equal('modified_count', 1)

        body = self.__call_script(script_name, {"params": {"content": "message9", "words_count": 90000}})
        body.get(executable_name).assert_equal('modified_count', 1)

        self.delete_script(script_name)

    def test04_update_insert_if_not_exists(self):
        script_name, executable_name = 'ipfs_database_update_insert_if_not_exists', 'database_update'

        self.__register_script(script_name, {'executable': {
            'name': executable_name,
            'type': 'update',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'},
                'update': {'$setOnInsert': {
                    'content': '$params.content',
                    'words_count': '$params.words_count'
                }},
                'options': {'upsert': True}
            }
        }})

        body = self.__call_script(script_name, {"params": {"author": "Alex", "content": "message10", "words_count": 100000}})
        self.assertTrue(is_valid_object_id(body.get(executable_name).get('upserted_id', str)))

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
        body.get(executable_name).assert_equal('deleted_count', 1)

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

        size_before, size_after = self.files_test.get_remote_file_size(self.file_name), len(IpfsScriptingTestCase.file_content)
        with VaultFilesUsageChecker(size_after - size_before) as _:
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

    def test07_file_download_with_anonymous(self):
        script_name, executable_name = 'ipfs_file_download', 'file_download'

        self.__register_script(script_name, {"executable": {
            "name": executable_name,
            "type": "fileDownload",
            "body": {
                "path": "$params.path"
            }},  'allowAnonymousUser': True, 'allowAnonymousApp': True})

        self.call_and_execute_transaction(script_name, executable_name, need_token=False)

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
        body.get(executable_name).assert_equal('size', len(self.file_content))
        body.get(executable_name).assert_equal('name', self.file_name)
        body.get(executable_name).assert_equal('type', 'file')
        body.get(executable_name).assert_true('last_modify', int)

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
        body.get(executable_name).assert_equal('SHA256', self.file_content_sha256)

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
            body.get(executable_name).assert_equal('SHA256', self.file_content_sha256)

        folder_name, file_name = self.file_name.split("/")

        register_hash(f'{folder_name}/$params.path')
        validate_call(file_name)

        register_hash(f'$params.path/{file_name}')
        validate_call(folder_name)

        split_index = 5
        register_hash('ipfs_scripting/${params.path}' + file_name[split_index:])
        validate_call(file_name[:split_index])

        self.delete_script(script_name)

    def test11_delete_script_not_exist(self):
        self.delete_script(self.name_not_exist, expect_status=404)


if __name__ == '__main__':
    unittest.main()

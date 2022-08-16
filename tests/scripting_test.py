# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-scripting module.
"""
import random
import typing

import pymongo
import unittest
import typing as t
import urllib.parse

from tests import init_test, is_valid_object_id, VaultFilesUsageChecker, VaultFreezer
from tests.utils.http_client import HttpClient, AppDID
from tests.utils.resp_asserter import RA, DictAsserter
from tests.utils.tester_http import HttpCode
from tests.subscription_test import SubscriptionTestCase
from tests.files_test import IpfsFilesTestCase


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

    subscription_test = SubscriptionTestCase()
    # subscription_test2 = SubscriptionTestCase(is_did2=True)
    files_test = IpfsFilesTestCase()

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()

        # owner client.
        self.cli = HttpClient(f'/api/v2/vault')

        # caller client
        # call http method without token if anonymous
        self.cli2 = HttpClient(f'/api/v2/vault', is_did2=True)

        # Owner's did and application did.
        self.target_did = self.cli.get_current_did()
        self.target_app_did = AppDID.app_did

    @classmethod
    def setUpClass(cls) -> None:
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

    def __register_script(self, script_name, script_body: dict, expect_status=200, anonymous=False):
        """
        :return: the response body (dict) of registering.
        """
        body = script_body.copy()
        if anonymous:
            body['allowAnonymousUser'] = anonymous
            body['allowAnonymousApp'] = anonymous

        response = self.cli.put(f'/scripting/{script_name}', body)
        RA(response).assert_status(expect_status)
        if expect_status == 200:
            body = RA(response).body()
            # check update existing one or insert a new one
            self.assertTrue(body.get('modified_count', int) == 1 or body.get('upserted_id', str))
            return body

    def __call_script(self, script_name, body=typing.Optional[dict], expect_status=200, need_context=True, anonymous=False):
        """ Call script successfully

        :param need_context call caller's script if False
        :return: the response body (dict) of calling.
        """
        body = body.copy() if body else {}
        if need_context:
            body['context'] = {
                'target_did': self.target_did,
                'target_app_did': self.target_app_did,
            }
        response = self.cli2.patch(f'/scripting/{script_name}', body, need_token=not anonymous)
        RA(response).assert_status(expect_status)
        return RA(response).body() if expect_status == 200 else None

    def __register_call_delete_script(self, script_name, script_body, call_body, call_response_checker: typing.Callable[[any, any], None],
                                      expect_status=HttpCode.OK):
        """ register and call, for vault-freeze&vault-unfreeze, anonymous&non-anonymous

        example: test06_file_upload()

            all other test cases need align with upload test case

        :param call_response_checker it will be called twice for anonymous and non-anonymous
        :return body of calling response if no error, else None
        """

        executable_type = script_body['executable']['type']

        def normal_check(anonymous):
            with VaultFreezer() as _:
                self.__register_script(script_name, script_body, expect_status=HttpCode.FORBIDDEN, anonymous=anonymous)

            self.__register_script(script_name, script_body, expect_status=expect_status, anonymous=anonymous)

            with VaultFreezer() as _:
                # FORBIDDEN is only for write operation
                if executable_type in ['insert', 'update', 'delete', 'fileUpload']:
                    self.__call_script(script_name, call_body, expect_status=HttpCode.FORBIDDEN, anonymous=anonymous)
                else:
                    self.__call_script(script_name, call_body, expect_status=HttpCode.OK, anonymous=anonymous)

            # no context: not found script if non-anonymous else can not find target_did and target_app_did
            #   all return BAD_REQUEST
            self.__call_script(script_name, call_body, expect_status=HttpCode.BAD_REQUEST, anonymous=anonymous, need_context=False)

            # do anonymous call when non-anonymous
            if not anonymous:
                self.__call_script(script_name, call_body, expect_status=HttpCode.UNAUTHORIZED, anonymous=True)

            body = self.__call_script(script_name, call_body, expect_status=expect_status, anonymous=anonymous)
            if expect_status == HttpCode.OK and call_response_checker:
                call_response_checker(body, anonymous)

            with VaultFreezer() as _:
                self.delete_script(script_name, expect_status=HttpCode.FORBIDDEN)

            self.delete_script(script_name)

        normal_check(anonymous=False)
        normal_check(anonymous=True)

    def call_and_execute_transaction(self, script_name, executable_name,
                                     path: t.Optional[str] = None, is_download=True, download_content=None, anonymous=False):
        """ Call uploading or downloading script and run relating transaction.

        Also, for files service testing.

        :path: used for 'params', default is 'self.file_name'
        :is_download: True, download file, else upload file.
        :download_content: for files service.
        """
        # call the script for uploading or downloading
        body = self.__call_script(script_name, {"params": {"path": path if path else self.file_name}}, anonymous=anonymous)
        body.get(executable_name).assert_true('transaction_id', str)

        # call relating transaction
        if is_download:
            response = self.cli2.get(f'/scripting/stream/{body[executable_name]["transaction_id"]}', need_token=not anonymous)
        else:
            response = self.cli2.put(f'/scripting/stream/{body[executable_name]["transaction_id"]}',
                                     self.file_content.encode(), is_json=False, need_token=not anonymous)
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
        script_body = {"executable": {
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
            }}}

        def get_call_body(content, words_count):
            return {
                "params": {
                    "author": "John",
                    "content": content,
                    "words_count": words_count
                }
            }

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_true('inserted_id', str)

        def execute_once(content, words_count):
            self.__register_call_delete_script(script_name, script_body, get_call_body(content, words_count), call_response_checker)

        # 18 docs
        execute_once('message1', 10000)
        execute_once('message3', 30000)
        execute_once('message5', 50000)
        execute_once('message7', 70000)
        execute_once('message9', 90000)
        execute_once('message2', 20000)
        execute_once('message4', 40000)
        execute_once('message6', 60000)
        execute_once('message8', 80000)

    def test02_count(self):
        script_name, executable_name = 'ipfs_database_count', 'database_count'
        script_body = {'executable': {
            'name': executable_name,
            'type': 'count',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'}
            }
        }}
        call_body = {"params": {"author": "John"}}

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_equal('count', 18)

        self.__register_call_delete_script(script_name, script_body, call_body, call_response_checker)

    def test02_count_with_invalid_run_params(self):
        script_name, executable_name = 'ipfs_database_count', 'database_count'
        script_body = {'executable': {
            'name': executable_name,
            'type': 'count',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'}
            }
        }}
        call_body = {"params": "invalid params data type"}

        self.__register_script(script_name, script_body, expect_status=HttpCode.OK, anonymous=False)
        self.__call_script(script_name, call_body, expect_status=HttpCode.BAD_REQUEST, anonymous=False, need_context=False)
        self.delete_script(script_name)

    def test02_find(self):
        script_name, executable_name = 'ipfs_database_find', 'database_find'
        script_body = {'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author'}
            }
        }}
        call_body = {"params": {"author": "John"}}

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_equal('total', 18)
            items = body.get(executable_name).get('items', list)

            # check asserted items.
            self.assertEqual(len(items), 18)
            self.assertTrue(all([a['author'] == 'John' for a in items]))
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message1', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message2', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message3', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message4', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message5', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message6', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message7', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message8', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message9', items))), 2)

        self.__register_call_delete_script(script_name, script_body, call_body, call_response_checker)

    def test03_find_with_output(self):
        script_name, executable_name = 'ipfs_database_find_with_output', 'database_find'

        def get_script_body(output: bool):
            return {'executable': {
                'name': executable_name,
                'type': 'find',
                'output': output,
                'body': {
                    'collection': self.collection_name,
                    'filter': {'author': '$params.author'}
                }
            }}
        call_body = {"params": {"author": "John"}}

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_equal('total', 18)
            items = body.get(executable_name).get('items', list)

            # check asserted items.
            self.assertEqual(len(items), 18)
            self.assertTrue(all([a['author'] == 'John' for a in items]))
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message1', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message2', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message3', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message4', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message5', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message6', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message7', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message8', items))), 2)
            self.assertEqual(len(list(filter(lambda a: a['content'] == 'message9', items))), 2)

        self.__register_call_delete_script(script_name, get_script_body(True), call_body, call_response_checker)

        def call_response_checker(body: DictAsserter, anonymous):
            self.assertFalse(body)

        self.__register_call_delete_script(script_name, get_script_body(False), call_body, call_response_checker)

    def test03_find_with_limit_skip(self):
        script_name, executable_name = 'ipfs_database_find_with_limit_skip', 'database_find'

        def get_script_body(limit, skip):
            return {'executable': {
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
            }}
        call_body = {"params": {"author": "John"}}

        def execute_once(limit, skip, response_items_count, response_first_content, extra_params=None):
            if extra_params:
                call_body['params'].update(extra_params)

            def call_response_checker(body: DictAsserter, anonymous):
                body.get(executable_name).assert_equal('total', 18)
                items = body.get(executable_name).get('items', list)

                # assert items
                self.assertEqual(len(items), response_items_count)
                self.assertEqual(items[0]['content'], response_first_content)

            self.__register_call_delete_script(script_name, get_script_body(limit, skip), call_body, call_response_checker)

        # total 9
        execute_once(6, 0, 6, 'message1')
        execute_once(10, 6, 10, 'message4')
        execute_once(14, 10, 8, 'message6')

        # options also support $params
        execute_once('$params.limit', '$params.skip', 4, 'message3', extra_params={'limit': 4, 'skip': 4})

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
        RA(response).body().get(executable_name).assert_equal('total', 2)
        items = RA(response).body().get(executable_name).get('items', list)

        # assert items
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['author'], 'John')
        self.assertEqual(items[0]['content'], 'message1')
        self.assertEqual(items[0]['words_count'], 10000)

        self.delete_script(script_name)

    def test03_find_with_gt_lt(self):
        script_name, executable_name = 'ipfs_database_find_with_gt_lt', 'database_find'
        script_body = {'executable': {
            'name': executable_name,
            'type': 'find',
            'body': {
                'collection': self.collection_name,
                'filter': {'author': '$params.author', "words_count": {"$gt": "$params.start", "$lt": "$params.end"}}
            }
        }}
        call_body = {"params": {"author": "John", "start": 5000, "end": 15000}}

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_equal('total', 2)
            items = body.get(executable_name).get('items', list)

            # assert items
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0]['author'], 'John')
            self.assertEqual(items[0]['content'], 'message1')
            self.assertEqual(items[0]['words_count'], 10000)

        self.__register_call_delete_script(script_name, script_body, call_body, call_response_checker)

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
        self.__call_script(script_name, {"params": {"condition_author": "Andersen", "content": "message1"}}, expect_status=400)

        # match checking
        body = self.__call_script(script_name, {"params": {"condition_author": "John", "content": "message1"}})
        body.get(executable_name).assert_equal('total', 2)
        items = body.get(executable_name).get('items', list)

        # assert items
        self.assertEqual(len(items), 2)
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
        body.get(executable_name).assert_equal('total', 2)
        items = body.get(executable_name).get('items', list)

        # assert items
        self.assertEqual(len(items), 2)
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
        body.get(executable_name).assert_equal('total', 18)
        items = body.get(executable_name).get('items', list)
        # check the order is pymongo.ASCENDING
        counts = list(map(lambda i: i['words_count'], items))
        self.assertTrue(all(counts[i] <= counts[i + 1] for i in range(len(counts) - 1)))

        # sort with pymongo.ASCENDING on hive style.
        body = self.__call_script(script_name, {"params": {"author": "John", 'sort': {'words_count': pymongo.DESCENDING}}})
        body.get(executable_name).assert_equal('total', 18)
        items = body.get(executable_name).get('items', list)
        # check the order is pymongo.DESCENDING
        counts = list(map(lambda i: i['words_count'], items))
        self.assertTrue(all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1)))

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
            body.get(executable_name + index).assert_equal('total', 2)
            items = body.get(executable_name + index).get('items', list)
            # assert items
            self.assertEqual(len(items), 2)
            self.assertEqual(items[0]['author'], 'John')
            self.assertEqual(items[0]['content'], f'message{index}')
            self.assertEqual(items[0]['words_count'], int(f'{index}0000'))

        [assert_executable(str(i)) for i in range(1, executable_count + 1)]

        self.delete_script(script_name)

    def test04_update(self):
        script_name, executable_name = 'ipfs_database_update', 'database_update'
        script_body = {'executable': {
            'name': executable_name,
            'type': 'update',
            'body': {
                'collection': self.collection_name,
                'filter': {'content': '$params.content', 'words_count': '$params.words_count_src'},
                'update': {
                    '$set': {
                        'words_count': '$params.words_count_dst'
                    }
                }
            }
        }}

        def get_call_body(words_count_src, words_count_dst):
            return {"params": {"content": "message9", "words_count_src": words_count_src, "words_count_dst": words_count_dst}}

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_equal('modified_count', 1)

        def execute_once(words_count_src, words_count_dst):
            self.__register_call_delete_script(script_name, script_body, get_call_body(words_count_src, words_count_dst), call_response_checker)

        execute_once(90000, 90001)
        execute_once(90001, 90000)

    def test04_update_insert_if_not_exists(self):
        script_name, executable_name = 'ipfs_database_update_insert_if_not_exists', 'database_update'
        script_body = {'executable': {
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
        }}
        call_body = {"params": {"author": "Alex", "content": "message10", "words_count": 100000}}

        def call_response_checker(body: DictAsserter, anonymous):
            if not anonymous:
                self.assertTrue(is_valid_object_id(body.get(executable_name).get('upserted_id', str)))
            else:
                self.assertFalse(body.get(executable_name)['upserted_id'])

        self.__register_call_delete_script(script_name, script_body, call_body, call_response_checker)

    def test05_delete(self):
        script_name, executable_name = 'ipfs_database_delete', 'database_delete'
        script_body = {'executable': {
            'name': executable_name,
            'type': 'delete',
            'body': {
                'collection': self.collection_name,
                'filter': {'content': '$params.content'}
            }}
        }
        call_body = {"params": {"content": "message9"}}

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_equal('deleted_count', 1)

        self.__register_call_delete_script(script_name, script_body, call_body, call_response_checker)

    def _upload_by_transaction(self, transaction_id, expect_status=HttpCode.OK, anonymous=False):
        response = self.cli2.put(f'/scripting/stream/{transaction_id}',
                                 self.file_content.encode(), is_json=False, need_token=not anonymous)
        RA(response).assert_status(expect_status)

    def test06_file_upload(self):
        script_name, executable_name = 'ipfs_file_upload', 'file_upload'
        script_body = {"executable": {
            "name": executable_name,
            "type": "fileUpload",
            "body": {
                "path": "$params.path"
            }}
        }
        call_body = {"params": {"path": self.file_name}}

        def call_response_checker(body: DictAsserter, anonymous):
            id_ = body.get(executable_name).get('transaction_id', str)

            with VaultFreezer() as _:
                self._upload_by_transaction(id_, anonymous=anonymous, expect_status=HttpCode.FORBIDDEN)

            size_before, size_after = self.files_test.get_remote_file_size(self.file_name), len(IpfsScriptingTestCase.file_content)
            with VaultFilesUsageChecker(size_after - size_before) as _:
                self._upload_by_transaction(id_, anonymous=anonymous)

        self.__register_call_delete_script(script_name, script_body, call_body, call_response_checker)

    def _download_by_transaction(self, transaction_id, expect_status=HttpCode.OK, anonymous=False):
        response = self.cli2.get(f'/scripting/stream/{transaction_id}',
                                 self.file_content.encode(), is_json=False, need_token=not anonymous)
        RA(response).assert_status(expect_status)
        if expect_status == HttpCode.OK:
            RA(response).text_equal(self.file_content)

    def test07_file_download(self):
        script_name, executable_name = 'ipfs_file_download', 'file_download'
        script_body = {"executable": {
            "name": executable_name,
            "type": "fileDownload",
            "body": {
                "path": "$params.path"
            }}
        }
        call_body = {"params": {"path": self.file_name}}

        def call_response_checker(body: DictAsserter, anonymous=False):
            id_ = body.get(executable_name).get('transaction_id', str)

            if random.randint(0, 1) == 0:
                with VaultFreezer() as _:
                    self._download_by_transaction(id_, anonymous=anonymous, expect_status=HttpCode.OK)
            else:
                self._download_by_transaction(id_, anonymous=anonymous)

        self.__register_call_delete_script(script_name, script_body, call_body, call_response_checker)

    def test08_file_properties(self):
        script_name, executable_name = 'ipfs_file_properties', 'file_properties'
        script_body = {"executable": {
            "name": executable_name,
            "type": "fileProperties",
            "body": {
                "path": "$params.path"
            }}
        }
        call_body = {'params': {'path': self.file_name}}

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_equal('size', len(self.file_content))
            body.get(executable_name).assert_equal('name', self.file_name)
            body.get(executable_name).assert_equal('type', 'file')
            body.get(executable_name).assert_true('last_modify', int)

        self.__register_call_delete_script(script_name, script_body, call_body, call_response_checker)

    def test09_file_hash(self):
        script_name, executable_name = 'ipfs_file_hash', 'file_hash'
        script_body = {"executable": {
            "name": executable_name,
            "type": "fileHash",
            "body": {
                "path": "$params.path"
            }}
        }
        call_body = {'params': {'path': self.file_name}}

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_equal('SHA256', self.file_content_sha256)

        self.__register_call_delete_script(script_name, script_body, call_body, call_response_checker)

    def test09_file_hash_with_part_params(self):
        script_name, executable_name = 'ipfs_file_hash_with_part_params', 'file_hash'

        def get_script_body(path_pattern: str):
            return {"executable": {
                "name": executable_name,
                "type": "fileHash",
                "body": {
                    "path": path_pattern
                }}
            }

        def get_call_body(path_value: str):
            return {'params': {'path': path_value}}

        def call_response_checker(body: DictAsserter, anonymous):
            body.get(executable_name).assert_equal('SHA256', self.file_content_sha256)

        def check_with_pattern(path_pattern, path_value):
            self.__register_call_delete_script(script_name, get_script_body(path_pattern), get_call_body(path_value), call_response_checker)

        folder_name, file_name = self.file_name.split("/")
        check_with_pattern(f'{folder_name}/$params.path', file_name)
        check_with_pattern(f'$params.path/{file_name}', folder_name)

        split_index = 5
        check_with_pattern('ipfs_scripting/${params.path}' + file_name[split_index:], file_name[:split_index])

    def test10_delete_script_not_exist(self):
        self.delete_script(self.name_not_exist, expect_status=404)


if __name__ == '__main__':
    unittest.main()

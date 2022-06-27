# -*- coding: utf-8 -*-
import os
import unittest

from bson import ObjectId
from bson.errors import InvalidId

from src.utils.did.did_init import init_did_backend
from tests.utils.resp_asserter import RA
from tests.utils.tester_http import HttpCode


class VaultFilesUsageChecker(unittest.TestCase):
    """ Only used check the file storage usage size changed in vault """

    def __init__(self, increase_size, method_name='runTest'):
        super().__init__(method_name)
        from tests.utils.http_client import HttpClient

        self.cli = HttpClient(f'/api/v2')
        self.increase_size = increase_size
        self.file_size_before = self.__get_vault_file_usage_size()

    def __get_vault_file_usage_size(self):
        response = self.cli.get('/subscription/vault?files_used=true')
        RA(response).assert_status(200)
        return RA(response).body().get('files_used', int)

    def __enter__(self):
        ...

    def __exit__(self, exc_type, exc_val, exc_tb):
        file_size_after = self.__get_vault_file_usage_size()
        self.assertEqual(self.increase_size, file_size_after - self.file_size_before)


class VaultFreezer(unittest.TestCase):
    """ Used to do some check on the freeze state of the vault """

    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        from tests.utils.http_client import HttpClient

        self.cli = HttpClient(f'/api/v2')

    def __enter__(self):
        response = self.cli.post('/subscription/vault?op=deactivation')
        RA(response).assert_status(HttpCode.CREATED)

    def __exit__(self, exc_type, exc_val, exc_tb):
        response = self.cli.post('/subscription/vault?op=activation')
        RA(response).assert_status(HttpCode.CREATED)


def init_test():
    init_did_backend()


def is_valid_object_id(oid: str):
    try:
        ObjectId(oid)
        return True
    except (InvalidId, TypeError):
        return False


def test_log(*args, **kwargs):
    """ Just for debug, if try test API, please set environment::

        TEST_DEBUG=True

    """
    if os.environ.get('TEST_DEBUG') == 'True':
        print(*args, **kwargs)

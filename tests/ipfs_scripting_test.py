# -*- coding: utf-8 -*-

"""
Testing file for ipfs-scripting module.
"""

import unittest
import json

from src import hive_setting
from tests.utils.http_client import HttpClient, TestConfig, RemoteResolver
from tests import init_test
from tests.utils_v1 import test_common


class IpfsScriptingTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.test_config = TestConfig()
        self.cli = HttpClient(f'{self.test_config.host_url}/api/v2/vault')
        self.cli2 = HttpClient(f'{self.test_config.host_url}/api/v2/vault', is_did2=True)
        self.file_name = 'ipfs-scripting/test.txt'
        self.file_content = 'File Content: 1234567890'
        # Owner's did and application did.
        self.did = RemoteResolver().get_did_str()
        self.app_did = test_common.app_id

    @staticmethod
    def _subscribe():
        HttpClient(f'{TestConfig().host_url}/api/v2').put('/subscription/vault')
        HttpClient(f'{TestConfig().host_url}/api/v2', is_did2=True).put('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

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
        response = self.cli2.patch(f'/ipfs-scripting/{script_name}', body)
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
            self.assertTrue(response_body[script_name]['anonymous_url'].startswith(hive_setting.IPFS_PROXY_URL))
        return response_body[script_name]['transaction_id']

    def test01_file_upload(self):
        name = 'ipfs_upload_file'
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
        response = self.cli2.put(f'/ipfs-scripting/stream/{self.__call_script_for_transaction_id(name)}',
                                 self.file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)

    def test02_file_download(self):
        name = 'ipfs_download_file'
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
        response = self.cli2.get(f'/ipfs-scripting/stream/{self.__call_script_for_transaction_id(name)}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.file_content)

    def test03_file_properties_without_params(self):
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

    def test04_file_hash(self):
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

    def test05_get_anonymous_file(self):
        name = 'ipfs_get_anonymous_file'
        self.__register_script(name, {
            "executable": {
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
        self.__call_script_for_transaction_id(name, check_anonymous=True)


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-

"""
Testing file for scripting module.
"""

import unittest
import json

from tests.utils.http_client import HttpClient


@unittest.skip
class ScriptingTestCase(unittest.TestCase):
    def __init__(self):
        super().__init__()
        self.cli = HttpClient('http://localhost:5000/api/v2/vault/scripting')
        self.file_content = 'File Content: 12345678'

    def __register_script(self, relative_url, body):
        response = self.cli.post(relative_url, body)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.text)

    def __call_script(self, relative_url, body, is_raw=False):
        response = self.cli.patch(relative_url, body)
        self.assertEqual(response.status_code, 200)
        return response.text if is_raw else json.loads(response.text)

    def test_register_script(self):
        self.__register_script('/database_insert', {
            "executable": {
                "output": True,
                "name": "database_insert",
                "type": "insert",
                "body": {
                    "collection": "script_database",
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

    def test_delete_script(self):
        response = self.cli.delete('/get_group_message2')
        self.assertEqual(response.status_code, 204)

    def test_call_script(self):
        self.__call_script('/database_insert', {
            "params": {
                "author": "John",
                "content": "message"
            }
        })

    def test_call_script_url(self):
        response = self.cli.get('/database_insert/@'
                                '/%7B%22params%22%3A%7B%22author%22%3A%22John%22%2C%22content%22%3A%22message%22%7D%7D')
        self.assertEqual(response.status_code, 200)

    def __call_script_for_transaction_id(self, script_name):
        response_body = self.__call_script(script_name, {
            "params": {
                "path": "test.txt"
            }
        })
        self.assertEqual(type(response_body), dict)
        self.assertTrue(script_name in response_body)
        self.assertEqual(type(response_body[script_name]), dict)
        self.assertTrue('transaction_id' in response_body[script_name])
        return response_body[script_name]['transaction_id']

    def test_file_upload(self):
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
        response = self.cli.put(f'/stream/{self.__call_script_for_transaction_id(name)}', self.file_content)
        self.assertEqual(response.status_code, 200)

    def test_file_download(self):
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
        response = self.cli.get(f'/stream/{self.__call_script_for_transaction_id(name)}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.file_content)


if __name__ == '__main__':
    unittest.main()

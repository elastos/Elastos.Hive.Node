# -*- coding: utf-8 -*-

"""
Testing file for files module.
"""

import unittest
import urllib

from tests.utils.http_client import HttpClient
from tests import init_test


class FilesTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient('http://localhost:5000/api/v2/vault')
        self.folder_name = ''  # root
        self.src_file_content = 'File Content: 12345678'
        self.dst_file_content = self.src_file_content
        self.src_file_name = 'src_file'
        self.dst_file_name = 'dst_file'

    def test01_upload_file(self):
        response = self.cli.put(f'/files/{self.src_file_name}',
                                self.src_file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)

    def test02_download_file(self):
        response = self.cli.get(f'/files/{self.src_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.src_file_content)

    def test03_move_file(self):
        response = self.cli.patch(f'/files/{self.src_file_name}?to={self.dst_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.dst_file_name)

    def test04_copy_file(self):
        response = self.cli.put(f'/files/{self.dst_file_name}?dst={self.src_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)

    def test05_list_folder(self):
        response = self.cli.get(f'/files/{self.folder_name}?comp=children')
        self.assertEqual(response.status_code, 200)

    def test06_get_properties(self):
        response = self.cli.get(f'/files/{self.src_file_name}?comp=metadata')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)

    def test07_get_hash(self):
        response = self.cli.get(f'/files/{self.src_file_name}?comp=hash')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)

    def test08_delete_file(self):
        response = self.cli.delete(f'/files/{self.src_file_name}')
        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()

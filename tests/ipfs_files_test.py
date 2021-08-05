# -*- coding: utf-8 -*-

"""
Testing file for ipfs files module.
"""

import unittest

from tests.utils.http_client import HttpClient, TestConfig
from tests import init_test


class IpfsFilesTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.test_config = TestConfig()
        self.cli = HttpClient(f'{self.test_config.host_url}/api/v2/vault')
        self.folder_name = ''  # root
        self.src_file_content = 'File Content: 12345678'
        self.dst_file_content = self.src_file_content
        self.src_file_name = 'src_file.txt'
        self.src_file_name2 = r'children/src_file2.txt'
        self.dst_file_name = 'dst_file'

    @staticmethod
    def _subscribe():
        HttpClient(f'{TestConfig().host_url}/api/v2').put('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_upload_file(self):
        response = self.cli.put(f'/ipfs-files/{self.src_file_name}',
                                self.src_file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)
        self.__check_remote_file_exist(self.src_file_name)

    def test11_upload_file2(self):
        response = self.cli.put(f'/ipfs-files/{self.src_file_name2}',
                                self.src_file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name2)
        self.__check_remote_file_exist(self.src_file_name2)

    def test02_download_file(self):
        response = self.cli.get(f'/ipfs-files/{self.src_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.src_file_content)

    def test03_move_file(self):
        response = self.cli.patch(f'/ipfs-files/{self.src_file_name}?to={self.dst_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.dst_file_name)
        self.__check_remote_file_exist(self.dst_file_name)

    def test04_copy_file(self):
        response = self.cli.put(f'/ipfs-files/{self.dst_file_name}?dest={self.src_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)
        self.__check_remote_file_exist(self.dst_file_name)
        self.__check_remote_file_exist(self.src_file_name)

    def test05_list_folder(self):
        response = self.cli.get(f'/ipfs-files/{self.folder_name}?comp=children')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('value' in response.json())
        self.assertEqual(type(response.json()['value']), list)

    def test06_get_properties(self):
        self.__check_remote_file_exist(self.src_file_name)

    def test07_get_hash(self):
        response = self.cli.get(f'/ipfs-files/{self.src_file_name}?comp=hash')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)

    def test08_delete_file(self):
        self.__delete_file(self.src_file_name)
        self.__delete_file(self.dst_file_name)

    def __check_remote_file_exist(self, file_name):
        response = self.cli.get(f'/ipfs-files/{file_name}?comp=metadata')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), file_name)
        return response.json()

    def __delete_file(self, file_name):
        response = self.cli.delete(f'/ipfs-files/{file_name}')
        self.assertEqual(response.status_code, 204)


if __name__ == '__main__':
    unittest.main()

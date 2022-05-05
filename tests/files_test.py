# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-files module.
"""
import os
import unittest

from src import hive_setting
from src.utils.http_client import HttpClient as Http

from tests import init_test
from tests.utils.http_client import HttpClient

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class IpfsFilesTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/vault')
        self.folder_name = 'ipfs_children'
        self.src_file_content = 'File Content: 12345678'
        self.dst_file_content = self.src_file_content
        self.src_file_name = 'ipfs_src_file.txt'
        self.src_public_name = 'ipfs_public_file.txt'
        self.src_file_cache = f'{BASE_DIR}/cache/test.txt'
        self.src_file_name2 = r'ipfs_children/ipfs_src_file2.txt'
        self.dst_file_name = 'ipfs_dst_file.txt'
        self.name_not_exist = 'name_not_exist'

    @staticmethod
    def _subscribe():
        HttpClient(f'/api/v2').put('/subscription/vault')

    @classmethod
    def setUpClass(cls):
        cls._subscribe()

    def test01_upload_file(self):
        with open(self.src_file_cache, 'rb') as f:
            response = self.cli.put(f'/files/{self.src_file_name}', f.read(), is_json=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)
        self.__check_remote_file_exist(self.src_file_name)

    def test01_upload_file2(self):
        response = self.cli.put(f'/files/{self.src_file_name2}',
                                self.src_file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name2)
        self.__check_remote_file_exist(self.src_file_name2)

    def test01_upload_public_file(self):
        script_name = self.src_public_name.split(".")[0]
        response = self.cli.put(f'/files/{self.src_public_name}?public=true&script_name={script_name}',
                                self.src_file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_public_name)
        self.assertTrue(bool(response.json().get('cid')))
        self.__check_remote_file_exist(self.src_public_name)

        # check cid
        response = Http().post(f'{hive_setting.IPFS_NODE_URL}/api/v0/cat?arg={response.json().get("cid")}', None, None, is_body=False, success_code=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.src_file_content)

        # check fileDownload script
        from tests.scripting_test import IpfsScriptingTestCase
        scripting_test = IpfsScriptingTestCase()
        scripting_test.call_and_stream(script_name, None, file_content=self.src_file_content)

        # clean the script and the file.
        scripting_test.delete_script(script_name)
        self.__delete_file(self.src_public_name)

    def test01_upload_file_invalid_parameter(self):
        response = self.cli.put(f'/files/', self.src_file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 405)

    def test02_download_file(self):
        response = self.cli.get(f'/files/{self.src_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.src_file_content)

    def test02_download_file_invalid_parameter(self):
        response = self.cli.get(f'/files/')
        self.assertEqual(response.status_code, 400)

    def test03_move_file(self):
        response = self.cli.patch(f'/files/{self.src_file_name}?to={self.dst_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.dst_file_name)
        self.__check_remote_file_exist(self.dst_file_name)

    def test03_move_file_invalid_parameter(self):
        response = self.cli.patch(f'/files/{self.src_file_name}?to=')
        self.assertEqual(response.status_code, 400)

    def test04_copy_file(self):
        response = self.cli.put(f'/files/{self.dst_file_name}?dest={self.src_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)
        self.__check_remote_file_exist(self.dst_file_name)
        self.__check_remote_file_exist(self.src_file_name)

    def test04_copy_file_invalid_parameter(self):
        response = self.cli.put(f'/files/{self.dst_file_name}?dest={self.dst_file_name}')
        self.assertEqual(response.status_code, 400)

    def test05_list_folder(self):
        response = self.cli.get(f'/files/{self.folder_name}?comp=children')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('value' in response.json())
        self.assertEqual(type(response.json()['value']), list)
        self.assertEqual(len(response.json()['value']), 1)
        self.assertEqual(response.json()['value'][0]['name'], self.src_file_name2)

    def test06_get_properties(self):
        self.__check_remote_file_exist(self.src_file_name)

    def test06_get_properties_invalid_parameter(self):
        response = self.cli.get(f'/files/?comp=metadata')
        self.assertEqual(response.status_code, 400)

    def test07_get_hash(self):
        response = self.cli.get(f'/files/{self.src_file_name}?comp=hash')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)

    def test07_get_hash_invalid_parameter(self):
        response = self.cli.get(f'/files/?comp=hash')
        self.assertEqual(response.status_code, 400)

    def test08_delete_file(self):
        self.__delete_file(self.src_file_name)
        self.__delete_file(self.src_file_name2)
        self.__delete_file(self.dst_file_name)

    def test08_delete_file_not_exist(self):
        response = self.cli.delete(f'/files/{self.name_not_exist}')
        self.assertEqual(response.status_code, 404)

    def test08_delete_file_invalid_parameter(self):
        response = self.cli.delete('/files/')
        self.assertEqual(response.status_code, 405)

    def __check_remote_file_exist(self, file_name):
        response = self.cli.get(f'/files/{file_name}?comp=metadata')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), file_name)
        return response.json()

    def __delete_file(self, file_name):
        response = self.cli.delete(f'/files/{file_name}')
        self.assertTrue(response.status_code in [204, 404])


if __name__ == '__main__':
    unittest.main()

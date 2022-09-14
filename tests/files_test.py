# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-files module.
"""
import os
import unittest

from src import hive_setting

from tests import init_test, VaultFilesUsageChecker, VaultFreezer
from tests.utils.http_client import HttpClient
from tests.utils.resp_asserter import RA
from tests.utils.tester_http import HttpCode

BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))


class IpfsFilesTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v2/vault')

        self.folder_name = 'ipfs_children'

        # for uploading, and copying back
        self.src_file_name = 'ipfs_src_file.node.txt'
        self.src_file_content = 'File Content: 12345678' + ('9' * 200)

        # just for uploading, from local file
        self.src_file_name2 = rf'{self.folder_name}/ipfs_src_file2.node.txt'
        self.src_file_cache2 = f'{BASE_DIR}/cache/test.txt'

        # for moving
        self.dst_file_name = 'ipfs_dst_file.node.txt'
        self.dst_file_content = self.src_file_content

        # for public sharing
        self.src_public_name = 'ipfs_public_file.node.txt'
        self.src_public_content = self.src_file_content

        # for not existing check
        self.name_not_exist = 'name_not_exist'

    @classmethod
    def setUpClass(cls):
        # subscribe
        HttpClient(f'/api/v2').put('/subscription/vault')

    def get_remote_file_size(self, file_name):
        """ if not exists, return 0 """
        response = self.cli.get(f'/files/{file_name}?comp=metadata')
        RA(response).assert_status(200, 404)
        if response.status_code == 404:
            return 0

        return RA(response).body().get('size', int)

    def test01_upload_file(self):
        def upload_file(name, content):
            src_size, dst_size = self.get_remote_file_size(file_name), len(file_content)
            with VaultFilesUsageChecker(dst_size - src_size) as _:
                response = self.cli.put(f'/files/{name}', content, is_json=False)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json().get('name'), name)
                self.__check_remote_file_exist(name)

        # upload self.src_file_name
        file_name, file_content = self.src_file_name, self.src_file_content.encode()

        with VaultFreezer() as _:
            response_ = self.cli.put(f'/files/{file_name}', file_content, is_json=False)
            RA(response_).assert_status(HttpCode.FORBIDDEN)

        upload_file(file_name, file_content)

        # upload self.src_file_name2
        file_name = self.src_file_name2
        with open(self.src_file_cache2, 'rb') as f:
            file_content = f.read()
        upload_file(file_name, file_content)

    def test01_upload_public_file(self):
        script_name = self.src_public_name.split(".")[0]
        response = self.cli.put(f'/files/{self.src_public_name}?public=true&script_name={script_name}',
                                self.src_public_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_public_name)
        self.assertTrue(bool(response.json().get('cid')))
        self.__check_remote_file_exist(self.src_public_name)

        # check cid
        from src.utils.http_client import HttpClient as Http
        response = Http().post(f'{hive_setting.IPFS_NODE_URL}/api/v0/cat?arg={response.json().get("cid")}', None, None, is_body=False, success_code=200)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.src_public_content)

        # check fileDownload script
        from tests.scripting_test import IpfsScriptingTestCase
        scripting_test = IpfsScriptingTestCase()
        scripting_test.call_and_execute_transaction(script_name, script_name, download_content=self.src_public_content)

        # clean the script and the file.
        scripting_test.delete_script(script_name)
        self.__delete_file(self.src_public_name)

    def test01_upload_file_invalid_parameter(self):
        response = self.cli.put(f'/files/', self.src_file_content.encode(), is_json=False)
        self.assertEqual(response.status_code, 405)

    def test02_download_file(self):
        with VaultFreezer() as _:
            response = self.cli.get(f'/files/{self.src_file_name}')
            self.assertEqual(response.status_code, 200)

        response = self.cli.get(f'/files/{self.src_file_name}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, self.src_file_content)

    def test02_download_file_invalid_parameter(self):
        response = self.cli.get(f'/files/')
        self.assertEqual(response.status_code, 400)

    def test03_move_file(self):
        with VaultFreezer() as _:
            response = self.cli.patch(f'/files/{self.src_file_name}?to={self.dst_file_name}')
            RA(response).assert_status(HttpCode.FORBIDDEN)

        with VaultFilesUsageChecker(0) as _:
            response = self.cli.patch(f'/files/{self.src_file_name}?to={self.dst_file_name}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json().get('name'), self.dst_file_name)
            self.__check_remote_file_exist(self.dst_file_name)

    def test03_move_file_invalid_parameter(self):
        response = self.cli.patch(f'/files/{self.src_file_name}?to=')
        self.assertEqual(response.status_code, 400)

    def test04_copy_file(self):
        with VaultFreezer() as _:
            response = self.cli.put(f'/files/{self.dst_file_name}?dest={self.src_file_name}')
            RA(response).assert_status(HttpCode.FORBIDDEN)

        with VaultFilesUsageChecker(len(self.src_file_content)) as _:
            response = self.cli.put(f'/files/{self.dst_file_name}?dest={self.src_file_name}')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json().get('name'), self.src_file_name)
            self.__check_remote_file_exist(self.dst_file_name)
            self.__check_remote_file_exist(self.src_file_name)

    def test04_copy_file_invalid_parameter(self):
        response = self.cli.put(f'/files/{self.dst_file_name}?dest={self.dst_file_name}')
        self.assertEqual(response.status_code, 400)

    def test05_list_folder(self):
        with VaultFreezer() as _:
            response = self.cli.get(f'/files/{self.folder_name}?comp=children')
            RA(response).assert_status(HttpCode.OK)

        # list root folder
        response = self.cli.get(f'/files/?comp=children')
        RA(response).assert_status(200)

        # list sub-folder
        response = self.cli.get(f'/files/{self.folder_name}?comp=children')
        RA(response).assert_status(200)
        files = RA(response).body().get('value', list)
        self.assertEqual(len(files), 1)
        file = files[0]
        self.assertEqual(file['name'], self.src_file_name2)

    def test06_get_properties(self):
        with VaultFreezer() as _:
            response = self.cli.get(f'/files/{self.src_file_name}?comp=metadata')
            RA(response).assert_status(HttpCode.OK)
            RA(response).body().assert_equal('name', self.src_file_name)

        self.__check_remote_file_exist(self.src_file_name)

    def test06_get_properties_invalid_parameter(self):
        response = self.cli.get(f'/files/?comp=metadata')
        self.assertEqual(response.status_code, 400)

    def test07_get_hash(self):
        with VaultFreezer() as _:
            response = self.cli.get(f'/files/{self.src_file_name}?comp=hash')
            RA(response).assert_status(HttpCode.OK)

        response = self.cli.get(f'/files/{self.src_file_name}?comp=hash')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('name'), self.src_file_name)

    def test07_get_hash_invalid_parameter(self):
        response = self.cli.get(f'/files/?comp=hash')
        self.assertEqual(response.status_code, 400)

    def test08_delete_file(self):
        with VaultFreezer() as _:
            response = self.cli.delete(f'/files/{self.src_file_name}')
            RA(response).assert_status(HttpCode.FORBIDDEN)

        with VaultFilesUsageChecker(-len(self.src_file_content)) as _:
            self.__delete_file(self.src_file_name)

        self.__delete_file(self.src_file_name2)
        self.__delete_file(self.dst_file_name)

    def test08_delete_file_not_exist(self):
        response = self.cli.delete(f'/files/{self.name_not_exist}')
        self.assertEqual(response.status_code, 404)

    def test08_delete_file_invalid_parameter(self):
        response = self.cli.delete('/files/')
        self.assertEqual(response.status_code, 405)

    def test09_sdk_encrypt(self):
        # upload file with encrypt information.
        file_name, file_content = self.src_file_name, self.src_file_content.encode()
        response = self.cli.put(f'/files/{file_name}?is_encrypt=true&encrypt_method=user_did', file_content, is_json=False)
        self.assertEqual(response.status_code, 200)

        # check on list file API.
        response = self.cli.get(f'/files/?comp=children')
        RA(response).assert_status(200)
        files = RA(response).body().get('value', list)
        self.assertGreaterEqual(len(files), 1)
        files = list(filter(lambda f: f['name'] == file_name, files))
        self.assertEqual(len(files), 1)
        file = files[0]
        self.assertEqual(file['is_encrypt'], True)
        self.assertEqual(file['encrypt_method'], 'user_did')

        # check on file property.
        response = self.cli.get(f'/files/{file_name}?comp=metadata')
        RA(response).assert_status(HttpCode.OK)
        RA(response).body().assert_equal('name', file_name)
        RA(response).body().assert_equal('is_encrypt', True)
        RA(response).body().assert_equal('encrypt_method', 'user_did')

        # delete file
        response = self.cli.delete(f'/files/{file_name}')
        self.assertEqual(response.status_code, 204)

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

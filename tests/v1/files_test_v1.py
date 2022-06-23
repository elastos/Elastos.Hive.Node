# -*- coding: utf-8 -*-

"""
Testing file for the ipfs-files module.
"""
import unittest

from tests import init_test
from tests.files_test import VaultFilesUsageChecker
from tests.utils.http_client import HttpClient
from tests.utils.resp_asserter import RA


class IpfsFilesTestCase(unittest.TestCase):
    def __init__(self, method_name='runTest'):
        super().__init__(method_name)
        init_test()
        self.cli = HttpClient(f'/api/v1')

        # for uploading, and copying back
        self.src_file_name = 'ipfs_src_file.node.txt'
        self.src_file_content = 'File Content: 12345678' + ('9' * 200)

    @classmethod
    def setUpClass(cls):
        # subscribe
        response = HttpClient(f'/api/v1').post('/service/vault/create')
        RA(response).assert_status(200)

    def __get_remote_file_size(self, file_name):
        """ if not exists, return 0 """
        response = self.cli.get(f'/files/properties?path={file_name}')
        RA(response).assert_status(200, 404)
        if response.status_code == 404:
            return 0
        return RA(response).body().get('size', int)

    def __check_remote_file_exist(self, file_name):
        response = self.cli.get(f'/files/properties?path={file_name}')
        RA(response).assert_status(200)

    def test01_upload_file(self):
        def upload_file(name, content):
            src_size, dst_size = self.__get_remote_file_size(file_name), len(file_content)
            with VaultFilesUsageChecker(dst_size - src_size) as _:
                response = self.cli.post(f'/files/upload/{name}', content, is_json=False)
                self.assertEqual(response.status_code, 200)
                self.__check_remote_file_exist(name)

        file_name, file_content = self.src_file_name, self.src_file_content.encode()
        upload_file(file_name, file_content)


if __name__ == '__main__':
    unittest.main()

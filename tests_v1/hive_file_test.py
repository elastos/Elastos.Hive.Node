import json
import unittest
import flask_unittest

from hive.util.constants import HIVE_MODE_TEST
from src import create_app
from src.utils.executor import executor
from tests import test_log
from tests_v1 import test_common
from tests_v1.test_common import create_upload_file, initialize_access_tokens


class HiveFileTestCase(flask_unittest.ClientTestCase):
    app = create_app(mode=HIVE_MODE_TEST)

    @classmethod
    def setUpClass(cls):
        test_log("HiveFileTestCase: Setting up HiveFileTestCase\n")

    @classmethod
    def tearDownClass(cls):
        # wait flask-executor to finish
        executor.shutdown()
        test_log("HiveAuthTestCase: \n\nShutting down HiveFileTestCase")

    def clear_all_test_files(self, client):
        r1, s = self.parse_response(client.get('/api/v1/files/list/folder', headers=self.auth))
        if r1["_status"] != "OK":
            return
        for info in r1["file_info_list"]:
            client.post('/api/v1/files/delete', data=json.dumps({"path": info["name"]}), headers=self.auth)

    def setUp(self, client):
        test_log("HiveFileTestCase: \n")
        self.app.config['TESTING'] = True
        self.content_type = ("Content-Type", "application/json")
        self.upload_file_content_type = ("Content-Type", "multipart/form-data")
        self.json_header = [self.content_type, ]

        initialize_access_tokens(self, client)
        self.init_auth()
        self.did = test_common.get_auth_did()
        self.app_id = test_common.get_auth_app_did()

        test_common.create_vault_if_not_exist(self, client)

    def init_auth(self):
        token = test_common.get_auth_token()
        self.auth = [("Authorization", "token " + token), self.content_type]
        self.upload_auth = [("Authorization", "token " + token), ]

    def tearDown(self, client):
        test_log("HiveFileTestCase: \n")
        test_common.delete_test_auth_token()
        # self.clear_all_test_files()

    def parse_response(self, r):
        try:
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert201(self, status):
        self.assertEqual(status, 201)

    def test01_create_and_upload_file_root(self, client):
        test_log("HiveFileTestCase: \nRunning test_b_create_and_upload_file_root")
        path = "test_0.txt"
        create_upload_file(self, client, path, f"Hello Temp {path}!")

    def test02_create_and_upload_file_in_folder(self, client):
        test_log("HiveFileTestCase: \nRunning test_c_create_and_upload_file_in_folder")
        path = "folder1/test_0.txt"
        create_upload_file(self, client, path, f"Hello Temp {path}!")

    def test03_create_and_upload_file_further_folder(self, client):
        test_log("HiveFileTestCase: \nRunning test_d_create_and_upload_file_further_folder")
        path = "folder1/folder2/folder3/test_0.txt"
        create_upload_file(self, client, path, f"Hello Temp {path}!")

    def test04_download_file(self, client):
        test_log("HiveFileTestCase: \nRunning test_f_download_file")
        path, file_content = "folder1/test_01.txt", "Hello Temp folder1/test_01.txt!"
        create_upload_file(self, client, path, file_content)
        r = client.get(f'api/v1/files/download?path={path}', headers=self.auth)
        self.assert200(r.status_code)
        self.assertEqual(r.get_data(as_text=True), file_content)
        test_log(f"HiveFileTestCase: data: {r.get_data(as_text=True)}")

    def test05_move_file(self, client):
        test_log("HiveFileTestCase: \nRunning test_g_move_file")
        src_path, dst_path = 'folder1/test_02.txt', 'folder1/test_03.txt'
        create_upload_file(self, client, src_path, f"Hello Temp test {src_path}!")

        move_file = {"src_path": src_path, "dst_path": dst_path}
        rt, s = self.parse_response(
            client.post('/api/v1/files/move', data=json.dumps(move_file), headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        self.check_file_exists(client, src_path, exists=False)
        self.check_file_exists(client, dst_path)

    def test06_copy_file(self, client):
        test_log("HiveFileTestCase: \nRunning test_i_copy_file")
        src_path, dst_path = 'folder1/test_04.txt', 'folder1/test_05.txt'
        create_upload_file(self, client, src_path, f"Hello Temp {src_path}!")

        move_file = {"src_path": src_path, "dst_path": dst_path}
        rt, s = self.parse_response(
            client.post('/api/v1/files/copy', data=json.dumps(move_file), headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        self.check_file_exists(client, src_path)
        self.check_file_exists(client, dst_path)

    def test07_file_properties(self, client):
        test_log("HiveFileTestCase: Test file_properties.")
        path = 'folder1/test_06.txt'
        create_upload_file(self, client, path, f"Hello Temp {path}!")
        self.check_file_exists(client, path)

    def test08_file_hash(self, client):
        test_log("HiveFileTestCase: \nRunning test_k_file_hash")
        path = 'folder1/test_07.txt'
        create_upload_file(self, client, path, f"Hello Temp {path}!")
        r1, s = self.parse_response(
            client.get(f'/api/v1/files/file/hash?path={path}', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")
        test_log(f"HiveFileTestCase: {json.dumps(r1)}")

    def test09_delete_file(self, client):
        test_log("HiveFileTestCase: \nRunning test_l_delete_file")
        path = 'folder1/test_08.txt'
        create_upload_file(self, client, path, f"Hello Temp {path}!")
        r, s = self.parse_response(
            client.post('/api/v1/files/delete', data=json.dumps({"path": path}), headers=self.auth)
        )
        self.assert200(s)

        self.check_file_exists(client, path, exists=False)
        self.do_remove_file(client, "test_0.txt")
        self.do_remove_file(client, "folder1/test_0.txt")
        self.do_remove_file(client, "folder1/folder2/folder3/test_0.txt")
        self.do_remove_file(client, "folder1/test_01.txt")
        self.do_remove_file(client, "folder1/test_02.txt")
        self.do_remove_file(client, "folder1/test_03.txt")
        self.do_remove_file(client, "folder1/test_04.txt")
        self.do_remove_file(client, "folder1/test_05.txt")
        self.do_remove_file(client, "folder1/test_06.txt")
        self.do_remove_file(client, "folder1/test_07.txt")
        self.do_remove_file(client, "folder1/test_08.txt")

    def do_remove_file(self, client, path):
        r, s = self.parse_response(
            client.post('/api/v1/files/delete', data=json.dumps({"path": path}), headers=self.auth)
        )
        self.assert200(s)

    def check_file_exists(self, client, path, exists=True):
        r1, s = self.parse_response(
            client.get(f'/api/v1/files/properties?path={path}', headers=self.auth)
        )
        if exists:
            self.assertEqual(r1["_status"], "OK")
        else:
            self.assertNotEqual(r1["_status"], "OK")


if __name__ == '__main__':
    unittest.main()

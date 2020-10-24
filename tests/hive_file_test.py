import json
import sys
import unittest
import logging
from io import BytesIO

from flask import appcontext_pushed, g
from contextlib import contextmanager
from hive import create_app
from tests import test_common

logger = logging.getLogger()
logger.level = logging.DEBUG


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HiveFileTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveFileTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HiveFileTestCase").debug("Setting up HiveFileTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HiveAuthTestCase").debug("\n\nShutting down HiveFileTestCase")
        logger.removeHandler(cls.stream_handler)

    def clear_all_test_files(self):
        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder', headers=self.auth)
        )
        if r1["_status"] != "OK":
            return
        for info in r1["file_info_list"]:
            self.test_client.post('/api/v1/files/delete',
                                  data=json.dumps({
                                      "path": info["name"]
                                  }),
                                  headers=self.auth)

    def setUp(self):
        logging.getLogger("HiveFileTestCase").info("\n")
        self.app = create_app(True)
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")
        self.upload_file_content_type = ("Content-Type", "multipart/form-data")

        self.json_header = [
            self.content_type,
        ]
        test_common.setup_test_auth_token()
        self.init_auth()
        self.clear_all_test_files()

    def init_auth(self):
        token = test_common.get_auth_token(self)
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]
        self.upload_auth = [
            ("Authorization", "token " + token),
            # self.upload_file_content_type,
        ]

    def tearDown(self):
        logging.getLogger("HiveFileTestCase").info("\n")
        test_common.delete_test_auth_token()
        self.clear_all_test_files()

    def init_db(self):
        pass

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

    def create_upload_file(self, file_name, data):
        temp = BytesIO()
        temp.write(data.encode(encoding="utf-8"))
        temp.seek(0)
        temp.name = 'temp.txt'

        upload_file_url = "/api/v1/files/upload/" + file_name
        r2, s = self.parse_response(
            self.test_client.post(upload_file_url,
                                  data=temp,
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r2["_status"], "OK")

        r3, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?path=' + file_name, headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r3["_status"], "OK")
        logging.getLogger("HiveFileTestCase").debug(json.dumps(r3))

    def test_b_create_and_upload_file_root(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_b_create_and_upload_file_root")
        self.create_upload_file("test_0.txt", "Hello Temp test 0!")

    def test_c_create_and_upload_file_in_folder(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_c_create_and_upload_file_in_folder")
        self.create_upload_file("folder1/test1.txt", "Hello Temp test 1!")

    def test_d_create_and_upload_file_further_folder(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_d_create_and_upload_file_further_folder")
        self.create_upload_file("folder1/folder2/folder3/test0.txt", "Hello Temp test 0!")

    def test_e_create_and_upload_file_new_folder(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_e_create_and_upload_file_new_folder")
        self.create_upload_file("f1/f2/f3/test_f3_1.txt", "Hello Temp test f3_1!")
        self.create_upload_file("f1/f2/f3/test_f3_2.txt", "Hello Temp test f3_2!")

    def test_f_download_file(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_f_download_file")
        self.create_upload_file("f1/f2/f3/test_f3_2.txt", "Hello Temp test f3_2!")
        r = self.test_client.get('api/v1/files/download?path=f1/f2/f3/test_f3_2.txt', headers=self.auth)

        self.assert200(r.status_code)
        logging.getLogger("HiveFileTestCase").debug("data:" + str(r.get_data()))

    def test_g_move_file(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_g_move_file")
        self.create_upload_file("f1/test_f1.txt", "Hello Temp test f1_2!")

        move_file = {
            "src_path": "f1/test_f1.txt",
            "dst_path": "f1/f2/f3/test_f1.txt",
        }

        rt, s = self.parse_response(
            self.test_client.post('/api/v1/files/move',
                                  data=json.dumps(move_file),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?path=f1/test_f1.txt', headers=self.auth)
        )
        self.assertNotEqual(r1["_status"], "OK")

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?path=f1/f2/f3/test_f1.txt', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")

    def test_h_move_folder(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_h_move_folder")
        self.create_upload_file("f1/f2/f3/f4/test_f4.txt", "Hello Temp test f1_2!")
        self.create_upload_file("f1/f2/f3/fr4_1/test_fr4_1.txt", "Hello Temp test fr4_1!")
        self.create_upload_file("f1/f2/f3/fr4_1/test_fr4_1_2.txt", "Hello Temp test fr4_2!")

        r2, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder?path=f1/f2/f3', headers=self.auth)
        )

        move_file = {
            "src_path": "f1/f2/f3/fr4_1",
            "dst_path": "f1/f2/f3/f4",
        }

        r1, s = self.parse_response(
            self.test_client.post('/api/v1/files/move',
                                  data=json.dumps(move_file),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")

        r2, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder?path=f1/f2/f3', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r2["_status"], "OK")
        logging.getLogger("HiveFileTestCase").debug(json.dumps(r2))

        r3, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder?path=f1/f2/f3/f4', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r3["_status"], "OK")
        logging.getLogger("HiveFileTestCase").debug(json.dumps(r3))

    def test_i_copy_file(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_i_copy_file")
        self.create_upload_file("f1/f2/test_f2.txt", "Hello Temp test f2_2!")

        move_file = {
            "src_path": "f1/f2/test_f2.txt",
            "dst_path": "f1/f2/f3/test_f2.txt",
        }

        rt, s = self.parse_response(
            self.test_client.post('/api/v1/files/copy',
                                  data=json.dumps(move_file),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?path=f1/f2/test_f2.txt', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")

        r2, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?path=f1/f2/f3/test_f2.txt', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r2["_status"], "OK")

    def test_j_copy_folder(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_j_copy_folder")
        self.create_upload_file("f1/f2/f3/f4/test_f4_1.txt", "Hello Temp test f4_1!")
        self.create_upload_file("f1/f2/f3/fr4_2/test_fr4_2.txt", "Hello Temp test fr4_1!")
        self.create_upload_file("f1/f2/f3/fr4_2/test_fr4_2_2.txt", "Hello Temp test fr4_2!")

        move_file = {
            "src_path": "f1/f2/f3/fr4_2",
            "dst_path": "f1/f2/f3/f4/fr_42",
        }

        r1, s = self.parse_response(
            self.test_client.post('/api/v1/files/copy',
                                  data=json.dumps(move_file),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")

        r2, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder?path=f1/f2/f3', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r2["_status"], "OK")
        logging.getLogger("HiveFileTestCase").debug(json.dumps(r2))

        r3, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder?path=f1/f2/f3/f4', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r3["_status"], "OK")
        logging.getLogger("HiveFileTestCase").debug(json.dumps(r3))

    def test_k_file_hash(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_k_file_hash")
        self.create_upload_file("f1/f2/test_f2_hash.txt", "Hello Temp test f2_hash!")
        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/file/hash?path=f1/f2/test_f2_hash.txt', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")
        logging.getLogger("HiveFileTestCase").debug(json.dumps(r1))

    def test_l_delete_file(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_l_delete_file")
        self.create_upload_file("f1/test_f1.txt", "Hello Temp test f1!")
        self.create_upload_file("f1/test_f2.txt", "Hello Temp test f1!")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/files/delete',
                                  data=json.dumps({
                                      "path": "f1/test_f1.txt"
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?path=f1/test_f1.txt', headers=self.auth)
        )
        self.assertNotEqual(r1["_status"], "OK")

    def test_m_delete_folder(self):
        logging.getLogger("HiveFileTestCase").debug("\nRunning test_m_delete_folder")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/files/delete',
                                  data=json.dumps({
                                      "path": "f1"
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")
        logging.getLogger("HiveFileTestCase").debug(json.dumps(r1))


if __name__ == '__main__':
    unittest.main()

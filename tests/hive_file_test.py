import json
import os
import unittest
import tempfile
import sqlite3
from io import StringIO, BytesIO

from flask import session, request, make_response, render_template, appcontext_pushed, g
from contextlib import closing, contextmanager
from hive import create_app
import test_common


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HiveFileTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveFileTestCase, self).__init__(methodName)

    def clear_all_test_files(self):
        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder', headers=self.auth)
        )
        self.assert200(s)
        if r1["_status"] != "OK":
            return
        for name in r1["files"]:
            if name[-1] == '/':
                self.test_client.post('/api/v1/files/deleter/folder',
                                      data=json.dumps({
                                          "name": name
                                      }),
                                      headers=self.auth)
            else:
                self.test_client.post('/api/v1/files/deleter/file',
                                      data=json.dumps({
                                          "name": name
                                      }),
                                      headers=self.auth)

    def setUp(self):
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")
        self.upload_file_content_type = ("Content-Type", "multipart/form-data")

        self.json_header = [
            self.content_type,
        ]
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
        self.clear_all_test_files()
        pass

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
        filename = {"name": file_name}

        r, s = self.parse_response(
            self.test_client.post('/api/v1/files/creator/file',
                                  data=json.dumps(filename),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        upload_file_url = r["upload_file_url"]

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?name=' + file_name, headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")

        temp = BytesIO()
        temp.write(data.encode(encoding="utf-8"))
        temp.seek(0)
        temp.name = 'hello-temp.txt'

        r2, s = self.parse_response(
            self.test_client.post(upload_file_url,
                                  data=temp,
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r2["_status"], "OK")

        r3, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?name=' + file_name, headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r3["_status"], "OK")
        print(json.dumps(r3))

    def test_create_folder(self):
        file_name = {
            "name": "folder1/folder2",
        }

        rt, s = self.parse_response(
            self.test_client.post('/api/v1/files/creator/folder',
                                  data=json.dumps(file_name),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?name=folder1/folder2', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")
        print(json.dumps(r1))

    def test_create_and_upload_file_root(self):
        self.create_upload_file("test_0.txt", "Hello Temp test 0!")

    def test_create_and_upload_file_in_folder(self):
        self.create_upload_file("folder1/test1.txt", "Hello Temp test 1!")

    def test_create_and_upload_file_further_folder(self):
        self.create_upload_file("folder1/folder2/folder3/test0.txt", "Hello Temp test 0!")

    def test_create_and_upload_file_new_folder(self):
        self.create_upload_file("f1/f2/f3/test_f3_1.txt", "Hello Temp test f3_1!")
        self.create_upload_file("f1/f2/f3/test_f3_2.txt", "Hello Temp test f3_2!")

    def test_download_file(self):
        self.create_upload_file("f1/f2/f3/test_f3_2.txt", "Hello Temp test f3_2!")
        r = self.test_client.get('api/v1/files/downloader?name=f1/f2/f3/test_f3_2.txt', headers=self.auth)

        self.assert200(r.status_code)
        print("data:" + str(r.get_data()))

    def test_move_file(self):
        self.create_upload_file("f1/test_f1.txt", "Hello Temp test f1_2!")

        move_file = {
            "src_name": "f1/test_f1.txt",
            "dst_name": "f1/f2/f3/test_f1.txt",
        }

        rt, s = self.parse_response(
            self.test_client.post('/api/v1/files/mover',
                                  data=json.dumps(move_file),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?name=f1/test_f1.txt', headers=self.auth)
        )
        self.assert200(s)
        self.assertNotEqual(r1["_status"], "OK")

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?name=f1/f2/f3/test_f1.txt', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")

    def test_move_folder(self):
        self.create_upload_file("f1/f2/f3/f4/test_f4.txt", "Hello Temp test f1_2!")
        self.create_upload_file("f1/f2/f3/fr4_1/test_fr4_1.txt", "Hello Temp test fr4_1!")
        self.create_upload_file("f1/f2/f3/fr4_1/test_fr4_1_2.txt", "Hello Temp test fr4_2!")

        move_file = {
            "src_name": "f1/f2/f3/fr4_1",
            "dst_name": "f1/f2/f3/f4",
        }

        r1, s = self.parse_response(
            self.test_client.post('/api/v1/files/mover',
                                  data=json.dumps(move_file),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")

        r2, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder?name=f1/f2/f3', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r2["_status"], "OK")
        print(json.dumps(r2))

        r3, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder?name=f1/f2/f3/f4', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r3["_status"], "OK")
        print(json.dumps(r3))

    def test_copy_file(self):
        self.create_upload_file("f1/f2/test_f2.txt", "Hello Temp test f2_2!")

        move_file = {
            "src_name": "f1/f2/test_f2.txt",
            "dst_name": "f1/f2/f3/test_f2.txt",
        }

        rt, s = self.parse_response(
            self.test_client.post('/api/v1/files/copier',
                                  data=json.dumps(move_file),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?name=f1/f2/test_f2.txt', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")

        r2, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?name=f1/f2/f3/test_f2.txt', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r2["_status"], "OK")

    def test_copy_folder(self):
        self.create_upload_file("f1/f2/f3/f4/test_f4_1.txt", "Hello Temp test f4_1!")
        self.create_upload_file("f1/f2/f3/fr4_2/test_fr4_2.txt", "Hello Temp test fr4_1!")
        self.create_upload_file("f1/f2/f3/fr4_2/test_fr4_2_2.txt", "Hello Temp test fr4_2!")

        move_file = {
            "src_name": "f1/f2/f3/fr4_2",
            "dst_name": "f1/f2/f3/f4/fr_42",
        }

        r1, s = self.parse_response(
            self.test_client.post('/api/v1/files/copier',
                                  data=json.dumps(move_file),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")

        r2, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder?name=f1/f2/f3', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r2["_status"], "OK")
        print(json.dumps(r2))

        r3, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder?name=f1/f2/f3/f4', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r3["_status"], "OK")
        print(json.dumps(r3))

    def test_file_hash(self):
        self.create_upload_file("f1/f2/test_f2_hash.txt", "Hello Temp test f2_hash!")
        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/file/hash?name=f1/f2/test_f2_hash.txt', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")
        print(json.dumps(r1))

    def test_delete_file(self):
        self.create_upload_file("f1/test_f1.txt", "Hello Temp test f1!")
        self.create_upload_file("f1/test_f2.txt", "Hello Temp test f1!")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/files/deleter/file',
                                  data=json.dumps({
                                      "name": "f1/test_f1.txt"
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/properties?name=f1/test_f1.txt', headers=self.auth)
        )
        self.assert200(s)
        self.assertNotEqual(r1["_status"], "OK")

    def test_delete_folder(self):
        r, s = self.parse_response(
            self.test_client.post('/api/v1/files/deleter/folder',
                                  data=json.dumps({
                                      "name": "f1"
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)

        r1, s = self.parse_response(
            self.test_client.get('/api/v1/files/list/folder', headers=self.auth)
        )

        self.assert200(s)
        self.assertEqual(r1["_status"], "OK")
        print(json.dumps(r1))


if __name__ == '__main__':
    unittest.main()

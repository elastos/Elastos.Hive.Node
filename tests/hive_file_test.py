import json
import os
import unittest
import tempfile
import sqlite3
from io import StringIO, BytesIO

from flask import session, request, make_response, render_template, appcontext_pushed, g
from contextlib import closing, contextmanager
from hive import create_app

token = "f8f54b38-c022-11ea-88b6-f45c898fba57"


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class SampleTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(SampleTestCase, self).__init__(methodName)

    def setUp(self):
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")
        self.upload_file_content_type = ("Content-Type", "multipart/form-data")

        self.json_header = [
            self.content_type,
        ]
        self.init_all_auth()

    def init_auth(self):
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

    def init_upload_auth(self):
        self.upload_auth = [
            ("Authorization", "token " + token),
            self.upload_file_content_type,
        ]

    def init_all_auth(self):
        self.init_auth()
        self.init_upload_auth()

    def tearDown(self):
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

    def test_upload_file(self):
        temp = BytesIO()
        temp.write(b'Hello Temp!')
        temp.seek(0)
        temp.name = 'hello-temp.txt'
        files = {'file': (temp, "test.txt")}

        r, s = self.parse_response(
            self.test_client.post('api/v1/file/uploader',
                                  data=files,
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_upload_file_new(self):
        file_pro = {"file_name": "test_big_file.txt",
                    "other_property": "test_property"
                    }

        rt, s = self.parse_response(
            self.test_client.post('api/v1/file/create',
                                  data=json.dumps(file_pro),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        upload_file_url = rt["upload_file_url"]

        temp = BytesIO()
        temp.write(b'Hello Temp!')
        temp.seek(0)
        temp.name = 'hello-temp.txt'
        # files = {'file': (temp, "test.txt")}

        r, s = self.parse_response(
            self.test_client.post(upload_file_url,
                                  data=temp,
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_list_file(self):
        r1 = self.test_client.get(
            'api/v1/file/list', headers=self.auth
        )
        self.assert200(r1.status_code)

    def test_file_property(self):

        file_pro = {"file_name": "test.txt",
                    "other_property1": "test_property1"
                    }
        rt, s = self.parse_response(
            self.test_client.post('api/v1/file/info',
                                  data=json.dumps(file_pro),
                                  headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        r1 = self.test_client.get(
            'api/v1/file/info?filename=test.txt', headers=self.auth
        )
        self.assert200(r1.status_code)

    def test_download_file(self):
        r1 = self.test_client.get(
            'api/v1/file/downloader?filename=test_big_file.txt', headers=self.auth
        )
        self.assert200(r1.status_code)

    def test_delete_file(self):
        r, s = self.parse_response(
            self.test_client.post('api/v1/file/delete',
                                  data=json.dumps({
                                      "file_name": "test.txt"
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)

        r1 = self.test_client.get(
            'api/v1/file/info?filename=test.txt', headers=self.auth
        )
        self.assert200(s)


if __name__ == '__main__':
    unittest.main()

import json
import os
import unittest
import tempfile
import sqlite3
from io import StringIO, BytesIO

from flask import session, request, make_response, render_template, appcontext_pushed, g
from contextlib import closing, contextmanager
from hive import create_app


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
        self.auth = None
        self.upload_auth = None

    def init_all_auth(self):
        self.register()
        token = self.login()
        self.init_auth(token)
        self.init_upload_auth(token)

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

    def register(self):
        r, s = self.parse_response(
            self.test_client.post('/api/v1/did/register',
                                  data=json.dumps({
                                      "did": "iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk",
                                      "password": "1223456"
                                  }),
                                  headers=self.json_header)
        )

    def login(self):
        r, s = self.parse_response(
            self.test_client.post('/api/v1/did/login',
                                  data=json.dumps({
                                      "did": "iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk",
                                      "password": "1223456"
                                  }),
                                  headers=self.json_header)
        )
        return r["token"]

    def init_auth(self, token):
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

    def init_upload_auth(self, token):
        self.upload_auth = [
            ("Authorization", "token " + token),
            self.upload_file_content_type,
        ]

    def test_upload_file(self):
        if self.upload_auth is None:
            self.init_all_auth()

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

    def test_list_file(self):
        if self.auth is None:
            self.init_all_auth()
        r1 = self.test_client.get(
            'api/v1/file/list', headers=self.auth
        )
        self.assert200(r1.status_code)

    def test_download_file(self):
        if self.auth is None:
            self.init_all_auth()
        r1 = self.test_client.get(
            'api/v1/file/downloader?filename=test.txt', headers=self.auth
        )
        self.assert200(r1.status_code)

    def test_delete_file(self):
        if self.auth is None:
            self.init_all_auth()
        r, s = self.parse_response(
            self.test_client.post('api/v1/file/delete',
                                  data=json.dumps({
                                      "file_name": "test.txt"
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    if __name__ == '__main__':
        unittest.main()

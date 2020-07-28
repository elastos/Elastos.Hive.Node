import json
import os
import unittest
import tempfile
import sqlite3
from flask import session, request, make_response, render_template, appcontext_pushed, g
from contextlib import closing, contextmanager
from hive import create_app

token = "1b30b24e-cfd9-11ea-8157-f45c898fba57"


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HiveSyncTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveSyncTestCase, self).__init__(methodName)

    def setUp(self):
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")

        self.json_header = [
            self.content_type,
        ]
        self.auth = None
        self.init_auth()

    def init_auth(self):
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

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

    def test_echo(self):
        r, s = self.parse_response(
            self.test_client.post('/api/v1/echo',
                                  data=json.dumps({"key": "value"}),
                                  headers=self.json_header)
        )
        self.assert200(s)
        print("** r:" + str(r))

    def test_setup_google_drive(self):
        google_auth_token = '{"token": "ya29.a0AfH6SMAVaP_gNAdbF25L5hktoPRdV8mBkcra6UaneG2w7ZYSusXevycqvhUrGrQ_FpsBPYYvxq2Sdx13zEwG1-m8I-pSFV05UY52X6wNnVlpxG7hsyBteEdUiiQPDT52zbK5ceQZ4-cpfXSlrplsQ8kZvPYC5nR1yks", "refresh_token": "1//06llFKBe-DBkRCgYIARAAGAYSNwF-L9Irfka2E6GP-J9gKBZN5AQS3z19vHOtjHq67p2ezCsJiVUZO-jKMSDKLgkiGfXgmBYimwc", "token_uri": "https://oauth2.googleapis.com/token", "client_id": "24235223939-7335upec07n0c3qc7mnd19jqoeglrg3t.apps.googleusercontent.com", "client_secret": "-7Ls5u1NpRe77Dy6VkL5W4pe", "scopes": ["https://www.googleapis.com/auth/drive.file"], "expiry": "2020-06-24 03:10:49.960710"}'
        r, s = self.parse_response(
            self.test_client.post('/api/v1/sync/setup/google_drive',
                                  data=google_auth_token,
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")


if __name__ == '__main__':
    unittest.main()

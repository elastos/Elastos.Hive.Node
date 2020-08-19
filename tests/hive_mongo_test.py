import json
import time
import unittest
from flask import appcontext_pushed, g
from contextlib import contextmanager
from hive import create_app
from tests import test_common


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HiveMongoDbTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveMongoDbTestCase, self).__init__(methodName)

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
        token = test_common.get_auth_token(self)
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

    def test_a_echo(self):
        r, s = self.parse_response(
            self.test_client.post('/api/v1/echo',
                                  data=json.dumps({"key": "value"}),
                                  headers=self.json_header)
        )
        self.assert200(s)
        print("** r:" + str(r))

    def test_b_create_collection(self):
        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/create_collection',
                                  data=json.dumps(
                                      {
                                          "collection": "works",
                                          "schema": {"title": {"type": "string"}, "author": {"type": "string"}}
                                      }
                                  ),
                                  headers=self.auth)
        )
        # Wait for collection to be created before continuing
        time.sleep(2)
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_c_add_collection_data(self):
        # r, s = self.parse_response(
        #     self.test_client.post('/api/v1/db/create_collection',
        #                           data=json.dumps(
        #                               {
        #                                   "collection": "works",
        #                                   "schema": {"title": {"type": "string"}, "author": {"type": "string"}}
        #                               }
        #                           ),
        #                           headers=self.auth)
        # )
        # self.assert200(s)

        r, s = self.parse_response(
            self.test_client.post('/api/v1/db/col/works',
                                  data=json.dumps(
                                      {"author": "john doe2", "title": "Eve for Dummies2"}
                                  ),
                                  headers=self.auth)
        )
        self.assert201(s)

        r1 = self.test_client.get(
            '/api/v1/db/col/works', headers=self.auth
        )
        self.assert200(r1.status_code)


if __name__ == '__main__':
    unittest.main()

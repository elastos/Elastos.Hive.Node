import json
import os
import unittest
import tempfile
import sqlite3
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

    def setUp(self):
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")

        self.json_header = [
            self.content_type,
        ]
        self.auth = None

    def init_auth(self, token):
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

    def test_register(self):
        r, s = self.parse_response(
            self.test_client.post('/api/v1/did/register',
                                  data=json.dumps({
                                      "did": "iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk",
                                      "password": "1223456"
                                  }),
                                  headers=self.json_header)
        )
        self.assert200(s)
        self.assertEqual({
            "_status": "OK"
        }, r)

    def test_login(self):
        r, s = self.parse_response(
            self.test_client.post('/api/v1/did/login',
                                  data=json.dumps({
                                      "did": "iUWjzkS4Di75yCXiKJqxrHYxQdBcS2NaPk",
                                      "password": "1223456"
                                  }),
                                  headers=self.json_header)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        self.init_auth(r["token"])

    def test_create_collection(self):
        if self.auth is None:
            self.test_login()

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
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def test_add_collection_data(self):
        self.test_create_collection()
        r, s = self.parse_response(
            self.test_client.post('api/v1/db/col/works',
                                  data=json.dumps(
                                      {"author": "john doe2", "title": "Eve for Dummies2"}
                                  ),
                                  headers=self.auth)
        )
        self.assert201(s)

        r1 = self.test_client.get(
            'api/v1/db/col/works', headers=self.auth
        )
        self.assert200(r1.status_code)

    if __name__ == '__main__':
        unittest.main()

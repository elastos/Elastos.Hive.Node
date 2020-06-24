import json
import os
import unittest
import tempfile
import sqlite3
from flask import session, request, make_response, render_template, appcontext_pushed, g
from contextlib import closing, contextmanager
from hive import create_app
from hive.util.did.ela_did_util import did_sign, init_test_did_store, did_verify

did_str = "did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6quumnym1"
auth_key_name = "key2"
storepass = "123456"


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

    def test_auth(self):
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/did/auth',
                                  data=json.dumps({
                                      "iss": did_str
                                  }),
                                  headers=self.json_header)
        )
        self.assert200(s)

        subject = rt["subject"]
        iss = rt["iss"]
        nonce = rt["nonce"]
        callback = rt["callback"]

        store, doc = init_test_did_store()
        sig = did_sign(did_str, doc, storepass, auth_key_name, nonce)
        param = dict()
        param["subject"] = subject
        param["realm"] = iss
        param["iss"] = did_str
        param["nonce"] = nonce
        param["key_name"] = auth_key_name
        param["sig"] = str(sig, encoding="utf-8")

        r, s = self.parse_response(
            self.test_client.post(callback,
                                  data=json.dumps(param),
                                  headers=self.json_header)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        print("token:" + r["token"])


if __name__ == '__main__':
    unittest.main()

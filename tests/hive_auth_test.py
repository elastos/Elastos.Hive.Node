import json
import unittest
from flask import appcontext_pushed, g
from contextlib import contextmanager
from hive import create_app
import test_common


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HiveAuthTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveAuthTestCase, self).__init__(methodName)

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
        token = test_common.get_auth_token(self)
        print("token:" + token)


if __name__ == '__main__':
    unittest.main()

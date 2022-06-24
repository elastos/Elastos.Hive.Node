import json
import unittest
import flask_unittest

from src import create_app
from hive.util.constants import HIVE_MODE_TEST
from src.utils.executor import executor
from tests import test_log
from tests_v1 import test_common


class HiveAuthTestCase(flask_unittest.ClientTestCase):
    app = create_app(mode=HIVE_MODE_TEST)

    @classmethod
    def setUpClass(cls):
        test_log("HiveAuthTestCase: Setting up HiveAuthTestCase\n")

    @classmethod
    def tearDownClass(cls):
        # wait flask-executor to finish
        executor.shutdown()
        test_log("HiveAuthTestCase: \n\nShutting down HiveAuthTestCase")

    def setUp(self, client):
        test_log("HiveAuthTestCase: \n")
        self.app.config['TESTING'] = True
        self.content_type = ("Content-Type", "application/json")
        self.json_header = [self.content_type, ]

    def tearDown(self, client):
        test_log("HiveAuthTestCase: \n")

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

    def test01_echo(self, client):
        test_log("HiveAuthTestCase: \nRunning test_a_echo")
        r, s = self.parse_response(
            client.post('/api/v1/echo', data=json.dumps({"key": "value"}), headers=self.json_header)
        )
        test_log(f"HiveAuthTestCase: \nr:{r}")
        self.assert200(s)

    def test02_access_token(self, client):
        test_log("HiveAuthTestCase: \nRunning test_c_auth")
        test_common.get_tokens(self, client)


if __name__ == '__main__':
    unittest.main()

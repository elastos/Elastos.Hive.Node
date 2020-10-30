import json
import sys
import time
import unittest
import logging
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


class HiveManageTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveManageTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HiveManageTestCase").debug("Setting up HiveManageTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HiveManageTestCase").debug("\n\nShutting down HiveManageTestCase")
        logger.removeHandler(cls.stream_handler)

    def setUp(self):
        logging.getLogger("HiveManageTestCase").info("\n")
        self.app = create_app(True)
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")

        self.json_header = [
            self.content_type,
        ]
        test_common.setup_test_auth_token()
        self.init_auth()
        self.did = test_common.get_auth_did()
        self.app_id = test_common.get_auth_app_did()

    def init_auth(self):
        token = test_common.get_auth_token()
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

    def tearDown(self):
        test_common.delete_test_auth_token()
        logging.getLogger("HiveManageTestCase").info("\n")

    def init_db(self):
        pass

    def parse_response(self, r):
        try:
            logging.getLogger("HiveManageTestCase").debug("\nret:" + str(r.get_data()))
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def assert200(self, status):
        self.assertEqual(status, 200)

    def assert201(self, status):
        self.assertEqual(status, 201)

    def test_1_get_info(self):
        logging.getLogger("HiveManageTestCase").debug("\nRunning test_1_get_info")
        r, s = self.parse_response(
            self.test_client.get('/api/v1/hive/version', headers=self.json_header)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        r, s = self.parse_response(
            self.test_client.get('/api/v1/hive/commithash', headers=self.json_header)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")


if __name__ == '__main__':
    unittest.main()

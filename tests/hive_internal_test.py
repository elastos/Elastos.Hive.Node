import json
import logging
import sys

import requests
import unittest
from flask_testing import LiveServerTestCase

unittest.TestSuite

import hive
from hive import HIVE_MODE_TEST
from tests import test_common

logger = logging.getLogger()
logger.level = logging.DEBUG

class MyTest(LiveServerTestCase):
    def assert200(self, status):
        self.assertEqual(status, 200)

    def create_app(self):
        app = hive.create_app()
        app.config['TESTING'] = True
        # Default port is 5000
        app.config['LIVESERVER_PORT'] =8493
        # Default timeout is 5 seconds
        app.config['LIVESERVER_TIMEOUT'] = 10
        return app

    def init_vault_backup_service(self, host):
        param = {}
        token = test_common.get_auth_token()

        r = requests.post(host + '/api/v1/service/vault_backup/create',
                          json=param,
                          headers={"Content-Type": "application/json", "Authorization": "token " + token})
        self.assert200(r.status_code)

    def set_Up(self):
        logging.getLogger("HiveBackupTestCase").info("\n")

        self.app = hive.create_app(mode=HIVE_MODE_TEST)
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
        test_common.setup_test_vault(self.did)

    def init_auth(self):
        token = test_common.get_auth_token()
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

    def test_server_is_up_and_running(self):
        print(self.get_server_url())
        self.init_vault_backup_service("http://127.0.0.1:8493")
        self.set_Up()
        self.test_echo()

    def parse_response(self, r):
        try:
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def test_echo(self):
        logging.getLogger("HiveBackupTestCase").debug("\nRunning test_a_echo")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/echo',
                                  data=json.dumps({"key": "value"}),
                                  headers=self.json_header)
        )
        self.assert200(s)
        logging.getLogger("HiveBackupTestCase").debug("** r:" + str(r))



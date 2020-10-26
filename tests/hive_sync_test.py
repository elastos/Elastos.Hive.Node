import json
import shutil
import sys
import unittest
import logging
from time import time

from flask import appcontext_pushed, g
from contextlib import contextmanager

from hive.util.did_sync import get_did_sync_info, update_did_sync_info, DATA_SYNC_STATE_RUNNING, DATA_SYNC_MSG_SUCCESS, \
    add_did_sync_info
from hive.util.constants import DID
from hive import create_app
from tests import test_common
from hive.main.hive_sync import HiveSync

logger = logging.getLogger()
logger.level = logging.DEBUG


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


class HiveSyncTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveSyncTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HiveSyncTestCase").debug("Setting up HiveSyncTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HiveSyncTestCase").debug("\n\nShutting down HiveSyncTestCase")
        logger.removeHandler(cls.stream_handler)

    def setUp(self):
        logging.getLogger("HiveSyncTestCase").info("\n")
        self.app = create_app(True)
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")

        self.json_header = [
            self.content_type,
        ]
        test_common.setup_test_auth_token()
        self.init_auth()

    def init_auth(self):
        token = test_common.get_auth_token()
        self.auth = [
            ("Authorization", "token " + token),
            self.content_type,
        ]

    def tearDown(self):
        test_common.delete_test_auth_token()
        logging.getLogger("HiveSyncTestCase").info("\n")

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
        logging.getLogger("HiveSyncTestCase").debug("\nRunning test_a_echo")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/echo',
                                  data=json.dumps({"key": "value"}),
                                  headers=self.json_header)
        )
        self.assert200(s)
        logging.getLogger("HiveSyncTestCase").debug("** r:" + str(r))

    def test_b_init_sync(self):
        logging.getLogger("HiveSyncTestCase").debug("\nRunning test_b_init_sync")
        did = "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM"
        drive = HiveSync.gene_did_google_drive_name(did)
        add_did_sync_info(did, time(), drive)
        did_folder = HiveSync.get_did_sync_path(did)
        if did_folder.exists():
            shutil.rmtree(did_folder)
        info = get_did_sync_info(did)
        HiveSync.sync_did_data(info[DID])

    def test_c_sync(self):
        logging.getLogger("HiveSyncTestCase").debug("\nRunning test_c_sync")
        did = "did:elastos:ijUnD4KeRpeBUFmcEDCbhxMTJRzUYCQCZM"
        drive = HiveSync.gene_did_google_drive_name(did)
        update_did_sync_info(did, DATA_SYNC_STATE_RUNNING, DATA_SYNC_MSG_SUCCESS, time(), drive)
        info = get_did_sync_info(did)
        HiveSync.sync_did_data(info[DID])

    def test_d_setup_google_drive(self):
        logging.getLogger("HiveSyncTestCase").debug("\nRunning test_d_setup_google_drive")
        google_auth_token = '{"token": "ya29.a0AfH6SMDknoTvi2dnt5HLqit4W6XbPmW-zNmPc9B_oiqLowJT1' \
                            '-QpFSTWKbhtbbArZqvFMgWAM4FpxGh-aNZoA93V3kMWjfFLgz1hGE65GXF' \
                            '-WvN_gmvfQZ8sbAtVrcABrJPTqVA_MCOBEKKgCXXbkZnwxzJDjxbs8Dk", "refresh_token": ' \
                            '"1//06d2r9StwWRzZCgYIARAAGAYSNwF-L9IrbrCxgQk5mDvTVNeNT' \
                            '-M7DUtMjR0XuvQx0VEfkSUwzN1k8fwW7V_ZjCJFCCpj9XSJzqU", "token_uri": ' \
                            '"https://oauth2.googleapis.com/token", "client_id": ' \
                            '"24235223939-guh47dijl0f0idm7h04bd44ulfcodta0.apps.googleusercontent.com", ' \
                            '"client_secret": "mqaI40MlghlNkfaFtDBzvpGg", "scopes": [' \
                            '"https://www.googleapis.com/auth/drive"], "expiry": "2020-07-31T09:26:14.816501+08:00"} '
        r, s = self.parse_response(
            self.test_client.post('/api/v1/sync/setup/google_drive',
                                  data=google_auth_token,
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")


if __name__ == '__main__':
    unittest.main()

import json
import shutil
import sys
import unittest
import logging
from time import time

from flask import appcontext_pushed, g
from contextlib import contextmanager

from hive.main.hive_backup import HiveBackup
from hive.util.constants import DID, HIVE_MODE_TEST
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


class HiveBackupTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveBackupTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HiveBackupTestCase").debug("Setting up HiveBackupTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HiveBackupTestCase").debug("\n\nShutting down HiveBackupTestCase")
        logger.removeHandler(cls.stream_handler)

    def setUp(self):
        logging.getLogger("HiveBackupTestCase").info("\n")
        self.app = create_app(mode=HIVE_MODE_TEST)
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

    def tearDown(self):
        test_common.delete_test_auth_token()
        logging.getLogger("HiveBackupTestCase").info("\n")

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
        logging.getLogger("HiveBackupTestCase").debug("\nRunning test_a_echo")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/echo',
                                  data=json.dumps({"key": "value"}),
                                  headers=self.json_header)
        )
        self.assert200(s)
        logging.getLogger("HiveBackupTestCase").debug("** r:" + str(r))

    def test_1_save_to_google_drive_call(self):
        logging.getLogger("HiveBackupTestCase").debug("\nRunning test_1_save_to_google_drive_call")
        google_auth_token = '''{ "token": "ya29.A0AfH6SMAuwGipoRVMVnvon_C_qqMhzpK53QzDQ8rapZavP_JXa8ASFecIKcKsy91oek8UvjbXfLMB9rlVG3Wj3X4e6drbNGuJjq97U8Lo6uwxwTpcmeybSl0wkQihwXZJlc3fKY31tvsT55vUbSSWwugPETCPZAFs2Oo_MURWbtY", "refresh_token": "1//06-2759fIGiJdCgYIARAAGAYSNwF-L9Irf7R8nimVqT2UieEcO5wtZMk1uNLxyBk_jB2WCPHDY7rhdTV_0WvHp5K09BWy1lUZnng", "token_uri": "https://oauth2.googleapis.com/token", "client_id": "24235223939-guh47dijl0f0idm7h04bd44ulfcodta0.apps.googleusercontent.com", "client_secret": "mqaI40MlghlNkfaFtDBzvpGg", "scopes": ["https://www.googleapis.com/auth/drive"], "expiry": "2020-11-17T05:14:10Z"}'''
        r, s = self.parse_response(
            self.test_client.post('/api/v1/backup/save/to/google_drive',
                                  data=google_auth_token,
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        drive_name = HiveBackup.gene_did_google_drive_name(self.did)
        HiveBackup.save_vault_data(self.did, drive_name)

    def test_2_resotre_from_google_drive(self):
        logging.getLogger("HiveBackupTestCase").debug("\nRunning test_2_resotre_from_google_drive")
        google_auth_token = '''{"token": "ya29.A0AfH6SMAuwGipoRVMVnvon_C_qqMhzpK53QzDQ8rapZavP_JXa8ASFecIKcKsy91oek8UvjbXfLMB9rlVG3Wj3X4e6drbNGuJjq97U8Lo6uwxwTpcmeybSl0wkQihwXZJlc3fKY31tvsT55vUbSSWwugPETCPZAFs2Oo_MURWbtY", "refresh_token": "1//06-2759fIGiJdCgYIARAAGAYSNwF-L9Irf7R8nimVqT2UieEcO5wtZMk1uNLxyBk_jB2WCPHDY7rhdTV_0WvHp5K09BWy1lUZnng", "token_uri": "https://oauth2.googleapis.com/token", "client_id": "24235223939-guh47dijl0f0idm7h04bd44ulfcodta0.apps.googleusercontent.com", "client_secret": "mqaI40MlghlNkfaFtDBzvpGg", "scopes": ["https://www.googleapis.com/auth/drive"], "expiry": "2020-11-17T05:14:10Z"}'''
        r, s = self.parse_response(
            self.test_client.post('/api/v1/backup/restore/from/google_drive',
                                  data=google_auth_token,
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        drive_name = HiveBackup.gene_did_google_drive_name(self.did)
        HiveBackup.restore_vault_data(self.did, drive_name)


if __name__ == '__main__':
    unittest.main()

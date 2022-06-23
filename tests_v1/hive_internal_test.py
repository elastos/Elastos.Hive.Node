import json
import logging
import multiprocessing

import requests
import unittest
from flask_testing import LiveServerTestCase

from hive.util.constants import HIVE_MODE_TEST
from src import create_app
from tests_v1.hive_auth_test import DIDApp, DApp
from src.utils.did.eladid import ffi, lib

from tests_v1.test_common import prepare_vault_data, copy_to_backup_data

unittest.TestSuite

# from hive import HIVE_MODE_TEST
from tests_v1 import test_common

from sys import platform

logger = logging.getLogger()
logger.level = logging.DEBUG


PORT = 5002

if platform == "darwin":
    # mac os
    multiprocessing.set_start_method("fork")


def disabled(f):
    def _decorator(self):
        print(f.__name__ + ' has been disabled')
    return _decorator


class HiveInternalTest(LiveServerTestCase):

    def assert200(self, status):
        self.assertEqual(status, 200)

    def parse_response(self, r):
        try:
            v = json.loads(r.get_data())
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def create_app(self):
        app = create_app(mode=HIVE_MODE_TEST, hive_config='.env.deprecated_v1')
        app.config['TESTING'] = True
        # Default port is 5000
        app.config['LIVESERVER_PORT'] = PORT
        # Default timeout is 5 seconds
        app.config['LIVESERVER_TIMEOUT'] = 10
        return app

    def setUp(self):
        logging.getLogger("HiveBackupTestCase").info("\n")

        self.app = create_app(mode=HIVE_MODE_TEST, hive_config='.env')
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
        self.upload_auth = [
            ("Authorization", "token " + token),
        ]

    def init_vault_backup_service(self, host):
        param = {}
        token = test_common.get_auth_token()

        r = requests.post(host + '/api/v1/service/vault_backup/create',
                          json=param,
                          headers={"Content-Type": "application/json", "Authorization": "token " + token})
        self.assert200(r.status_code)

    def save_to_hive_node(self, vc_json, did):
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/backup/save_to_node',
                                  data=json.dumps({
                                      "backup_credential": vc_json,
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)
        # info = HiveBackup.save_vault_data(did)
        # self.assertIsNotNone(info)

    def restore_from_hive_node(self, vc_json, did):
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/backup/restore_from_node',
                                  data=json.dumps({
                                      "backup_credential": vc_json,
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)
        # info = HiveBackup.restore_vault_data(did)
        # self.assertIsNotNone(info)

    @disabled
    def test_1_save_restore_hive_node(self):
        host = self.get_server_url()
        self.init_vault_backup_service(host)
        prepare_vault_data(self)
        copy_to_backup_data(self)

        user_did = DIDApp("didapp", "clever bless future fuel obvious black subject cake art pyramid member clump")
        app_did = DApp("testapp", test_common.app_id,
                       "amount material swim purse swallow gate pride series cannon patient dentist person")
        token, hive_did = test_common.test_auth_common(self, user_did, app_did)

        # backup_auth
        vc = user_did.issue_backup_auth(hive_did, host, hive_did)
        vc_json = ffi.string(lib.Credential_ToString(vc, True)).decode()

        did = user_did.get_did_string()
        self.save_to_hive_node(vc_json, did)
        self.restore_from_hive_node(vc_json, did)

import json
import os
import shutil
import signal
import subprocess
import sys
import unittest
import logging
import time
from pathlib import Path

import requests
from flask import appcontext_pushed, g
from contextlib import contextmanager
from hive.util.did.eladid import ffi, lib
from pymongo import MongoClient

from hive.main import view
from hive.main.hive_backup import HiveBackup
from hive.settings import env_dist
from hive.util.constants import DID, HIVE_MODE_TEST, DID_INFO_DB_NAME, VAULT_ORDER_COL, VAULT_BACKUP_SERVICE_COL, \
    INTER_BACKUP_FTP_START_URL, INTER_BACKUP_FTP_END_URL, VAULT_BACKUP_SERVICE_DATA, INTER_BACKUP_SAVE_URL
from hive import create_app
from hive.util.payment.vault_backup_service_manage import setup_vault_backup_service, update_vault_backup_service_item
from hive.util.payment.vault_order import check_wait_order_tx_job
from hive.util.payment.vault_service_manage import delete_user_vault, setup_vault_service
from tests import test_common
from hive import settings
from tests.hive_auth_test import DIDApp, DApp

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
        google_auth_token = '''{
            "token": "ya29.A0AfH6SMBB9WMZvjyxF2n7lfh4NHKaHdjd7ESfJOvAQctNJqydbM6PDlfV2A4oQT_-aINM_n0qmNPuns22a_Ufwp9C1cyzrjINZ4V1l-HAwR7uH8-BxY4QsKRi0gV0T50JyKm8Bmk5uHUGsZQfJfbMoYcCGZFOdAxuvf7Ue14LFgc",
            "refresh_token": "1//06gWBqRQQMerxCgYIARAAGAYSNwF-L9IrS5H5ETnTrxfgyMk3b9O1K1pclZducb21cqhwc2rmsLVwUHZCjXM0R4sEyAhXlM6xvPo",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "24235223939-guh47dijl0f0idm7h04bd44ulfcodta0.apps.googleusercontent.com",
            "client_secret": "mqaI40MlghlNkfaFtDBzvpGg", "scopes": ["https://www.googleapis.com/auth/drive"],
            "expiry": "2020-11-18T04:13:37Z"}'''
        r, s = self.parse_response(
            self.test_client.post('/api/v1/backup/save/to/google_drive',
                                  data=google_auth_token,
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        drive_name = HiveBackup.gene_did_google_drive_name(self.did)
        HiveBackup.save_vault_data(self.did)

    def test_2_resotre_from_google_drive(self):
        logging.getLogger("HiveBackupTestCase").debug("\nRunning test_2_resotre_from_google_drive")
        google_auth_token = '''{
            "token": "ya29.A0AfH6SMBB9WMZvjyxF2n7lfh4NHKaHdjd7ESfJOvAQctNJqydbM6PDlfV2A4oQT_-aINM_n0qmNPuns22a_Ufwp9C1cyzrjINZ4V1l-HAwR7uH8-BxY4QsKRi0gV0T50JyKm8Bmk5uHUGsZQfJfbMoYcCGZFOdAxuvf7Ue14LFgc",
            "refresh_token": "1//06gWBqRQQMerxCgYIARAAGAYSNwF-L9IrS5H5ETnTrxfgyMk3b9O1K1pclZducb21cqhwc2rmsLVwUHZCjXM0R4sEyAhXlM6xvPo",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "24235223939-guh47dijl0f0idm7h04bd44ulfcodta0.apps.googleusercontent.com",
            "client_secret": "mqaI40MlghlNkfaFtDBzvpGg", "scopes": ["https://www.googleapis.com/auth/drive"],
            "expiry": "2020-11-18T04:13:37Z"}'''
        r, s = self.parse_response(
            self.test_client.post('/api/v1/backup/restore/from/google_drive',
                                  data=google_auth_token,
                                  headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")
        drive_name = HiveBackup.gene_did_google_drive_name(self.did)
        HiveBackup.restore_vault_data(self.did)

    def init_vault_backup_service(self, host):
        param = {}
        token = test_common.get_auth_token()

        r = requests.post(host + '/api/v1/service/vault_backup/create',
                          json=param,
                          headers={"Content-Type": "application/json", "Authorization": "token " + token})
        self.assert200(r.status_code)

    def test_internal_ftp(self):
        backup_token = "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCIsICJraWQiOiAiZGlkOmVsYXN0b3M6aWpVbkQ0S2VScGVCVUZtY0VEQ2JoeE1USlJ6VVlDUUNaTSNwcmltYXJ5In0.eyJpc3MiOiJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwic3ViIjoiQmFja3VwVG9rZW4iLCJhdWQiOiJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwiZXhwIjoxNjEyMDAxODI2LCJwcm9wcyI6IntcInNvdXJjZURJRFwiOiBcImRpZDplbGFzdG9zOmlqVW5ENEtlUnBlQlVGbWNFRENiaHhNVEpSelVZQ1FDWk1cIiwgXCJ0YXJnZXRESURcIjogXCJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNXCIsIFwidGFyZ2V0SG9zdFwiOiBcImh0dHA6Ly8wLjAuMC4wOjUwMDBcIiwgXCJ1c2VyRGlkXCI6IFwiZGlkOmVsYXN0b3M6aWo4a3JBVlJKaXRaS0ptY0N1Zm9MSFFqcTdNZWYzWmpUTlwiLCBcIm5vbmNlXCI6IFwiNTU2OGJkOGMtNGI1MS0xMWViLWJiMDktYWNkZTQ4MDAxMTIyXCJ9In0.Kx74LxqmvQK4Vv3iJORjS6rQAZq0Yk6m7kxRQ2kVb4I0LBgk4j9GtWdHT2GBtknsJ1Qdk8ItVAfLagBozyo3Cg"

        param = {
            "backup_did": self.did
        }

        r, s = self.parse_response(
            self.test_client.post(INTER_BACKUP_FTP_START_URL,
                                  data=json.dumps(param),
                                  headers=[("Content-Type", "application/json"),
                                           ("Authorization", "token " + backup_token)]
                                  )
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

        r, s = self.parse_response(
            self.test_client.post(INTER_BACKUP_FTP_END_URL,
                                  data=json.dumps(param),
                                  headers=[("Content-Type", "application/json"),
                                           ("Authorization", "token " + backup_token)]
                                  )
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")

    def save_to_hive_node(self, vc_json, did):
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/backup/save/to/node',
                                  data=json.dumps({
                                      "backup_credential": vc_json,
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)
        info = HiveBackup.save_vault_data(did)
        self.assertIsNotNone(info)

    def restore_from_hive_node(self, vc_json, did):
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/backup/restore/from/node',
                                  data=json.dumps({
                                      "backup_credential": vc_json,
                                  }),
                                  headers=self.auth)
        )
        self.assert200(s)
        info = HiveBackup.restore_vault_data(did)
        self.assertIsNotNone(info)

    # def test_3_save_restore_hive_node(self):
    #     host = "http://0.0.0.0:5000"
    #     if "HIVE_NODE_HOME" in env_dist:
    #         work_dir = Path(env_dist["HIVE_NODE_HOME"]).resolve()
    #     else:
    #         work_dir = Path("./..").resolve()
    #
    #     if not (work_dir/"test_hive_data/data").exists():
    #         shutil.copytree((work_dir/"data").as_posix(), (work_dir/"test_hive_data/data").as_posix())
    #
    #     child = subprocess.Popen("./run_other_node.sh", cwd=work_dir.as_posix(),
    #                              stdout=subprocess.PIPE, shell=True,
    #                              preexec_fn=os.setsid)
    #     try:
    #         time.sleep(5)
    #         self.init_vault_backup_service(host)
    #
    #         user_did = DIDApp("didapp", "clever bless future fuel obvious black subject cake art pyramid member clump")
    #         app_did = DApp("testapp", test_common.app_id,
    #                        "amount material swim purse swallow gate pride series cannon patient dentist person")
    #         token, hive_did = test_common.test_auth_common(self, user_did, app_did)
    #
    #         # backup_auth
    #         vc = user_did.issue_backup_auth(hive_did, host, hive_did)
    #         vc_json = ffi.string(lib.Credential_ToString(vc, True)).decode()
    #
    #         did = user_did.get_did_string()
    #         self.save_to_hive_node(vc_json, did)
    #         delete_user_vault(did)
    #         self.restore_from_hive_node(vc_json, did)
    #
    #     finally:
    #         child.stdout.close()
    #         os.killpg(os.getpgid(child.pid), signal.SIGTERM)
    #         subprocess.call("docker container stop hive-test-mongo", shell=True)
    #         pass

    def prepare_active_backup_hive_node_db(self):
        setup_vault_backup_service(self.did, 500, -1)
        setup_vault_service(self.did, 500, -1)
        app_id_list = ["appid", "appid2"]
        param = {"app_id_list": app_id_list}
        rt, s = self.parse_response(
            self.test_client.post(INTER_BACKUP_SAVE_URL,
                                  data=json.dumps(param),
                                  headers=self.auth)
        )
        self.assert200(s)

    def active_backup_hive_node(self):
        param = {}
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/backup/active/to/vault',
                                  data=json.dumps(param),
                                  headers=self.auth)
        )
        self.assert200(s)

    def test_4_active_backup_hive_node(self):
        self.prepare_active_backup_hive_node_db()
        self.active_backup_hive_node()


if __name__ == '__main__':
    unittest.main()

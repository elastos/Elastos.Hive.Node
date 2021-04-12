import json
import os
import shutil
import signal
import subprocess
import sys
import unittest
import logging
import time
from io import BytesIO
from pathlib import Path
import pickle

import requests
from flask import appcontext_pushed, g
from contextlib import contextmanager
from pymongo import MongoClient

from hive.main import view
from hive.main.hive_backup import HiveBackup
from hive.main.hive_internal import HiveInternal
from hive.util.common import gene_temp_file_name
from hive.util.constants import DID, HIVE_MODE_TEST, DID_INFO_DB_NAME, VAULT_ORDER_COL, VAULT_BACKUP_SERVICE_COL, \
    INTER_BACKUP_SAVE_FINISH_URL, INTER_BACKUP_RESTORE_FINISH_URL, APP_ID, INTER_BACKUP_PATCH_HASH_URL, \
    INTER_BACKUP_FILE_URL, INTER_BACKUP_PATCH_DELTA_URL, CHUNK_SIZE
from hive import create_app
from hive.util.did_info import get_all_did_info_by_did
from hive.util.payment.vault_backup_service_manage import setup_vault_backup_service, update_vault_backup_service_item
from hive.util.payment.vault_order import check_wait_order_tx_job
from hive.util.payment.vault_service_manage import delete_user_vault, setup_vault_service, get_vault_path
from hive.util.pyrsync import rsyncdelta, rsyncdelta
from tests import test_common
from hive import settings
from tests.hive_auth_test import DIDApp, DApp
from tests.test_common import upsert_collection, create_upload_file, prepare_vault_data, copy_to_backup_data, \
    move_to_backup_data

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
        self.upload_auth = [
            ("Authorization", "token " + token),
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
            self.test_client.post('/api/v1/backup/save_to_google_drive',
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
            self.test_client.post('/api/v1/backup/restore_from_google_drive',
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


    def prepare_active_backup_hive_node(self):
        setup_vault_backup_service(self.did, 500, -1)
        setup_vault_service(self.did, 500, -1)
        prepare_vault_data(self)
        HiveBackup.export_mongo_db_did(self.did)

        app_id_list = list()
        did_info_list = get_all_did_info_by_did(self.did)
        for did_info in did_info_list:
            app_id_list.append(did_info[APP_ID])

        vault_path = get_vault_path(self.did)
        checksum_list = HiveBackup.get_file_checksum_list(vault_path)
        move_to_backup_data(self)
        param = {"app_id_list": app_id_list,
                 "checksum_list": checksum_list
                 }

        rt, s = self.parse_response(
            self.test_client.post(INTER_BACKUP_SAVE_FINISH_URL,
                                  data=json.dumps(param),
                                  headers=self.auth)
        )
        self.assert200(s)

    def active_backup_hive_node(self):
        param = {}
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/backup/activate_to_vault',
                                  data=json.dumps(param),
                                  headers=self.auth)
        )
        self.assert200(s)

    def init_vault_service(self):
        param = {}
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/service/vault/create',
                                  data=json.dumps(param),
                                  headers=self.auth)
        )

        self.assert200(s)


    def test_5_get_backup_state(self):
        r, s = self.parse_response(
            self.test_client.get('api/v1/backup/state', headers=self.auth)
        )
        self.assert200(s)
        self.assertEqual(r["_status"], "OK")


    def delete_backup_file(self, file_name):
        param = {
            'file_name': file_name
        }
        r = self.test_client.post(INTER_BACKUP_FILE_URL,
                                  json=param,
                                  headers=self.auth)

    def put_backup_file(self, file_name, data):
        temp = BytesIO()
        temp.write(data.encode(encoding="utf-8"))
        temp.seek(0)
        temp.name = 'temp.txt'

        put_file_url = INTER_BACKUP_FILE_URL + "?file=" + file_name
        r2, s = self.parse_response(
            self.test_client.put(put_file_url,
                                 data=temp,
                                 headers=self.upload_auth)
        )
        self.assert200(s)
        self.assertEqual(r2["_status"], "OK")

    def get_backup_file(self, file_name):
        get_file_url = INTER_BACKUP_FILE_URL + "?file=" + file_name
        r = self.test_client.get(get_file_url, headers=self.upload_auth)
        self.assert200(r.status_code)
        return r.get_data()

    def get_backup_file_hash(self, file_name):
        get_file_hash_url = INTER_BACKUP_PATCH_HASH_URL + "?file=" + file_name
        r = self.test_client.get(get_file_hash_url, headers=self.upload_auth)
        self.assert200(r.status_code)
        hashes = list()
        lines = r.data.split(b'\n')
        print(lines)
        for i in lines:
            if not i:
                continue
            l = i.split(b',')
            h = (int(l[0]), l[1].decode("utf-8"))
            hashes.append(h)
        return hashes

    def post_backup_file_delta(self, file_name, delta):
        post_delta_url = INTER_BACKUP_PATCH_DELTA_URL + "?file=" + file_name
        r = self.test_client.post(post_delta_url,
                                  data=delta,
                                  headers=self.upload_auth)
        self.assert200(r.status_code)

    def test_patch_remote_file(self):
        file_name = "test_patch.txt"
        self.delete_backup_file(file_name)

        file_old_content = "Hello Temp test patch content 123456789!"
        self.put_backup_file(file_name, file_old_content)
        file_get_content = self.get_backup_file(file_name)
        self.assertEqual(file_old_content, str(file_get_content, "utf-8"))

        hashes = self.get_backup_file_hash(file_name)
        file_new_content = "Hello 1 Temp 2 test 3 patch 4 content 5 123456789 6!"
        new_file = BytesIO()
        new_file.write(file_new_content.encode(encoding="utf-8"))
        new_file.seek(0)
        new_file.name = 'temp.txt'
        delta_list = rsyncdelta(new_file, hashes, blocksize=CHUNK_SIZE)

        with open("test_patch.delta", "wb") as f:
            pickle.dump(delta_list, f)

        with open("test_patch.delta", "rb") as f:
            self.post_backup_file_delta(file_name, f)

        file_get_content2 = self.get_backup_file(file_name)
        self.assertEqual(file_new_content, str(file_get_content2, "utf-8"))

    def requests_patch_remote_file(self):
        dst_file_name = "test_patch.txt"
        self.delete_backup_file(dst_file_name)

        file_old_content = "Hello Temp test patch content 123456789!"
        self.put_backup_file(dst_file_name, file_old_content)
        file_get_content = self.get_backup_file(dst_file_name)
        self.assertEqual(file_old_content, str(file_get_content, "utf-8"))

        host = "http://127.0.0.1:5000"
        token = "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCIsICJraWQiOiAiZGlkOmVsYXN0b3M6aWpVbkQ0S2VScGVCVUZtY0VEQ2JoeE1USlJ6VVlDUUNaTSNwcmltYXJ5In0.eyJpc3MiOiJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwic3ViIjoiQWNjZXNzVG9rZW4iLCJhdWQiOiJkaWQ6ZWxhc3RvczppZGZwS0pKMXNvRHhUMkdjZ0NSbkR0M2N1OTRabkdmek5YIiwiZXhwIjoxNjE4NjQwMTE0LCJwcm9wcyI6IntcImFwcERpZFwiOiBcImFwcGlkXCIsIFwidXNlckRpZFwiOiBcImRpZDplbGFzdG9zOmlqOGtyQVZSSml0WktKbWNDdWZvTEhRanE3TWVmM1pqVE5cIiwgXCJub25jZVwiOiBcIjRjZjVjMzdlLTg3YjEtMTFlYi04M2U1LWFjZGU0ODAwMTEyMlwifSJ9.S5HRzTea45qix7VDChC44CLor0IQXBZmPOqi866NLus8stqcmYYDUTsraBMFZFvR9eNlXQf8aaYMpDSA8Fk9aA"
        file_new_content = "Hello 1 Temp 2 test 3 patch 4 content 5 123456789 6!"
        src_file = gene_temp_file_name()
        with open(src_file.as_posix(), "wb") as f:
            f.write(file_new_content.encode(encoding="utf-8"))

        HiveBackup.patch_remote_file(src_file.as_posix(), dst_file_name, host, token)

        file_get_content2 = self.get_backup_file(dst_file_name)
        self.assertEqual(file_new_content, str(file_get_content2, "utf-8"))

    def requests_patch_local_file(self):
        src_file_name = "test_patch.txt"
        self.delete_backup_file(src_file_name)

        file_old_content = "Hello Temp test patch content 123456789!"
        self.put_backup_file(src_file_name, file_old_content)
        file_get_content = self.get_backup_file(src_file_name)
        self.assertEqual(file_old_content, str(file_get_content, "utf-8"))

        host = "http://127.0.0.1:5000"
        token = "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCIsICJraWQiOiAiZGlkOmVsYXN0b3M6aWpVbkQ0S2VScGVCVUZtY0VEQ2JoeE1USlJ6VVlDUUNaTSNwcmltYXJ5In0.eyJpc3MiOiJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwic3ViIjoiQWNjZXNzVG9rZW4iLCJhdWQiOiJkaWQ6ZWxhc3RvczppZGZwS0pKMXNvRHhUMkdjZ0NSbkR0M2N1OTRabkdmek5YIiwiZXhwIjoxNjE4NjQwMTE0LCJwcm9wcyI6IntcImFwcERpZFwiOiBcImFwcGlkXCIsIFwidXNlckRpZFwiOiBcImRpZDplbGFzdG9zOmlqOGtyQVZSSml0WktKbWNDdWZvTEhRanE3TWVmM1pqVE5cIiwgXCJub25jZVwiOiBcIjRjZjVjMzdlLTg3YjEtMTFlYi04M2U1LWFjZGU0ODAwMTEyMlwifSJ9.S5HRzTea45qix7VDChC44CLor0IQXBZmPOqi866NLus8stqcmYYDUTsraBMFZFvR9eNlXQf8aaYMpDSA8Fk9aA"
        file_new_content = "Hello 1 Temp 2 test 3 patch 4 content 5 123456789 6!"
        dst_file = gene_temp_file_name()
        with open(dst_file.as_posix(), "wb") as f:
            f.write(file_new_content.encode(encoding="utf-8"))

        with open(dst_file.as_posix(), "rb") as f:
            file_local_content = f.read()
        self.assertEqual(file_new_content, str(file_local_content, "utf-8"))

        HiveBackup.patch_local_file(src_file_name, dst_file.as_posix(), host, token)

        with open(dst_file.as_posix(), "rb") as f:
            file_local_content = f.read()
        self.assertEqual(file_old_content, str(file_local_content, "utf-8"))


if __name__ == '__main__':
    unittest.main()

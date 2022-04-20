import json
import unittest
import logging
from flask import appcontext_pushed, g
import flask_unittest
from contextlib import contextmanager

from src.utils.did.eladid import ffi, lib
from src.utils.did.did_wrapper import DID, Credential
from src import create_app

from hive.util.constants import HIVE_MODE_TEST
from hive.util.did.v1_entity import V1Entity

from tests_v1 import test_common

logger = logging.getLogger()
logger.level = logging.DEBUG


class DIDApp(V1Entity):
    def __init__(self, name, mnemonic=None, passphrase=None):
        V1Entity.__init__(self, name, mnemonic=mnemonic, passphrase=passphrase)

    def issue_auth(self, app) -> Credential:
        props = {'appDid': app.appId}
        return super().create_credential('AppIdCredential', props, owner_did=DID(app.get_did()))

    def issue_backup_auth(self, hive1_did, host, hive2_did):
        props = {'sourceDID': hive1_did, 'targetHost': host, 'targetDID': hive2_did}
        return super().create_credential('BackupCredential', props, owner_did=DID.from_string(hive1_did)).vc


class DApp(V1Entity):
    access_token = "123"
    appId = test_common.app_id

    def __init__(self, name, appId=None, mnemonic=None, passphrase=None):
        if (appId is not None):
            self.appId = appId
        V1Entity.__init__(self, name, mnemonic=mnemonic, passphrase=passphrase, need_resolve=False)

    def access_api_by_token(self):
        return self.access_token

    def set_access_token(self, token):
        self.access_token = token


class HiveAuthTestCase(flask_unittest.ClientTestCase):
    app = create_app(mode=HIVE_MODE_TEST)

    @classmethod
    def setUpClass(cls):
        logging.getLogger("HiveAuthTestCase").debug("Setting up HiveAuthTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HiveAuthTestCase").debug("\n\nShutting down HiveAuthTestCase")

    def setUp(self, client):
        logging.getLogger("HiveAuthTestCase").info("\n")
        self.app.config['TESTING'] = True
        self.content_type = ("Content-Type", "application/json")
        self.json_header = [self.content_type, ]

    def tearDown(self, client):
        logging.getLogger("HiveAuthTestCase").info("\n")

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

    def test_a_echo(self, client):
        logging.getLogger("HiveAuthTestCase").debug("\nRunning test_a_echo")
        r, s = self.parse_response(
            client.post('/api/v1/echo', data=json.dumps({"key": "value"}), headers=self.json_header)
        )
        logging.getLogger("HiveAuthTestCase").debug(f"\nr:{r}")
        self.assert200(s)

    def __test_auth_common(self, client, didapp, testapp):
        # sign_in
        doc = lib.DIDStore_LoadDID(testapp.get_did_store(), testapp.get_did())
        doc_str = ffi.string(lib.DIDDocument_ToJson(doc, True)).decode()
        logging.getLogger("HiveAuthTestCase").debug(f"\ndoc_str: {doc_str}")
        doc = json.loads(doc_str)
        rt, s = self.parse_response(
            client.post('/api/v1/did/sign_in', data=json.dumps({"document": doc,}), headers=self.json_header)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")
        jwt = rt["challenge"]
        # print(jwt)
        jws = lib.DefaultJWSParser_Parse(jwt.encode())
        if not jws:
            assert False, ffi.string(lib.DIDError_GetLastErrorMessage()).decode()
        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        self.assertEqual(aud, testapp.get_did_string())
        nonce = ffi.string(lib.JWT_GetClaim(jws, "nonce".encode())).decode()
        hive_did = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)

        # auth
        vc = didapp.issue_auth(testapp)
        vp_json = testapp.create_presentation_str(vc, nonce, hive_did)
        auth_token = testapp.create_vp_token(vp_json, "DIDAuthResponse", hive_did, 60)
        # print(auth_token)
        logging.getLogger("HiveAuthTestCase").debug(f"\nauth_token: {auth_token}")

        rt, s = self.parse_response(
            client.post('/api/v1/did/auth', data=json.dumps({"jwt": auth_token,}), headers=self.json_header)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")

        token = rt["access_token"]
        jws = lib.DefaultJWSParser_Parse(token.encode())
        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        self.assertEqual(aud, testapp.get_did_string())
        issuer = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)
        # print(token)
        logging.getLogger("HiveAuthTestCase").debug(f"\ntoken: {token}")
        testapp.set_access_token(token)

        # auth_check
        # token = test_common.get_auth_token()
        self.json_header = [
            ("Authorization", "token " + token),
            self.content_type,
        ]
        rt, s = self.parse_response(client.post('/api/v1/did/check_token', headers=self.json_header))
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")
        return token, hive_did

    def test_b_auth(self, client):
        logging.getLogger("HiveAuthTestCase").debug("\nRunning test_b_auth")

        didapp = DIDApp("didapp", "clever bless future fuel obvious black subject cake art pyramid member clump")
        testapp = DApp("testapp", test_common.app_id,
                       "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        self.__test_auth_common(client, didapp, testapp)

    def test_c_auth(self, client):
        logging.getLogger("HiveAuthTestCase").debug("\nRunning test_c_auth")
        didapp = DIDApp("didapp", "clever bless future fuel obvious black subject cake art pyramid member clump")
        testapp1 = DApp("testapp", test_common.app_id, "chimney limit involve fine absent topic catch chalk goat era suit leisure")
        testapp2 = DApp("testapp2", test_common.app_id2, "chimney limit involve fine absent topic catch chalk goat era suit leisure", "")
        # testapp3 = DApp("testapp3", "appid3", "license mango cluster candy payment prefer video rice desert pact february rabbit")
        token = self.__test_auth_common(client, didapp, testapp1)
        token2 = self.__test_auth_common(client, didapp, testapp2)
        logging.getLogger("HiveAuthTestCase").debug(f"\ntoken: {token}")
        # self.__test_auth_common(didapp, testapp3)


if __name__ == '__main__':
    unittest.main()

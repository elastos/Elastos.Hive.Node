import json
import sys
import unittest
import logging
from flask import appcontext_pushed, g
from contextlib import contextmanager
from datetime import datetime

# import os
# import sys
# sys.path.append(os.getcwd())
# sys.path.append(os.getcwd() + "/hive/util/did")

from hive.util.did.entity import Entity
from hive.util.did.eladid import ffi, lib

from hive import create_app, HIVE_MODE_TEST
from tests import test_common

logger = logging.getLogger()
logger.level = logging.DEBUG


@contextmanager
def name_set(app, name):
    def handler(sender, **kwargs):
        g.app_name = name

    with appcontext_pushed.connected_to(handler, app):
        yield


# ---------------
class DIDApp(Entity):
    issuer = None

    def __init__(self, name, mnemonic=None):
        Entity.__init__(self, name, mnemonic)
        self.issuer = lib.Issuer_Create(self.did, ffi.NULL, self.store)

    def __del__(self):
        lib.Issuer_Destroy(self.issuer)
        # Entity.__del__(self)

    def issue_auth(self, app):
        props = {
            'appDid': app.appId,
        }
        return self.issue_auth_vc("AppIdCredential", props, app.did)

    def issue_backup_auth(self, hive1_did, hive2_did):
        props = {
            'sourceDID': hive1_did,
            'targetHost': "http://0.0.0.0:5001",
            'targetDID': hive2_did,
        }
        did = lib.DID_FromString(hive1_did.encode())
        return self.issue_auth_vc("BackupCredential", props, did)

# ---------------
class DApp(Entity):
    access_token = "123"
    appId = test_common.app_id

    def __init__(self, name, appId=None, mnemonic=None, passphrase=None):
        if (appId is not None):
            self.appId = appId
        Entity.__init__(self, name, mnemonic, passphrase)

    def access_api_by_token(self):
        return self.access_token

    def set_access_token(self, token):
        self.access_token = token

# ------------------
class HiveAuthTestCase(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(HiveAuthTestCase, self).__init__(methodName)

    @classmethod
    def setUpClass(cls):
        cls.stream_handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(cls.stream_handler)
        logging.getLogger("HiveAuthTestCase").debug("Setting up HiveAuthTestCase\n")

    @classmethod
    def tearDownClass(cls):
        logging.getLogger("HiveAuthTestCase").debug("\n\nShutting down HiveAuthTestCase")
        logger.removeHandler(cls.stream_handler)

    def setUp(self):
        logging.getLogger("HiveAuthTestCase").info("\n")
        self.app = create_app(mode=HIVE_MODE_TEST)
        self.app.config['TESTING'] = True
        self.test_client = self.app.test_client()
        self.content_type = ("Content-Type", "application/json")

        self.json_header = [
            self.content_type,
        ]
        self.auth = None

    def tearDown(self):
        logging.getLogger("HiveAuthTestCase").info("\n")

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
        logging.getLogger("HiveAuthTestCase").debug("\nRunning test_a_echo")
        r, s = self.parse_response(
            self.test_client.post('/api/v1/echo',
                                  data=json.dumps({"key": "value"}),
                                  headers=self.json_header)
        )
        logging.getLogger("HiveAuthTestCase").debug(f"\nr:{r}")
        self.assert200(s)

    def __test_auth_common(self, didapp, testapp):
        # sign_in
        doc = lib.DIDStore_LoadDID(testapp.store, testapp.did)
        doc_str = ffi.string(lib.DIDDocument_ToJson(doc, True)).decode()
        logging.getLogger("HiveAuthTestCase").debug(f"\ndoc_str: {doc_str}")
        doc = json.loads(doc_str)
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/did/sign_in',
                                  data=json.dumps({
                                      "document": doc,
                                  }),
                                  headers=self.json_header)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")
        jwt = rt["challenge"]
        # print(jwt)
        jws = lib.DefaultJWSParser_Parse(jwt.encode())
        # if not jws:
        #     print(ffi.string(lib.DIDError_GetMessage()).decode())
        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        self.assertEqual(aud, testapp.get_did_string())
        nonce = ffi.string(lib.JWT_GetClaim(jws, "nonce".encode())).decode()
        hive_did = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)

        # auth
        vc = didapp.issue_auth(testapp)
        vp_json = testapp.create_presentation(vc, nonce, hive_did)
        auth_token = testapp.create_vp_token(vp_json, "DIDAuthResponse", hive_did, 60)
        # print(auth_token)
        logging.getLogger("HiveAuthTestCase").debug(f"\nauth_token: {auth_token}")

        rt, s = self.parse_response(
            self.test_client.post('/api/v1/did/auth',
                                  data=json.dumps({
                                      "jwt": auth_token,
                                  }),
                                  headers=self.json_header)
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
        rt, s = self.parse_response(
            self.test_client.post('/api/v1/did/check_token',
                                  headers=self.json_header)
        )
        self.assert200(s)
        self.assertEqual(rt["_status"], "OK")
        return token, hive_did

    #test sign in auth
    def test_b_auth(self):
        logging.getLogger("HiveAuthTestCase").debug("\nRunning test_b_auth")

        didapp = DIDApp("didapp", "clever bless future fuel obvious black subject cake art pyramid member clump")
        testapp = DApp("testapp", test_common.app_id,
                       "amount material swim purse swallow gate pride series cannon patient dentist person")
        self.__test_auth_common(didapp, testapp)

    def test_c_auth(self):
        logging.getLogger("HiveAuthTestCase").debug("\nRunning test_c_auth")
        didapp = DIDApp("didapp", "clever bless future fuel obvious black subject cake art pyramid member clump")
        testapp1 = DApp("testapp1", test_common.app_id, "amount material swim purse swallow gate pride series cannon patient dentist person")
        testapp2 = DApp("testapp2", test_common.app_id2, "chimney limit involve fine absent topic catch chalk goat era suit leisure", "")
        # testapp3 = DApp("testapp3", "appid3", "license mango cluster candy payment prefer video rice desert pact february rabbit")
        token = self.__test_auth_common(didapp, testapp1)
        token2 = self.__test_auth_common(didapp, testapp2)
        logging.getLogger("HiveAuthTestCase").debug(f"\ntoken: {token}")
        # self.__test_auth_common(didapp, testapp3)
        pass

    #test bauck up auth
    def test_d_auth(self):
        didapp = DIDApp("didapp", "clever bless future fuel obvious black subject cake art pyramid member clump")
        testapp = DApp("testapp", test_common.app_id,
                       "amount material swim purse swallow gate pride series cannon patient dentist person")
        token, hive_did = self.__test_auth_common(didapp, testapp)

        # backup_auth
        vc = didapp.issue_backup_auth(hive_did, hive_did)
        vc_json = ffi.string(lib.Credential_ToString(vc, True)).decode()

        rt, s = self.parse_response(
            self.test_client.post('/api/v1/backup/save/to/node',
                                  data=json.dumps({
                                      "backup_credential": vc_json,
                                  }),
                                  headers=self.json_header)
        )
        self.assert200(s)
        # self.assertEqual(rt["_status"], "OK")
        pass


if __name__ == '__main__':
    unittest.main()

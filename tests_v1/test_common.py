import json
import logging
import shutil
from datetime import datetime
from time import time
from io import BytesIO

from hive.util.did.eladid import ffi, lib

from hive.util.constants import DID_INFO_TOKEN
from hive.util.did_info import get_did_info_by_did_appid

from hive.util.payment.vault_backup_service_manage import get_vault_backup_path
from hive.util.payment.vault_service_manage import setup_vault_service, remove_vault_service, get_vault_path

did = "did:elastos:ij8krAVRJitZKJmcCufoLHQjq7Mef3ZjTN"
app_id = "appid"
did2 = "did:elastos:ioLFi22fodmFUAFKia6uTV2W8Jz9vEcQyP"
app_id2 = "appid2"
# nonce = "c4211de6-e297-11ea-9bab-acde48001122"
token = "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCIsICJraWQiOiAiZGlkOmVsYXN0b3M6aWpVbkQ0S2VScGVCVUZtY0VEQ2JoeE1USlJ6VVlDUUNaTSNwcmltYXJ5In0.eyJpc3MiOiJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwic3ViIjoiQWNjZXNzVG9rZW4iLCJhdWQiOiJkaWQ6ZWxhc3RvczppZGZwS0pKMXNvRHhUMkdjZ0NSbkR0M2N1OTRabkdmek5YIiwiZXhwIjoyNzUyNzM5NzIwNSwicHJvcHMiOiJ7XCJhcHBEaWRcIjogXCJhcHBpZFwiLCBcInVzZXJEaWRcIjogXCJkaWQ6ZWxhc3RvczppajhrckFWUkppdFpLSm1jQ3Vmb0xIUWpxN01lZjNaalROXCIsIFwibm9uY2VcIjogXCI1NDRiZTNjNi0zOTAzLTExZWItYWY0OC1hY2RlNDgwMDExMjJcIn0ifQ.xGqGT-doIWrsQyynv0DVq6YzTDyHpJrYQghX0dgLYe6qNXZ3jhq5QQPKKVFQhY3QwdANnn8Dr_2xbL8WuKZeuA"
token2 = "eyJhbGciOiAiRVMyNTYiLCAidHlwIjogIkpXVCIsICJ2ZXJzaW9uIjogIjEuMCIsICJraWQiOiAiZGlkOmVsYXN0b3M6aWpVbkQ0S2VScGVCVUZtY0VEQ2JoeE1USlJ6VVlDUUNaTSNwcmltYXJ5In0.eyJpc3MiOiJkaWQ6ZWxhc3RvczppalVuRDRLZVJwZUJVRm1jRURDYmh4TVRKUnpVWUNRQ1pNIiwic3ViIjoiQWNjZXNzVG9rZW4iLCJhdWQiOiJkaWQ6ZWxhc3RvczppZTFNNkpKNFpmVHZhYTZONEJ0blJZQzE5OUFncjZpaHptIiwiZXhwIjoyNzUyNzM5NzM2OSwicHJvcHMiOiJ7XCJhcHBEaWRcIjogXCJhcHBpZDJcIiwgXCJ1c2VyRGlkXCI6IFwiZGlkOmVsYXN0b3M6aWo4a3JBVlJKaXRaS0ptY0N1Zm9MSFFqcTdNZWYzWmpUTlwiLCBcIm5vbmNlXCI6IFwiYjdhMDNiZGUtMzkwMy0xMWViLThlM2QtYWNkZTQ4MDAxMTIyXCJ9In0.XLj98LePKgSvb7asOns4tOqauHETaDOSv-L4qkcYxrDOM9f4wrHS13gOV8Zi0v2Vw9p7ynKLRFM7Vt1ijW6-Kg"


def setup_test_auth_token():
    info = get_did_info_by_did_appid(did, app_id)
    if info:
        global token
        token = info[DID_INFO_TOKEN]

    info2 = get_did_info_by_did_appid(did, app_id)
    if info2:
        global token2
        token2 = info2[DID_INFO_TOKEN]
    return


def delete_test_auth_token():
    # delete_did_info(did, app_id)
    pass


def get_auth_did():
    return did


def get_auth_app_did():
    return app_id


def get_auth_token():
    return token


def get_auth_token2():
    return token2


def setup_test_vault(did):
    setup_vault_service(did, 100, -1)


def remove_test_vault(did):
    remove_vault_service(did)


def test_auth_common(self, user_did, app_did):
    # sign_in
    doc = lib.DIDStore_LoadDID(app_did.store, app_did.did)
    doc_str = ffi.string(lib.DIDDocument_ToJson(doc, True)).decode()
    logging.getLogger("test_auth_common").debug(f"\ndoc_str: {doc_str}")
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
    self.assertEqual(aud, app_did.get_did_string())
    nonce = ffi.string(lib.JWT_GetClaim(jws, "nonce".encode())).decode()
    hive_did = ffi.string(lib.JWT_GetIssuer(jws)).decode()
    lib.JWT_Destroy(jws)

    # auth
    vc = user_did.issue_auth(app_did)
    vp_json = app_did.create_presentation(vc, nonce, hive_did)
    auth_token = app_did.create_vp_token(vp_json, "DIDAuthResponse", hive_did, 60)
    # print(auth_token)
    logging.getLogger("test_auth_common").debug(f"\nauth_token: {auth_token}")

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
    self.assertEqual(aud, app_did.get_did_string())
    issuer = ffi.string(lib.JWT_GetIssuer(jws)).decode()
    lib.JWT_Destroy(jws)
    # print(token)
    logging.getLogger("test_auth_common").debug(f"\ntoken: {token}")
    app_did.set_access_token(token)

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


def create_upload_file(self, file_name, data):
    temp = BytesIO()
    temp.write(data.encode(encoding="utf-8"))
    temp.seek(0)
    temp.name = 'temp.txt'

    upload_file_url = "/api/v1/files/upload/" + file_name
    r2, s = self.parse_response(
        self.test_client.post(upload_file_url,
                              data=temp,
                              headers=self.upload_auth)
    )
    self.assert200(s)
    self.assertEqual(r2["_status"], "OK")

    r3, s = self.parse_response(
        self.test_client.get('/api/v1/files/properties?path=' + file_name, headers=self.auth)
    )

    self.assert200(s)
    self.assertEqual(r3["_status"], "OK")
    logging.getLogger("HiveFileTestCase").debug(json.dumps(r3))


def upsert_collection(self, col_name, doc):
    logging.getLogger("HiveMongoDbTestCase").debug("\nRunning test_1_create_collection")
    r, s = self.parse_response(
        self.test_client.post('/api/v1/db/create_collection',
                              data=json.dumps(
                                  {
                                      "collection": col_name
                                  }
                              ),
                              headers=self.auth)
    )
    self.assert200(s)

    r, s = self.parse_response(
        self.test_client.post('/api/v1/db/insert_one',
                              data=json.dumps(
                                  {
                                      "collection": col_name,
                                      "document": doc,
                                  }
                              ),
                              headers=self.auth)
    )
    self.assert200(s)
    self.assertEqual(r["_status"], "OK")


def prepare_vault_data(self):
    doc = dict()
    for i in range(1, 10):
        doc["work" + str(i)] = "work_content" + str(i)
        upsert_collection(self, "works", doc)
    create_upload_file(self, "test0.txt", "this is a test 0 file")
    create_upload_file(self, "f1/test1.txt", "this is a test 1 file")
    create_upload_file(self, "f1/test1_2.txt", "this is a test 1_2 file")
    create_upload_file(self, "f2/f1/test2.txt", "this is a test 2 file")
    create_upload_file(self, "f2/f1/test2_2.txt", "this is a test 2_2 file")


def copy_to_backup_data(self):
    vault_path = get_vault_path(self.did)
    backup_path = get_vault_backup_path(self.did)
    print(vault_path.as_posix())
    print(backup_path.as_posix())
    if backup_path.exists():
        shutil.rmtree(backup_path.as_posix())
    shutil.copytree(vault_path.as_posix(), backup_path.as_posix())


def move_to_backup_data(self):
    vault_path = get_vault_path(self.did)
    backup_path = get_vault_backup_path(self.did)
    print(vault_path.as_posix())
    print(backup_path.as_posix())
    if backup_path.exists():
        shutil.rmtree(backup_path.as_posix())
    shutil.move(vault_path.as_posix(), backup_path.as_posix())

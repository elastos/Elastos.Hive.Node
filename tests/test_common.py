import json
import logging

from datetime import datetime
from hive.util.did.entity import Entity
from hive.util.did.eladid import ffi, lib

class DIDApp(Entity):
    issuer = None

    def __init__(self, name, mnemonic=None):
        Entity.__init__(self, name, mnemonic)
        self.issuer = lib.Issuer_Create(self.did, ffi.NULL, self.store)

    def __del__(self):
        lib.Issuer_Destroy(self.issuer)
        # Entity.__del__(self)

    def issue_auth(self, app):
        types = ffi.new("char*[]", [ffi.new("char[]", "DIDAuthCredential".encode())])
        props = {
            'userDid': self.get_did_string(),
            'appDid': app.get_did_string(),
            'purpose': 'did:elastos:ieaA5VMWydQmVJtM5daW5hoTQpcuV38mHM',
            'scope': ['read', 'write']
        }
        issuerid = self.did
        issuerdoc = lib.DIDStore_LoadDID(self.store, self.did)
        expires = lib.DIDDocument_GetExpires(issuerdoc)
        credid = lib.DIDURL_NewByDid(issuerid, self.name.encode())
        vc = lib.Issuer_CreateCredentialByString(self.issuer, issuerid, credid, types, 1,
                                                 json.dumps(props).encode(), expires, self.storepass)
        vcJson = ffi.string(lib.Credential_ToString(vc, True)).decode()
        logging.debug(vcJson)
        return vc


# ---------------
class DApp(Entity):
    access_token = "123"

    def __init__(self, name, mnemonic=None):
        Entity.__init__(self, name, mnemonic)

    def access_api_by_token(self):
        return self.access_token

    def set_access_token(self, token):
        self.access_token = token

    def create_presentation(self, vc, realm, nonce):
        vp = lib.Presentation_Create(self.did, ffi.NULL, self.store, self.storepass, nonce.encode(),
                                     realm.encode(), 1, vc)
        # print_err()
        vp_json = ffi.string(lib.Presentation_ToJson(vp, True)).decode()
        logging.debug(vp_json)
        return vp_json

    def create_token(self, vp_json):
        doc = lib.DIDStore_LoadDID(self.store, self.did)
        builder = lib.DIDDocument_GetJwtBuilder(doc)
        ticks = int(datetime.now().timestamp())
        iat = ticks
        nbf = ticks
        exp = ticks + 10000

        lib.JWTBuilder_SetHeader(builder, "type".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())

        lib.JWTBuilder_SetSubject(builder, "DIDAuthCredential".encode())
        lib.JWTBuilder_SetAudience(builder, "Hive".encode())
        lib.JWTBuilder_SetIssuedAt(builder, iat)
        lib.JWTBuilder_SetExpiration(builder, exp)
        lib.JWTBuilder_SetNotBefore(builder, nbf)
        lib.JWTBuilder_SetClaimWithJson(builder, "vp".encode(), vp_json.encode())

        token = ffi.string(lib.JWTBuilder_Compact(builder)).decode()
        lib.JWTBuilder_Destroy(builder)
        return token


def get_auth_token(self):
    self.didapp = DIDApp("didapp")
    self.testapp = DApp("testapp")

    vc = self.didapp.issue_auth(self.testapp)
    vp_json = self.testapp.create_presentation(vc, "testapp", "873172f58701a9ee686f0630204fee59")
    auth_token = self.testapp.create_token(vp_json)

    rt, s = self.parse_response(
        self.test_client.post('/api/v1/did/auth',
                              data=json.dumps({
                                  "jwt": auth_token,
                              }),
                              headers=self.json_header)
    )
    self.assert200(s)
    self.assertEqual(rt["_status"], "OK")
    self.testapp.set_access_token(rt["token"])

    logging.debug(f"token: {rt['token']}")
    return rt["token"]

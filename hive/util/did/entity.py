import logging
import os
import pathlib
import json
from datetime import datetime
from hive.util.did.eladid import ffi, lib
import requests

from hive.util.did.did_init import init_did
from hive.settings import hive_setting

# ---------------
from hive.util.error_code import SUCCESS


class Entity:
    passphrase = "secret"
    storepass = "password"
    store = None
    doc = None
    did = None
    mnemonic = None
    did_str = None
    name = "Entity"

    def __init__(self, name, mnemonic=None, passphrase=None):
        self.name = name
        if not mnemonic is None:
            self.mnemonic = mnemonic
        if not passphrase is None:
            self.passphrase = passphrase
        self.store, self.did, self.doc = init_did(self.mnemonic, self.passphrase, self.storepass, self.name)
        self.storepass = self.storepass.encode()
        self.did_str = self.get_did_string()
        print("    Back-end DID string: " + self.did_str)
        # print(self.did_str)

    def __del__(self):
        pass

    def get_did_string_from_did(self, did):
        if not did:
            return None

        method = lib.DID_GetMethod(did)
        if not method:
            return None
        method = ffi.string(method).decode()
        sep_did = lib.DID_GetMethodSpecificId(did)
        if not sep_did:
            return None
        sep_did = ffi.string(sep_did).decode()
        return "did:" + method + ":" + sep_did

    def get_did_string(self):
        if self.did_str is None:
            self.did_str = self.get_did_string_from_did(self.did)
        return self.did_str

    def get_did_store(self):
        return self.store

    def get_did(self):
        return self.did

    def get_document(self):
        return self.doc

    def get_name(self):
        return self.name

    def get_store_password(self):
        return self.storepass

    def get_error_message(self, prompt):
        err_message = ffi.string(lib.DIDError_GetLastErrorMessage()).decode()
        if not prompt is None:
            err_message = prompt + " error: " + err_message
        return err_message

    def issue_auth_vc(self, type, props, owner):
        type0 = ffi.new("char[]", type.encode())
        types = ffi.new("char **", type0)

        issuerid = self.did
        issuerdoc = self.doc
        expires = lib.DIDDocument_GetExpires(issuerdoc)
        credid = lib.DIDURL_NewByDid(owner, self.name.encode())
        vc = lib.Issuer_CreateCredentialByString(self.issuer, owner, credid, types, 1,
                                                 json.dumps(props).encode(), expires, self.storepass)
        lib.DIDURL_Destroy(credid)
        # vcJson = ffi.string(lib.Credential_ToString(vc, True)).decode()
        # logging.debug(f"vcJson: {vcJson}")
        # print(vcJson)
        return vc

    def create_presentation(self, vc, nonce, realm):
        vpid = lib.DIDURL_NewByDid(self.did, "jwtvp".encode())
        type0 = ffi.new("char[]", "VerifiablePresentation".encode())
        types = ffi.new("char **", type0)

        vp = lib.Presentation_Create(vpid, self.did, types, 1, nonce.encode(),
                realm.encode(), ffi.NULL, self.store, self.storepass, 1, vc)
        lib.DIDURL_Destroy(vpid)

        # print_err()
        vp_json = ffi.string(lib.Presentation_ToJson(vp, True)).decode()
        # print(vp_json)
        logging.debug(f"vp_json: {vp_json}")
        return vp_json

    def create_vp_token(self, vp_json, subject, hive_did, expire):
        doc = lib.DIDStore_LoadDID(self.store, self.did)
        builder = lib.DIDDocument_GetJwtBuilder(doc)
        ticks = int(datetime.now().timestamp())
        iat = ticks
        nbf = ticks
        exp = ticks + expire

        lib.JWTBuilder_SetHeader(builder, "type".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())

        lib.JWTBuilder_SetSubject(builder, subject.encode())
        lib.JWTBuilder_SetAudience(builder, hive_did.encode())
        lib.JWTBuilder_SetIssuedAt(builder, iat)
        lib.JWTBuilder_SetExpiration(builder, exp)
        lib.JWTBuilder_SetNotBefore(builder, nbf)
        lib.JWTBuilder_SetClaimWithJson(builder, "presentation".encode(), vp_json.encode())

        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        token = ffi.string(lib.JWTBuilder_Compact(builder)).decode()
        lib.JWTBuilder_Destroy(builder)
        # print(token)
        return token

    def get_auth_token_by_sign_in(self, base_url, vc_str, subject):
        vc = lib.Credential_FromJson(vc_str.encode(), ffi.NULL)
        if not vc:
            return None, None,"The credential string is error, unable to rebuild to a credential object."

        #sign_in
        doc = lib.DIDStore_LoadDID(self.store, self.did)
        doc_str = ffi.string(lib.DIDDocument_ToJson(doc, True)).decode()
        doc = json.loads(doc_str)

        rt, status_code, err = self.post(base_url + '/api/v1/did/sign_in', {"document": doc})

        if err != None:
            return None, None, "Post sign_in error: " + err

        jwt = rt["challenge"]
        if jwt is None:
            return None, None, "Challenge is none."

        # print(jwt)
        jws = lib.DefaultJWSParser_Parse(jwt.encode())
        if not jws:
            return None, None, "Challenge DefaultJWSParser_Parse error: " + ffi.string(lib.DIDError_GetLastErrorMessage()).decode()

        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        if aud != self.get_did_string():
            lib.JWT_Destroy(jws)
            return None, None, "Audience is error."

        nonce = ffi.string(lib.JWT_GetClaim(jws, "nonce".encode())).decode()
        if nonce is None:
            lib.JWT_Destroy(jws)
            return None, None, "Nonce is none."

        hive_did = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)
        if hive_did is None:
            return None, None, "Issuer is none."

        #auth_token
        vp_json = self.create_presentation(vc, nonce, hive_did)
        if vp_json is None:
            return None, None, "create_presentation error."
        auth_token = self.create_vp_token(vp_json, subject, hive_did, hive_setting.AUTH_CHALLENGE_EXPIRED)
        if auth_token is None:
            return None, None, "create_vp_token error."
        return auth_token, hive_did, None

    def get_backup_auth_from_node(self, base_url, auth_token, hive_did):
        rt, status_code, err = self.post(base_url + '/api/v1/did/backup_auth', {"jwt": auth_token})
        if err != None:
            return None, "Post backup_auth error: " + err

        token = rt["backup_token"]
        if token is None:
            return None,  "Token is none."

        jws = lib.DefaultJWSParser_Parse(token.encode())
        if not jws:
            return None, "Backup token DefaultJWSParser_Parse error: " + ffi.string(lib.DIDError_GetLastErrorMessage()).decode()

        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        if aud != self.get_did_string():
            lib.JWT_Destroy(jws)
            return None, "Audience is error."

        issuer = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)
        if issuer is None:
            return None, "Issuer is none."

        if issuer != hive_did:
            return None, "Issuer is error."

        return token, None

    def post(self, url, param):
        try:
            err = None
            r = requests.post(url, json=param, headers={"Content-Type": "application/json"})
            rt = r.json()
            if r.status_code != SUCCESS:
                err = "[" + str(r.status_code) + "]"
                if "_error" in rt and "message" in rt["_error"]:
                    err += rt["_error"]["message"]
        except Exception as e:
            err = f"Exception in post to '{url}'': {e}"
            logging.error(err)
            return None, None, err
        return rt, r.status_code, err



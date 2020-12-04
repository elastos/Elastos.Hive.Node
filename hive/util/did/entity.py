import logging
import os
import pathlib
import json
from datetime import datetime
from eladid import ffi, lib

from hive.util.did.did_init import init_did

# ---------------
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
        err_message = ffi.string(lib.DIDError_GetMessage()).decode()
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
        # vcJson = ffi.string(lib.Credential_ToString(vc, True)).decode()
        # logging.debug(f"vcJson: {vcJson}")
        # print(vcJson)
        return vc

    def create_presentation(self, vc, nonce, realm):
        vp = lib.Presentation_Create(self.did, ffi.NULL, self.store, self.storepass, nonce.encode(),
                                     realm.encode(), 1, vc)
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



import logging
import json
import os
from datetime import datetime
import requests

from src.utils_v1.did.eladid import ffi, lib
from src.utils.http_exception import BadRequestException
from src.utils.resolver import DIDResolver
from src.settings import hive_setting
from src.utils_v1.error_code import SUCCESS


class Entity:
    name = "Entity"
    mnemonic = None
    passphrase = "secret"
    storepass = "password"
    did_store = None
    did = None
    did_str = None
    doc = None

    def __init__(self, name, mnemonic=None, passphrase=None, need_resolve=True):
        self.name = name
        if mnemonic is not None:
            self.mnemonic = mnemonic
        if passphrase is not None:
            self.passphrase = passphrase
        self.init_did(need_resolve)
        self.did_str = self.get_did_string_from_did(self.did)
        logging.info(f"    V2 Back-end DID string: {self.did_str}, need_resolver={need_resolve}, "
                     f"name={self.name}, mnemonic={self.mnemonic}")

    def init_did(self, need_resolve):
        store_dir = hive_setting.DID_DATA_STORE_PATH + os.sep + self.name
        self.did_store = lib.DIDStore_Open(store_dir.encode())
        if not self.did_store:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't create store"))

        root_identity = self.get_root_identity()
        self.did, self.doc = self.init_did_by_root_identity(root_identity, need_resolve=need_resolve)
        lib.RootIdentity_Destroy(root_identity)

    def get_root_identity(self):
        # TODO: release c_id
        c_id = lib.RootIdentity_CreateId(self.mnemonic.encode(), self.passphrase.encode())
        if not c_id:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't create root identity id string"))

        if lib.DIDStore_ContainsRootIdentity(self.did_store, c_id) == 1:
            root_identity = lib.DIDStore_LoadRootIdentity(self.did_store, c_id)
            if not root_identity:
                raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't load root identity"))
            return root_identity

        root_identity = lib.RootIdentity_Create(self.mnemonic.encode(),
                                                self.passphrase.encode(),
                                                True, self.did_store, self.storepass.encode())
        if not root_identity:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't create root identity"))
        return root_identity

    def init_did_by_root_identity(self, root_identity, need_resolve=True):
        # TODO: Should align with Hive JS.
        c_did, c_doc = lib.RootIdentity_GetDIDByIndex(root_identity, 0), None
        if c_did and lib.DIDStore_ContainsDID(self.did_store, c_did) == 1 \
                and lib.DIDStore_ContainsPrivateKeys(self.did_store, c_did) == 1:
            # direct get
            return c_did, self.get_doc_from_did(c_did)

        if need_resolve:
            # resolve, then get
            success = lib.RootIdentity_SynchronizeByIndex(root_identity, 0, ffi.NULL)
            if not success:
                raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't create did doc"))
            return c_did, self.get_doc_from_did(c_did)

        # create, then get
        c_doc = lib.RootIdentity_NewDIDByIndex(root_identity, 0, self.storepass.encode(), ffi.NULL, True)
        if not c_doc:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't create did doc"))
        c_did = lib.DIDDocument_GetSubject(c_doc)
        if not c_did:
            lib.DIDDocument_Destroy(c_doc)
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't get doc from created did"))
        return c_did, c_doc

    def get_doc_from_did(self, c_did):
        c_doc = lib.DIDStore_LoadDID(self.did_store, c_did)
        if not c_doc:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't load did doc"))
        return c_doc

    def __del__(self):
        if self.doc:
            lib.DIDDocument_Destroy(self.doc)
        if self.did:
            lib.DID_Destroy(self.did)

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
        return self.did_str

    def get_did_store(self):
        return self.did_store

    def get_did(self):
        return self.did

    def get_document(self):
        return self.doc

    def get_name(self):
        return self.name

    def get_store_password(self):
        return self.storepass

    def create_presentation(self, vc, nonce, realm):
        vpid = lib.DIDURL_NewFromDid(self.did, "jwtvp".encode())
        type0 = ffi.new("char[]", "VerifiablePresentation".encode())
        types = ffi.new("char **", type0)

        vp = lib.Presentation_Create(vpid, self.did, types, 1, nonce.encode(),
                                     realm.encode(), ffi.NULL, self.did_store, self.storepass.encode(), 1, vc)
        if not vp:
            logging.error(DIDResolver.get_errmsg())
        lib.DIDURL_Destroy(vpid)

        # print_err()
        vp_json = ffi.string(lib.Presentation_ToJson(vp, True)).decode()
        # print(vp_json)
        logging.debug(f"vp_json: {vp_json}")
        return vp_json

    def create_vp_token(self, vp_json, subject, hive_did, expire):
        doc = lib.DIDStore_LoadDID(self.did_store, self.did)
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

        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass.encode())
        token = ffi.string(lib.JWTBuilder_Compact(builder)).decode()
        lib.JWTBuilder_Destroy(builder)
        # print(token)
        return token

    def get_auth_token_by_sign_in(self, base_url, vc_str, subject):
        vc = lib.Credential_FromJson(vc_str.encode(), ffi.NULL)
        if not vc:
            return None, None,"The credential string is error, unable to rebuild to a credential object."

        #sign_in
        doc = lib.DIDStore_LoadDID(self.did_store, self.did)
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
            error_msg = lib.DIDError_GetLastErrorMessage()
            msg = ffi.string(error_msg).decode() if error_msg else 'Unknown DID error.'
            return None, None, "Challenge DefaultJWSParser_Parse error: " + msg

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
            error_msg = lib.DIDError_GetLastErrorMessage()
            msg = ffi.string(error_msg).decode() if error_msg else 'Unknown DID error.'
            return None, "Backup token DefaultJWSParser_Parse error: " + msg

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

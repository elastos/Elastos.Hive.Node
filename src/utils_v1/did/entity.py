import logging
import json
import os
from datetime import datetime

import base58
import requests

from src.utils_v1.did.eladid import ffi, lib

from src.utils.consts import DID
from src.utils.http_exception import BadRequestException, HiveException
from src.utils.resolver import DIDResolver
from src.settings import hive_setting
from src.utils_v1.common import gene_temp_file_name
from src.utils_v1.did.did_wrapper import DIDStore, DIDDocument, RootIdentity, Issuer
from src.utils_v1.error_code import SUCCESS


class Entity:
    def __init__(self, name='Entity', mnemonic=None, passphrase='secret', storepass='password', need_resolve=True, from_file=False, file_content=None):
        """
        :param file_content: base58
        """
        self.name = name
        self.storepass = storepass  # TODO: Try to remove this with self.did_store
        store_dir = hive_setting.DID_DATA_STORE_PATH + os.sep + self.name
        self.did_store: DIDStore = DIDStore(store_dir, storepass)
        self.did: DID
        self.doc: DIDDocument
        if from_file:
            assert file_content, 'Entity.__init__: file_content must provide.'
            self.did, self.doc = self.init_did_from_file(file_content, passphrase)
        else:
            assert mnemonic, 'Entity.__init__: mnemonic must provide.'
            self.did, self.doc = self.init_did_from_mnemonic(mnemonic, passphrase, need_resolve)
        self.did_str = str(self.did)
        self.issuer: Issuer = self.did_store.create_issuer(self.did)

    def init_did_from_file(self, file_content: str, passphrase: str) -> (DID, DIDDocument):
        try:
            return self.load_existed_did()
        except HiveException as e:
            logging.info('Entity.init_from_file: try to load DID failed, need load first')
            self.load_did_to_store(file_content, passphrase)
            return self.load_existed_did()

    def load_did_to_store(self, file_content: str, passphrase: str):
        try:
            file_content_str = base58.b58decode(file_content).decode('utf8')
        except Exception as e:
            raise RuntimeError(f'get_verified_owner_did: invalid value of NODE_CREDENTIAL')

        file_path = gene_temp_file_name()
        with open(file_path, 'w') as f:
            f.write(file_content_str)

        try:
            self.did_store.import_did(file_path.as_posix(), passphrase)
        except Exception as ex:
            raise ex
        finally:
            file_path.unlink()

    def load_existed_did(self):
        dids = self.did_store.list_dids()
        if not dids:
            raise BadRequestException(msg='Entity.init_from_file: no did in store')
        return dids[0], self.did_store.load_did(dids[0])

    def init_did_from_mnemonic(self, mnemonic: str, passphrase: str, need_resolve: bool):
        root_identity = self.did_store.get_root_identity(mnemonic, passphrase)
        return self.init_did_by_root_identity(root_identity, need_resolve=need_resolve)

    def init_did_by_root_identity(self, root_identity: RootIdentity, need_resolve=True):
        did, doc = root_identity.get_did_0(), None
        if self.did_store.contains_did(did) and self.did_store.contains_did(did):
            # direct get
            return did, self.did_store.load_did(did)

        if need_resolve:
            # resolve, then get
            root_identity.sync_0()
            return did, self.did_store.load_did(did)

        # create, then get
        doc = root_identity.new_did_0()
        return doc.get_subject(), doc

    def get_did_string(self):
        return self.did_str

    def get_did_store(self):
        return self.did_store.store

    def get_did(self):
        return self.did.did

    def get_document(self):
        return self.doc.doc

    def get_name(self):
        return self.name

    def get_store_password(self):
        return self.storepass

    def create_credential(self, type_, props, owner_did: DID = None):
        did = owner_did if owner_did else self.did
        return self.issuer.create_credential_by_string(did, self.name, type_, props)

    def create_presentation(self, vc, nonce, realm):
        type0 = ffi.new("char[]", "VerifiablePresentation".encode())
        types = ffi.new("char **", type0)
        did_url = lib.DIDURL_NewFromDid(self.did, "jwtvp".encode())
        if not did_url:
            raise BadRequestException(msg=DIDResolver.get_errmsg("create_presentation: can't new did url"))

        vp = lib.Presentation_Create(did_url, self.did, types, 1, nonce.encode(),
                                     realm.encode(), ffi.NULL, self.did_store, self.storepass.encode(), 1, vc)
        if not vp:
            msg = DIDResolver.get_errmsg("create_presentation: can't create presentation")
            lib.DIDURL_Destroy(did_url)
            raise BadRequestException(msg=msg)
        lib.DIDURL_Destroy(did_url)

        c_vp_json = lib.Presentation_ToJson(vp, True)
        if not c_vp_json:
            raise BadRequestException(msg=DIDResolver.get_errmsg("create_presentation: can't convert to json"))

        return ffi.string(c_vp_json).decode()

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

    def get_error_message(self, prompt=None):
        return DIDResolver.get_errmsg(prompt)

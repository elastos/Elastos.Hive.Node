import logging
import json
import os
from datetime import datetime

import base58
import requests

from src.utils_v1.did.eladid import ffi, lib

from src import init_did_backend
from src.utils.http_exception import BadRequestException, HiveException
from src.utils.resolver import DIDResolver
from src.settings import hive_setting
from src.utils_v1.common import gene_temp_file_name
from src.utils_v1.error_code import SUCCESS


class Entity:
    def __init__(self, name, mnemonic=None, passphrase=None, storepass=None, need_resolve=True, from_file=False, file_content=None):
        """
        :param file_content: base58
        """
        self.name = name if name else 'Entity'
        self.passphrase = passphrase if passphrase else "secret"
        self.storepass = storepass if storepass else "password"
        self.did_store = None
        self.did = None
        self.doc = None
        self.did_str = None

        if from_file:
            assert file_content, 'Entity.__init__: file_content must provide.'
            self.init_did_from_file(file_content)
        else:
            assert mnemonic, 'Entity.__init__: mnemonic must provide.'
            self.init_did(mnemonic, need_resolve)

        self.did_str = self.get_did_str_from_doc(self.doc)

    def init_did_from_file(self, file_content):
        store_dir = hive_setting.DID_DATA_STORE_PATH + os.sep + self.name
        self.did_store = lib.DIDStore_Open(store_dir.encode())

        try:
            self.load_existed_did()
        except HiveException as e:
            logging.info('Entity.init_from_file: try to load DID failed, need load first')
            self.load_did_to_store(file_content)
            self.load_existed_did()

    def load_did_to_store(self, file_content):
        if not self.did_store:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init_from_file: can't create store"))

        try:
            file_content_str = base58.b58decode(file_content).decode('utf8')
        except Exception as e:
            raise RuntimeError(f'get_verified_owner_did: invalid value of NODE_CREDENTIAL')

        file_path = gene_temp_file_name()
        with open(file_path, 'w') as f:
            f.write(file_content_str)

        ret_value = lib.DIDStore_ImportDID(self.did_store, self.storepass.encode(), file_path.as_posix().encode(), self.passphrase.encode())
        file_path.unlink()
        if ret_value != 0:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init_from_file: can't import did"))

    def load_existed_did(self):
        @ffi.callback("int(DID *, void *)")
        def did_callback(did, context):
            # INFO: contains a terminating signal by a did with None.
            if did:
                did_str = ffi.new('char[64]')
                did_str = lib.DID_ToString(did, did_str, 64)
                self.did = lib.DID_FromString(did_str)

        # INFO: 1, has private keys
        ret_value = lib.DIDStore_ListDIDs(self.did_store, 1, did_callback, ffi.NULL)
        if ret_value != 0:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init_from_file: can't load did"))

        if not self.did:
            raise BadRequestException(msg="Entity.init_from_file: can't load did from callback")

        self.doc = self.get_doc_from_did(self.did)

    def init_did(self, mnemonic, need_resolve):
        store_dir = hive_setting.DID_DATA_STORE_PATH + os.sep + self.name
        self.did_store = lib.DIDStore_Open(store_dir.encode())
        if not self.did_store:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't create store"))

        root_identity = self.get_root_identity(mnemonic)
        self.did, self.doc = self.init_did_by_root_identity(root_identity, need_resolve=need_resolve)
        lib.RootIdentity_Destroy(root_identity)

    def get_root_identity(self, mnemonic):
        c_id = lib.RootIdentity_CreateId(mnemonic.encode(), self.passphrase.encode())
        if not c_id:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't create root identity id string"))

        if lib.DIDStore_ContainsRootIdentity(self.did_store, c_id) == 1:
            root_identity = lib.DIDStore_LoadRootIdentity(self.did_store, c_id)
            lib.Mnemonic_Free(c_id)
            if not root_identity:
                raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't load root identity"))
            return root_identity
        lib.Mnemonic_Free(c_id)

        root_identity = lib.RootIdentity_Create(mnemonic.encode(),
                                                self.passphrase.encode(),
                                                True, self.did_store, self.storepass.encode())
        if not root_identity:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't create root identity"))
        return root_identity

    def init_did_by_root_identity(self, root_identity, need_resolve=True):
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
            msg = DIDResolver.get_errmsg("Entity.init: can't get doc from created did")
            lib.DIDDocument_Destroy(c_doc)
            raise BadRequestException(msg=msg)
        return c_did, c_doc

    def get_doc_from_did(self, c_did):
        c_doc = lib.DIDStore_LoadDID(self.did_store, c_did)
        if not c_doc:
            raise BadRequestException(msg=DIDResolver.get_errmsg("Entity.init: can't load did doc"))
        return c_doc

    def __del__(self):
        # if self.doc:
        #     lib.DIDDocument_Destroy(self.doc)
        # if self.did:
        #     lib.DID_Destroy(self.did)
        # if self.did_store:
        #     lib.DIDStore_Close(self.did_store)
        pass

    def get_did_str_from_doc(self, doc):
        c_doc_json = lib.DIDDocument_ToJson(doc, True)
        if not c_doc_json:
            raise BadRequestException(msg=DIDResolver.get_errmsg("get_did_str_from_doc: can't get did str from doc"))

        return json.loads(ffi.string(c_doc_json).decode()).get('id')

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

    def issue_auth_vc(self, issuer, type, props, owner):
        type0 = ffi.new("char[]", type.encode())
        types = ffi.new("char **", type0)

        issuerid = self.did
        issuerdoc = self.doc
        expires = lib.DIDDocument_GetExpires(issuerdoc)
        credid = lib.DIDURL_NewFromDid(owner, self.name.encode())
        vc = lib.Issuer_CreateCredentialByString(issuer, owner, credid, types, 1,
                                                 json.dumps(props).encode(), expires, self.storepass.encode())
        lib.DIDURL_Destroy(credid)
        # vcJson = ffi.string(lib.Credential_ToString(vc, True)).decode()
        # logging.debug(f"vcJson: {vcJson}")
        # print(vcJson)
        return vc

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

    def get_error_message(self, prompt=None):
        return DIDResolver.get_errmsg(prompt)

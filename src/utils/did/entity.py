# -*- coding: utf-8 -*-
import logging
import os
import typing

import base58

from src.utils.consts import DID
from src.utils.http_exception import BadRequestException, HiveException
from src.settings import hive_setting
from src.utils_v1.common import gene_temp_file_name
from src.utils.did.did_wrapper import DIDStore, DIDDocument, RootIdentity, Issuer, Credential, JWTBuilder


class Entity:
    def __init__(self, name, mnemonic=None, passphrase=None, storepass=None, need_resolve=True, from_file=False, file_content=None):
        """
        :param file_content: base58
        """
        passphrase, storepass = 'secret' if passphrase is None else passphrase, 'password' if storepass is None else storepass
        self.name = name
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
            ret_val = f.write(file_content_str)
            f.flush()

        try:
            self.did_store.import_did(file_path.as_posix(), passphrase)
        except Exception as ex:
            raise ex
        finally:
            file_path.unlink()

    def load_existed_did(self):
        dids = self.did_store.list_dids()
        if not dids:
            raise BadRequestException('Entity.init_from_file: no did in store')
        return dids[0], self.did_store.load_did(dids[0])

    def init_did_from_mnemonic(self, mnemonic: str, passphrase: str, need_resolve: bool):
        root_identity = self.did_store.get_root_identity(mnemonic, passphrase)
        return self.init_did_by_root_identity(root_identity, need_resolve=need_resolve)

    def init_did_by_root_identity(self, root_identity: RootIdentity, need_resolve=True):
        did, doc = root_identity.get_did_0(), None
        if self.did_store.contains_did(did):
            # direct get
            return did, self.did_store.load_did(did)

        if need_resolve:
            # resolve, then get
            root_identity.sync_0()
            return did, self.did_store.load_did(did)

        # create, then get
        doc = root_identity.new_did_0()
        return doc.get_subject(), doc

    def get_name(self):
        return self.name

    def get_doc(self) -> DIDDocument:
        return self.doc

    def get_did_string(self) -> str:
        return self.did_str

    def create_credential(self, type_, props, owner_did: DID = None) -> Credential:
        did = owner_did if owner_did else self.did
        return self.issuer.create_credential_by_string(did, self.name, type_, props, self.doc.get_expires())

    def create_presentation_str(self, vc: Credential, nonce: str, realm: str) -> str:
        return self.did_store.create_presentation(self.did, 'jwtvp', nonce, realm, vc).to_json()

    def create_vp_token(self, vp_json, subject, hive_did: str, expire: typing.Optional[int]) -> str:
        return self.create_jwt_token(subject, hive_did, expire, 'presentation', vp_json)

    def create_jwt_token(self, subject: str, audience_did_str: str, expire: typing.Optional[int], claim_key: str, claim_value: any, claim_json: bool = True) -> str:
        builder: JWTBuilder = self.did_store.get_jwt_builder(self.doc)
        return builder.create_token(subject, audience_did_str, expire, claim_key, claim_value, claim_json=claim_json)

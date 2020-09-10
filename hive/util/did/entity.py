import logging
import os
import pathlib
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

    def __init__(self, name, mnemonic=None):
        self.name = name
        if not mnemonic is None:
            self.mnemonic = mnemonic
        self.store, self.did, self.doc = init_did(self.mnemonic, self.passphrase, self.storepass, self.name)
        self.storepass = self.storepass.encode()

    def __del__(self):
        pass

    def get_did_string_from_did(self, did):
        method = ffi.string(lib.DID_GetMethod(did)).decode()
        sep_did = ffi.string(lib.DID_GetMethodSpecificId(did)).decode()
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




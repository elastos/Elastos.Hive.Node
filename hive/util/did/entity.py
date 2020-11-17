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




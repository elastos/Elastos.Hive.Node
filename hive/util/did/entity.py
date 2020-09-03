import logging
import os
import pathlib
from eladid import ffi, lib

from hive.settings import DID_SIDECHAIN_URL

resolver = DID_SIDECHAIN_URL.encode()  # 20606
language = "english".encode()
idchain_path = str(pathlib.Path("." + os.sep + "data" + os.sep + "idchain").absolute())
localdids = idchain_path + os.sep + "localdids"


@ffi.def_extern()
def CreateIdTransactionHandle(adapter, payload, memo):
    # print("run CreateIdTransactionHandle")
    # TODO:: need to improve
    return True

@ffi.def_extern()
def MyDIDLocalResovleHandle(did):
    spec_did_str = ffi.string(lib.DID_GetMethodSpecificId(did)).decode()
    doc = ffi.NULL

    file_path = localdids + os.sep + spec_did_str
    is_exist =os.path.exists(file_path)
    if is_exist:
        f = open(file_path, "r")
        try:
            doc_str = f.read()
            doc = lib.DIDDocument_FromJson(doc_str.encode())
        finally:
            f.close()

    return doc

def print_err(fun_name=None):
    err = "Error:: "
    if fun_name:
        err += fun_name + ": "
    logging.debug(f"{err + str(ffi.string(lib.DIDError_GetMessage()), encoding='utf-8')}")


def new_adapter():
    adapter = ffi.new("struct DIDAdapter *")
    adapter.createIdTransaction = lib.CreateIdTransactionHandle
    return adapter


# ---------------
class Entity:
    passphrase = "secret".encode()
    storepass = "password".encode()
    store = None
    doc = None
    did = None
    did_str = None
    name = "Entity"
    mnemonic = "advance duty suspect finish space matter squeeze elephant twenty over stick shield"

    def __init__(self, name, mnemonic=None):
        self.name = name
        if not mnemonic is None:
            self.mnemonic = mnemonic
        logging.debug(f"Entity name: {self.name}")
        self.init_did_store()
        self.init_private_identity()
        self.init_did()

    def __del__(self):
        pass

    def init_did_store(self):
        store_path = idchain_path + os.sep + self.name + os.sep + ".store"
        self.store = lib.DIDStore_Open(store_path.encode(), adapter)
        return self.store

    def init_private_identity(self):
        ret = lib.DIDStore_ContainsPrivateIdentity(self.store)
        # Check the store whether contains the root private identity.
        if ret:
            return  # Already exists

        if self.mnemonic is None:
            mnemonic = lib.Mnemonic_Generate(language)
        else:
            mnemonic = self.mnemonic.encode()
        rc = lib.DIDStore_InitPrivateIdentity(self.store, self.storepass, mnemonic, self.passphrase, language, False)
        if self.mnemonic is None:
            mnemonic_str = str(ffi.string(mnemonic), encoding="utf-8")
            self.mnemonic = mnemonic_str
            lib.Mnemonic_Free(mnemonic)
        logging.debug(f"mnemonic: {self.mnemonic}")

    def check_did_and_sync(self, did):
        if lib.DIDStore_ContainsDID(self.store, did) and lib.DIDSotre_ContainsPrivateKeys(self.store, did):
            self.did = did
            return True, 0
        else:
            lib.DIDStore_DeleteDID(self.store, did)
            ret = lib.DIDStore_Synchronize(self.store, self.storepass, ffi.NULL)
            return False, ret

    def check_did_and_new(self, did):
        if lib.DIDStore_ContainsDID(self.store, did) and lib.DIDSotre_ContainsPrivateKeys(self.store, did):
            self.did = did
        else:
            doc = lib.DIDStore_NewDIDByIndex(self.store, self.storepass, 0, self.name.encode())
            if not doc:
                return False
            self.did = lib.DIDDocument_GetSubject(doc)
            lib.DIDDocument_Destroy(doc)
        return True

    def init_did(self):
        logging.debug(f"init did, please wait ... ...")
        did = lib.DIDStore_GetDIDByIndex(self.store, 0)
        if not did:
            print_err("DIDStore_GetDIDByIndex")
            return

        check, sync = self.check_did_and_sync(did)
        if not check:
            if sync == -1:
                print_err("check_did_and_sync")
                return
            if not self.check_did_and_new(did):
                print_err("check_did_and_new")
                return

        doc = lib.DID_Resolve(did, True)
        if not doc:
            print_err("DID_Resolve")
            return

        ret = lib.DIDStore_StoreDID(self.store, doc)
        if ret == -1:
            print_err("DIDStore_StoreDID")
            return

        self.doc = lib.DIDStore_LoadDID(self.store, self.did)
        if not self.doc:
            print_err("DIDStore_LoadDID")
            return

        # ret = lib.DIDStore_PublishDID(self.store, self.storepass, self.did, ffi.NULL, False)
        # if ret == -1:
        #     print_err("DIDStore_PublishDID")

        self.did_str = self.get_did_string()
        logging.debug(self.did_str)
        return

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


# ---------------
def init_did_backend():
    cache_dir = idchain_path + os.sep + "didcache"
    ret = lib.DIDBackend_InitializeDefault(resolver, cache_dir.encode())
    if ret == -1:
        print_err("DIDBackend_InitializeDefault")

    is_exist =os.path.exists(localdids)
    if not is_exist:
        os.makedirs(localdids)
    lib.DIDBackend_SetLocalResolveHandle(lib.MyDIDLocalResovleHandle)

    return ret


adapter = new_adapter()
init_did_backend()

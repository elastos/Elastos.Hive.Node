
import os
import json
import pathlib
from eladid import ffi, lib

resolver = "http://api.elastos.io:21606".encode() #20606
language = "english".encode()
idchain_path = str(pathlib.Path("." + os.sep + "data" + os.sep +"idchain").absolute())

@ffi.def_extern()
def CreateIdTransactionHandle(adapter, payload, memo):
    # print("run CreateIdTransactionHandle")
    #TODO:: need to improve
    return True

def print_err(fun_name = None):
    err = "Error:: "
    if fun_name != None:
        err += fun_name + ": "
    print(err + str(ffi.string(lib.DIDError_GetMessage()), encoding="utf-8"))

def new_adapter():
    adapter = ffi.new("struct DIDAdapter *")
    adapter.createIdTransaction = lib.CreateIdTransactionHandle
    return adapter

# ---------------
class Entity:
    passphrase = "secret".encode()
    storepass = "password".encode()
    store = None
    did = None
    did_str = None
    name = "Entity"
    mnemonic = "advance duty suspect finish space matter squeeze elephant twenty over stick shield"

    def __init__(self, name, mnemonic = None):
        self.name = name
        # self.mnemonic = mnemonic
        print("Entity name:" + self.name)
        self.init_did_store()
        self.init_private_identity()
        self.init_did()

    def init_did_store(self):
        store_path = idchain_path + os.sep + self.name + os.sep + ".store"
        self.store = lib.DIDStore_Open(store_path.encode(), adapter)
        return self.store

    def init_private_identity(self):
        ret = lib.DIDStore_ContainsPrivateIdentity(self.store)
        #Check the store whether contains the root private identity.
        if (ret):
            return #Already exists

        if self.mnemonic is None:
            mnemonic = lib.Mnemonic_Generate(language)
        else:
            mnemonic = self.mnemonic.encode()
        rc = lib.DIDStore_InitPrivateIdentity(self.store, self.storepass, mnemonic, self.passphrase, language, False)
        if self.mnemonic is None:
            mnemonic_str = str(ffi.string(mnemonic), encoding="utf-8")
            self.mnemonic = mnemonic_str
            lib.Mnemonic_Free(mnemonic)
        print("  mnemonic:" + self.mnemonic)


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
        print("init did, please wait ... ...")
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

        ret = lib.DIDStore_PublishDID(self.store, self.storepass, self.did, ffi.NULL, False)
        if ret == -1:
            print_err("DIDStore_PublishDID")

        self.did_str = self.get_did_string_from_did(self.did)
        print(self.did_str)
        return

    def get_did_string_from_did(self, did):
        didstr = ffi.new("char[" + str(lib.ELA_MAX_DID_LEN) + "]")
        lib.DID_ToString(did, didstr, lib.ELA_MAX_DID_LEN)
        return ffi.string(didstr).decode()

    def get_did_string(self):
        if self.did_str is None:
            self.did_str = self.get_did_string_from_did(self.did)
        return self.did_str

    def get_did_store():
        return self.store

    def get_did():
        return self.did

    def get_document():
        return lib.DIDStore_LoadDID(self.store, self.did)

    def get_name():
        return self.name

    def get_store_password():
        return self.storepass

# ---------------
def init_did_backend():
    cache_dir = idchain_path + os.sep + ".cache"
    ret = lib.DIDBackend_InitializeDefault(resolver, cache_dir.encode())
    return ret

adapter = new_adapter()
init_did_backend()

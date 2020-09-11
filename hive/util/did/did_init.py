import logging
import os
import pathlib
from eladid import ffi, lib

from hive.settings import DID_RESOLVER, DID_MNEMONIC, DID_PASSPHRASE, DID_STOREPASS, HIVE_DATA

resolver = DID_RESOLVER.encode()  # 20606
language = "english".encode()

did_data_path = HIVE_DATA + os.sep + "did" + os.sep
localdids = did_data_path + "localdids"
store_path = did_data_path + "store"
cache_path = did_data_path + "cache"

def new_adapter():
    adapter = ffi.new("struct DIDAdapter *")
    adapter.createIdTransaction = lib.CreateIdTransactionHandle
    return adapter

adapter = new_adapter()

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

def init_did_store():
    store = lib.DIDStore_Open(store_path.encode(), adapter)
    return store

def init_private_identity(store, mnemonic, storepass, passphrase):
    ret = lib.DIDStore_ContainsPrivateIdentity(store)
    # Check the store whether contains the root private identity.
    if ret:
        return  # Already exists

    if mnemonic is None:
        mnemonic = lib.Mnemonic_Generate(language)
    ret = lib.DIDStore_InitPrivateIdentity(store, storepass, mnemonic, passphrase, language, False)
    if ret == -1:
        print_err("DIDStore_InitPrivateIdentity")

def get_did(store):
    did = lib.DIDStore_GetDIDByIndex(store, 0)
    if not did:
        print_err("DIDStore_GetDIDByIndex")
    return did

def load_did(store, did):
    doc = lib.DIDStore_LoadDID(store, did)
    if not doc:
        print_err("DIDStore_LoadDID")
    return doc

def check_did_and_sync(store, did, storepass):
    if lib.DIDStore_ContainsDID(store, did) and lib.DIDSotre_ContainsPrivateKeys(store, did):
        return True, 0
    else:
        lib.DIDStore_DeleteDID(store, did)
        ret = lib.DIDStore_Synchronize(store, storepass, ffi.NULL)
        return False, ret

def check_did_and_new(store, did, storepass, name):
    if not lib.DIDStore_ContainsDID(store, did) and lib.DIDSotre_ContainsPrivateKeys(store, did):
        doc = lib.DIDStore_NewDIDByIndex(store, storepass, 0, name.encode())
        if not doc:
            return False
        # did = lib.DIDDocument_GetSubject(doc)
        lib.DIDDocument_Destroy(doc)
    return True

def sync_did(store, did, storepass, name):
    logging.debug(f"init did, please wait ... ...")

    check, sync = check_did_and_sync(store, did, storepass)
    if not check:
        if sync == -1:
            print_err("check_did_and_sync")
            return False
        if not check_did_and_new(store, did, storepass, name):
            print_err("check_did_and_new")
            return False

    # ret = lib.DIDStore_PublishDID(store, storepass, did, ffi.NULL, False)
    # if ret == -1:
    #     print_err("DIDStore_PublishDID")

    doc = lib.DID_Resolve(did, True)
    if not doc:
        print_err("DID_Resolve")
        return False

    ret = lib.DIDStore_StoreDID(store, doc)
    if ret == -1:
        print_err("DIDStore_StoreDID")
        return False
    return True

def init_did(mnemonic, passphrase, storepass, name):
    mnemonic = mnemonic.encode()
    passphrase = passphrase.encode()
    storepass = storepass.encode()
    store = init_did_store()
    if not store:
        print_err("init_did_store")
        return None, None, None

    init_private_identity(store, mnemonic, storepass, passphrase)
    did = get_did(store)
    if not did:
        print_err("get_did")
        return None, None, None

    doc = load_did(store, did)
    if not doc:
        ret = sync_did(store, did, storepass, name)
        if ret:
            doc = load_did(store, did)
            if not doc:
                print_err("load_did")
                return None, None, None
        else:
            print_err("load_did")
            return None, None, None
    return store, did, doc

def init_did_backend():
    ret = lib.DIDBackend_InitializeDefault(resolver, cache_path.encode())
    if ret == -1:
        print_err("DIDBackend_InitializeDefault")

    is_exist =os.path.exists(localdids)
    if not is_exist:
        os.makedirs(localdids)
    lib.DIDBackend_SetLocalResolveHandle(lib.MyDIDLocalResovleHandle)

    return ret

init_did_backend()
# init_did(DID_MNEMONIC, DID_PASSPHRASE, DID_STOREPASS)

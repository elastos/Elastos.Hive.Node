import logging
import os
from src.utils.did.eladid import ffi, lib

from hive.settings import hive_setting

@ffi.def_extern()
def MyDIDLocalResovleHandle(did):
    spec_did_str = ffi.string(lib.DID_GetMethodSpecificId(did)).decode()
    doc = ffi.NULL

    file_path = hive_setting.DID_DATA_LOCAL_DIDS + os.sep + spec_did_str
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
    error_msg = lib.DIDError_GetLastErrorMessage()
    msg = str(ffi.string(error_msg), encoding='utf-8') if error_msg else 'Unknown DID error.'
    logging.error(f"{err + msg}")

def get_error_message():
    error_msg = lib.DIDError_GetLastErrorMessage()
    if not error_msg:
        return 'Unknown DID error.'
    return str(ffi.string(error_msg), encoding='utf-8')


def init_did_store(name):
    if name is None:
        return ffi.NULL

    store_dir = hive_setting.DID_DATA_STORE_PATH + os.sep + name
    store = lib.DIDStore_Open(store_dir.encode())
    return store

def init_rootidentity(store, mnemonic, storepass, passphrase):
    if (not store) or (not storepass) or (mnemonic is None):
        return

    id = lib.RootIdentity_CreateId(mnemonic, passphrase)
    assert(id is not None)

    if lib.DIDStore_ContainsRootIdentity(store, id) == 1:
        identity = lib.DIDStore_LoadRootIdentity(store, id)
        if identity:
            return identity

    identity = lib.RootIdentity_Create(mnemonic, passphrase, True, store, storepass)
    assert(identity is not None)
    return identity

def get_did(identity):
    if (not identity):
        return ffi.NULL

    did = lib.RootIdentity_GetDIDByIndex(identity, 0)
    if not did:
        print_err("DIDStore_GetDIDByIndex")

    return did

def check_did(store, did):
    if lib.DIDStore_ContainsDID(store, did) == 1 and lib.DIDStore_ContainsPrivateKeys(store, did) == 1:
        doc = lib.DIDStore_LoadDID(store, did)
        if doc:
            return doc

    return ffi.NULL

def resolve_did(store, did, identity):
    status = ffi.new("DIDStatus *")
    doc = lib.DID_Resolve(did, status, True)
    assert doc, get_error_message()

    lib.DIDDocument_Destroy(doc)

    ret = lib.RootIdentity_SynchronizeByIndex(identity, 0, ffi.NULL)
    doc = lib.DIDStore_LoadDID(store, did)
    assert doc, get_error_message()
    return doc

def destroy_identity(identity):
    lib.RootIdentity_Destroy(identity)

def init_did(mnemonic, passphrase, storepass, name, need_resolve=True):
    assert(mnemonic is not None)
    assert(passphrase is not None)
    assert(storepass is not None)
    assert(name is not None)

    passphrase = passphrase.encode()
    storepass = storepass.encode()
    mnemonic = mnemonic.encode()
    store = init_did_store(name)
    assert store, get_error_message()

    identity = init_rootidentity(store, mnemonic, storepass, passphrase)
    assert identity, get_error_message()

    did = get_did(identity)
    assert did, get_error_message()

    doc = check_did(store, did)
    if doc:
        destroy_identity(identity)
        return store, did, doc

    if need_resolve:
        doc = resolve_did(store, did, identity)
    else:
        doc = lib.RootIdentity_NewDIDByIndex(identity, 0, storepass, ffi.NULL, True)
    destroy_identity(identity)

    return store, did, doc

def init_did_backend():
    print("Initializing the [Auth] module")
    print("    DID Resolver: " + hive_setting.EID_RESOLVER_URL)

    ret = lib.DIDBackend_InitializeDefault(ffi.NULL, hive_setting.EID_RESOLVER_URL.encode(), hive_setting.DID_DATA_CACHE_PATH.encode())
    if ret == -1:
        print_err("DIDBackend_InitializeDefault")

    is_exist =os.path.exists(hive_setting.DID_DATA_LOCAL_DIDS)
    if not is_exist:
        os.makedirs(hive_setting.DID_DATA_LOCAL_DIDS)
    lib.DIDBackend_SetLocalResolveHandle(lib.MyDIDLocalResovleHandle)

    return ret

# init_did(hive_setting.DID_MNEMONIC, hive_setting.DID_PASSPHRASE, hive_setting.DID_STOREPASS)

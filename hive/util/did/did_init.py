import logging
import os
import pathlib
from hive.util.did.eladid import ffi, lib

from hive.settings import hive_setting


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
    logging.error(f"{err + str(ffi.string(lib.DIDError_GetMessage()), encoding='utf-8')}")

def get_error_message():
    return str(ffi.string(lib.DIDError_GetMessage()), encoding='utf-8')


def init_did_store(name):
    if name is None:
        return ffi.NULL

    store_dir = hive_setting.DID_DATA_STORE_PATH + os.sep + name
    store = lib.DIDStore_Open(store_dir.encode(), adapter)
    return store

def export_current_mnemonic(store, storepass):
    if (not store) or (not storepass):
        return ffi.NULL

    mnemonic_str = ffi.new("char[" + str(lib.ELA_MAX_MNEMONIC_LEN + 1) + "]")
    lib.DIDStore_ExportMnemonic(store, storepass, mnemonic_str, lib.ELA_MAX_MNEMONIC_LEN + 1)
    return ffi.string(mnemonic_str).decode()

def init_private_identity(store, mnemonic, storepass, passphrase):
    if (not store) or (not storepass) or (mnemonic is None):
        return

    ret = lib.DIDStore_ContainsPrivateIdentity(store)
    # Check the store whether contains the root private identity.
    if ret:
        cur_mnemonic = export_current_mnemonic(store, storepass)
        if cur_mnemonic == mnemonic:
            return  # Already exists

    mnemonic = mnemonic.encode()
    if not mnemonic:
        mnemonic = lib.Mnemonic_Generate(hive_setting.LANGUAGE.encode())
    ret = lib.DIDStore_InitPrivateIdentity(store, storepass, mnemonic, passphrase, hive_setting.LANGUAGE.encode(), True)
    if ret == -1:
        print_err("DIDStore_InitPrivateIdentity")

def get_did(store):
    if (not store):
        return ffi.NULL

    did = lib.DIDStore_GetDIDByIndex(store, 0)
    if not did:
        print_err("DIDStore_GetDIDByIndex")
    return did

def load_did(store, did):
    if (not store) or (not did):
        return ffi.NULL

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
    assert(mnemonic is not None)
    assert(passphrase is not None)
    assert(storepass is not None)
    assert(name is not None)

    passphrase = passphrase.encode()
    storepass = storepass.encode()
    store = init_did_store(name)
    assert store, get_error_message()

    init_private_identity(store, mnemonic, storepass, passphrase)
    did = get_did(store)
    assert did, get_error_message()

    doc = load_did(store, did)
    if not doc:
        ret = sync_did(store, did, storepass, name)
        assert ret, get_error_message()
        doc = load_did(store, did)
        assert doc, get_error_message()

    return store, did, doc

def init_did_backend():
    print("Initializing the [Auth] module")
    print("    DID Resolver: " + hive_setting.DID_RESOLVER)
    print("    DID Mnemonic: " + hive_setting.DID_MNEMONIC)

    assert hive_setting.DID_RESOLVER in [
        'http://api.elastos.io:20606',
        'http://api.elastos.io:21606',
        'https://api-testnet.elastos.io/did',
    ], "resolver is invalid!"

    ret = lib.DIDBackend_InitializeDefault(hive_setting.DID_RESOLVER.encode(), hive_setting.DID_DATA_CACHE_PATH.encode())
    if ret == -1:
        print_err("DIDBackend_InitializeDefault")

    is_exist =os.path.exists(hive_setting.DID_DATA_LOCAL_DIDS)
    if not is_exist:
        os.makedirs(hive_setting.DID_DATA_LOCAL_DIDS)
    lib.DIDBackend_SetLocalResolveHandle(lib.MyDIDLocalResovleHandle)

    return ret

# init_did(hive_setting.DID_MNEMONIC, hive_setting.DID_PASSPHRASE, hive_setting.DID_STOREPASS)

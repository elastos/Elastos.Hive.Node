import pathlib
from ctypes import c_long

import base58
from .ela_did import ffi, lib
import os

resolver = "http://api.elastos.io:21606"
did_str = "did:elastos:iWFAUYhTa35c1fPe3iCJvihZHx6quumnym"
walletId = "cywallet"
network = "TestNet"
walletpass = "12345678"
storepass = "123456"
passphase = ""
default_type = "ECDSAsecp256r1"
service_type = "CarrierAddress"
mnemonic = "cloth always junk crash fun exist stumble shift over benefit fun toe"
language = "english"
test_resources_path = "./etc/did/resources/testdata"
SIGNATURE_BYTES = 64


@ffi.def_extern()
def py_resolve(resolver, did, all):
    print("in py_resolve")


@ffi.def_extern()
def py_create_id_transaction(adapter, payload, memo):
    print("in py_createIdTransaction")


def setup_did_store():
    store_path = pathlib.Path().absolute() / "idchain"
    adapter = ffi.new("struct DIDAdapter *")
    adapter.createIdTransaction = lib.py_create_id_transaction
    did_store = lib.DIDStore_Open(store_path.as_posix().encode(), adapter)
    print("did_store ctype" + str(type(did_store)))
    return did_store


def load_resources_file(file_name):
    this_dir = pathlib.Path().absolute()
    h_file_name = this_dir / test_resources_path / file_name
    return h_file_name


def store_document(did_store, file_name, alias):
    h_file_name = load_resources_file(file_name)
    with open(h_file_name) as h_file:
        doc_json = h_file.read()
        doc = lib.DIDDocument_FromJson(doc_json.encode())
        ret = lib.DIDStore_StoreDID(did_store, doc, alias.encode())
        if -1 == ret:
            lib.DIDDocument_Destroy(doc)
        else:
            return doc


def store_private_key(did_store, store_pass, subject, key_name, key_file_name):
    h_file_name = load_resources_file(key_file_name)
    with open(h_file_name) as h_file:
        s = h_file.read()
        private_key = base58.b58decode(s)
        did_url = lib.DIDURL_NewByDid(subject, key_name.encode())
        did = lib.DIDURL_GetDid(did_url)
        rt = lib.DIDStore_StorePrivateKey(did_store, store_pass.encode(), did, did_url, private_key)
        lib.DIDURL_Destroy(did_url)
        return rt


def init_test_did_store():
    did_store = setup_did_store()
    doc = store_document(did_store, "document.json", "hive doc test")
    ret = lib.DIDStore_ContainsPrivateIdentity(did_store)
    print("did_store ret" + str(type(ret)))
    if ret == 0:
        subject = lib.DIDDocument_GetSubject(doc)
        rt = store_private_key(did_store, storepass, subject, "primary", "document.primary.sk")
        if rt == -1:
            print("store_private_key failed")
            exit(rt)
        rt = store_private_key(did_store, storepass, subject, "key2", "document.key2.sk")
        if rt == -1:
            print("store_private_key failed")
            exit(rt)
        rt = store_private_key(did_store, storepass, subject, "key3", "document.key3.sk")
        if rt == -1:
            print("store_private_key failed")
            exit(rt)

    return did_store, doc


# ---------------

def setup_did_backend():
    env_dist = os.environ
    cachedir = env_dist["HOME"] + "/.cache.did.elastos"
    resolver_ffi = ffi.new("char[]", resolver.encode())
    cachedir_ffi = ffi.new("char[]", cachedir.encode())
    ret = lib.DIDBackend_InitializeDefault(resolver_ffi, cachedir_ffi)
    return ret


def is_did_resolve(did_str):
    did = lib.DID_FromString(did_str.encode())
    if did is None:
        return False
    doc = lib.DID_Resolve(did, True)
    if doc is None:
        return False
    else:
        return True


def did_verify(did_str, sig, key_name, msg):
    did = lib.DID_FromString(did_str.encode())
    if did is None:
        return False

    doc = lib.DID_Resolve(did, True)
    if doc is None:
        return False

    did_url = lib.DIDURL_NewByDid(did, key_name.encode())
    sig_in = ffi.new("char[" + str(SIGNATURE_BYTES * 2) + "]", sig.encode(encoding="utf-8"))
    msg_in = ffi.new("char[]", msg.encode())
    msg_len = ffi.cast("int", len(msg_in))
    rt = lib.DIDDocument_Verify(doc, did_url, sig_in, 1, msg_in, msg_len)
    if 0 == rt:
        return True
    else:
        return False


def did_sign(did_str, doc, storepass, key_name, msg):
    did = lib.DID_FromString(did_str.encode())
    if did is None:
        return None

    did_url = lib.DIDURL_NewByDid(did, key_name.encode())
    sig = ffi.new("char[" + str(SIGNATURE_BYTES * 2) + "]")
    msg_in = ffi.new("char[]", msg.encode())
    msg_len = ffi.cast("int", len(msg_in))
    rt = lib.DIDDocument_Sign(doc, did_url, storepass.encode(), sig, 1, msg_in, msg_len)
    if 0 != rt:
        return None
    return ffi.string(sig)

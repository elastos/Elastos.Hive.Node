import logging
import os
from src.utils_v1.did.eladid import ffi, lib

from src.settings import hive_setting

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
    msg = ffi.string(error_msg).decode() if error_msg else 'Unknown DID error.'
    logging.error(f"{err + msg}")

def get_error_message():
    error_msg = lib.DIDError_GetLastErrorMessage()
    return ffi.string(error_msg).decode() if error_msg else 'Unknown DID error.'


def init_did_backend():
    logging.getLogger('did_init').info("Initializing the DID backend")
    logging.getLogger('did_init').info("    DID Resolver: " + hive_setting.EID_RESOLVER_URL)
    logging.getLogger('did_init').info("    DID Mnemonic: " + hive_setting.DID_MNEMONIC)

    ret = lib.DIDBackend_InitializeDefault(ffi.NULL, hive_setting.EID_RESOLVER_URL.encode(), hive_setting.DID_DATA_CACHE_PATH.encode())
    if ret == -1:
        print_err("DIDBackend_InitializeDefault")

    is_exist = os.path.exists(hive_setting.DID_DATA_LOCAL_DIDS)
    if not is_exist:
        os.makedirs(hive_setting.DID_DATA_LOCAL_DIDS)
    lib.DIDBackend_SetLocalResolveHandle(lib.MyDIDLocalResovleHandle)

    return ret

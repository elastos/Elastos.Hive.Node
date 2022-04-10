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

import logging
import os
from src.utils_v1.did.eladid import ffi, lib

from src.settings import hive_setting
from src.utils.http_exception import ElaDIDException
from src.utils_v1.did.did_wrapper import ElaError, DID, DIDDocument


@ffi.def_extern()
def MyDIDLocalResovleHandle(did):
    """
    # type: DID* -> DIDDocument*
    """
    spec_str = DID(did).get_method_specific_id()
    file_path = hive_setting.DID_DATA_LOCAL_DIDS + os.sep + spec_str
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            try:
                return DIDDocument.from_json(f.read()).doc
            except Exception as ex:
                logging.error(f'failed to read did file: {file_path}')
                return ffi.NULL


def init_did_backend() -> None:
    resolver_url, cache_path, dids_path = hive_setting.EID_RESOLVER_URL, hive_setting.DID_DATA_CACHE_PATH, hive_setting.DID_DATA_LOCAL_DIDS
    logging.getLogger('did_wrapper').info("Initializing the V2 DID backend")
    logging.getLogger('did_wrapper').info("    DID Resolver: " + resolver_url)

    ret = lib.DIDBackend_InitializeDefault(ffi.NULL, resolver_url.encode(), cache_path.encode())
    if ret != 0:
        raise ElaDIDException(ElaError.get('init_did_backend: '))

    os.makedirs(dids_path, exist_ok=True)
    lib.DIDBackend_SetLocalResolveHandle(lib.MyDIDLocalResovleHandle)

import inspect

from src.utils_v1.did.eladid import ffi, lib
from src.utils.http_exception import ElaDIDException

"""
The wrapper for eladid.so

1. Replace lib.Mnemonic_Free() with lib.free() when lib.free() is ready.
"""


class ElaError:
    @staticmethod
    def get(prompt=None):
        """ helper method to get error message from did.so """
        error_msg, c_msg = 'UNKNOWN ERROR', lib.DIDError_GetLastErrorMessage()
        if c_msg:
            error_msg = ffi.string(c_msg).decode()
        return error_msg if not prompt else f'{prompt}: {error_msg}'

    @staticmethod
    def get_from_method(prompt=None):
        ppt = ': ' + prompt if prompt else ''
        frame = inspect.stack()[1]
        self = frame.frame.f_locals['self']
        cls_name = self.__class__.name
        mtd_name = frame[3]
        return ElaError.get(f'{cls_name}.{mtd_name}{ppt}')


class JwtBuilder:
    def __init__(self, builder):
        self.builder = builder


class Credential:
    def __init__(self, vc):
        self.vc = vc

    @staticmethod
    def from_json(vc_json: str) -> 'Credential':
        # INFO: second NULL means owner is NULL
        vc = lib.Credential_FromJson(vc_json.encode(), ffi.NULL)
        if not vc:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(vc, lib.Credential_Destroy)
        return Credential(vc)

    def is_valid(self) -> bool:
        return lib.Credential_IsValid(self.vc) == 1

    def get_expiration_date(self) -> int:
        expire_date = lib.Credential_GetExpirationDate(self.vc)
        if expire_date == 0:
            raise ElaDIDException(ElaError.get_from_method())
        return expire_date

    def to_json(self):
        # INFO: param 2: normalized
        vc_json = lib.Credential_ToJson(self.vc, True)
        if not vc_json:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(vc_json, lib.Mnemonic_Free)
        return ffi.string(lib.DID_GetMethod(vc_json)).decode()


class DID:
    def __init__(self, did):
        self.did = did

    @staticmethod
    def from_string(did_str: str):
        d = lib.DID_FromString(did_str.encode())
        if not d:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(lib.DID_Destroy)
        return DID(d)

    def get_method(self):
        """ Get third part of the did string. """
        return ffi.string(lib.DID_GetMethod(self.did)).decode()

    def get_method_specific_id(self):
        """ Get third part of the did string. """
        return ffi.string(lib.DID_GetMethodSpecificId(self.did)).decode()

    def resolve(self, force=True):
        """
        :param force: only get from chain if True, else get from cache first.
        """
        status = ffi.new("DIDStatus *")
        doc = lib.DID_Resolve(self.did, status, force)
        if not doc:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(doc, lib.DIDDocument_Destroy)
        return DIDDocument(doc)

    def __str__(self):
        did_str = ffi.new('char[64]')
        did_str = lib.DID_ToString(self.did, did_str, 64)
        return ffi.string(did_str).decode()


class DIDDocument:
    def __init__(self, doc):
        self.doc = doc

    @staticmethod
    def from_json(doc_str: str) -> 'DIDDocument':
        doc = lib.DIDDocument_FromJson(doc_str.encode())
        if not doc:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(doc, lib.DIDDocument_Destroy)
        return DIDDocument(doc)

    def to_json(self) -> str:
        doc_str = lib.DIDDocument_ToJson(self.doc)
        if not doc_str:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(doc_str, lib.Mnemonic_Free)
        return ffi.string(doc_str).decode()

    def is_valid(self) -> bool:
        valid = lib.DIDDocument_IsValid(self.doc)
        if valid < 0:
            raise ElaDIDException(ElaError.get_from_method())
        return valid == 1

    def get_subject(self) -> DID:
        did = lib.DIDDocument_GetSubject(self.doc)
        if not did:
            raise ElaDIDException(ElaError.get_from_method())
        return DID(did)

    def get_credential(self, did: DID, fragment: str) -> Credential:
        did_url = lib.DIDURL_NewFromDid(did.did, fragment.encode())
        if not did_url:
            raise ElaDIDException(ElaError.get_from_method('Can not create did url'))
        ffi.release(did_url, lib.DIDURL_Destroy)

        vc = lib.DIDDocument_GetCredential(self.doc, did_url)
        if not vc:
            raise ElaDIDException(ElaError.get_from_method('Can not get credential'))

        return Credential(vc)

    def get_jwt_builder(self) -> JwtBuilder:
        builder = lib.DIDDocument_GetJwtBuilder(self.doc)
        if not builder:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(builder, lib.JWTBuilder_Destroy)
        return JwtBuilder(builder)

    def get_expires(self) -> int:
        expire = lib.DIDDocument_GetExpires(self.doc)
        if expire == 0:
            raise ElaDIDException(ElaError.get_from_method())
        return expire


class RootIdentity:
    def __init__(self, store, identity):
        self.store = store
        self.identity = identity

    def get_did_by_index(self, index: int) -> DID:
        did = lib.RootIdentity_GetDIDByIndex(self.identity, index)
        if not did:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(did, lib.DID_Destroy)
        return DID(did)

    def get_did_0(self) -> DID:
        return self.get_did_by_index(0)

    def sync_by_index(self, index) -> None:
        # INFO: third NULL means local replace chain.
        success = lib.RootIdentity_SynchronizeByIndex(self.identity, index, ffi.NULL)
        if not success:
            raise ElaDIDException(ElaError.get_from_method())

    def sync_0(self) -> None:
        self.sync_by_index(0)

    def new_did_by_index(self, index) -> DIDDocument:
        # INFO: forth True means override local
        doc = lib.RootIdentity_NewDIDByIndex(self.identity, index, self.store.storepass, ffi.NULL, True)
        if not doc:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(doc, lib.DIDDocument_Destroy)
        return DIDDocument(doc)

    def new_did_0(self) -> DIDDocument:
        return self.new_did_by_index(0)


class DIDStore:
    def __init__(self, dir_path: str, storepass: str):
        self.store = self._init(dir_path)
        self.storepass = storepass.encode

    def _init(self, dir_path: str):
        store = lib.DIDStore_Open(dir_path.encode())
        if not store:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(store, lib.DIDStore_Close)
        return store

    def load_did(self, did: DID):
        doc = lib.DIDStore_LoadDID(did)
        if not doc:
            raise ElaDIDException(ElaError.get_from_method())
        ffi.release(doc, lib.DIDDocument_Destroy)
        return DIDDocument(doc)

    def import_did(self, file_path: str, passphrase: str):
        ret_val = lib.DIDStore_ImportDID(self.store, self.storepass, file_path.encode(), passphrase.encode())
        if ret_val != 0:
            raise ElaDIDException(ElaError.get_from_method())

    def list_dids(self):
        dids = []

        @ffi.callback("int(DID *, void *)")
        def did_callback(did, context):
            # INFO: contains a terminating signal by a did with None.
            if did:
                did_str = ffi.new('char[64]')
                did_str = lib.DID_ToString(did, did_str, 64)
                d = lib.DID_FromString(did_str)
                ffi.release(d, lib.DID_Destroy)
                dids.append(DID(d))

        filter_has_private_keys = 1
        ret_value = lib.DIDStore_ListDIDs(self.store, filter_has_private_keys, did_callback, ffi.NULL)
        if ret_value != 0:
            raise ElaDIDException(ElaError.get_from_method())

        return dids

    def get_root_identity(self, mnemonic: str, passphrase: str):
        c_id = lib.RootIdentity_CreateId(mnemonic.encode(), passphrase.encode())
        if not c_id:
            raise ElaDIDException(ElaError.get_from_method('Can not create the id of root identity'))
        ffi.release(c_id, lib.Mnemonic_Free)

        if lib.DIDStore_ContainsRootIdentity(self.store, c_id) == 1:
            root_identity = lib.DIDStore_LoadRootIdentity(self.store, c_id)
            if not root_identity:
                raise ElaDIDException(ElaError.get_from_method('Can not load root identity'))
            return RootIdentity(self, root_identity)

        root_identity = lib.RootIdentity_Create(mnemonic.encode(), passphrase.encode(), True, self.store, self.storepass)
        if not root_identity:
            raise ElaDIDException(ElaError.get_from_method('Can not create root identity'))
        return RootIdentity(self, root_identity)

    def contains_did(self, did: DID):
        return lib.DIDStore_ContainsDID(self.store, did.did)

    def contains_private_key(self, did: DID):
        return lib.DIDStore_ContainsPrivateKey(self.store, did.did) == 1

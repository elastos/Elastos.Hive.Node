import json
import typing
import typing as t
from datetime import datetime
from enum import Enum

from .eladid import lib, ffi


# used to free malloc memory.
_DEFAULT_MEMORY_FREE_NAME = 'DID_FreeMemory'


class ElaDIDException(Exception):
    def __init__(self, msg, internal_code=-1):
        super().__init__(self)
        self.msg = msg
        self.icode = internal_code

    def __str__(self):
        return f'DID Exception: {self.msg}, ({self.icode})'


class ElaDIDDIDDeactivatedException(ElaDIDException):
    def __init__(self, msg):
        super().__init__(msg, 1002)


class ElaDIDDIDNotFoundException(ElaDIDException):
    def __init__(self, msg):
        super().__init__(msg, 1003)


class ElaError:
    @staticmethod
    def get(prompt=None):
        """ helper method to get error message from eladid.so """
        error_msg, c_msg = 'UNKNOWN ERROR', lib.DIDError_GetLastErrorMessage()
        if c_msg:
            error_msg = ffi.string(c_msg).decode()
        return error_msg if not prompt else f'{prompt}: {error_msg}'


def _get_gc_obj(src, release_name=None):
    # release_name = None
    return ffi.gc(src, getattr(lib, release_name)) if release_name else src


def _int_call(name, *args, fail_val: t.Optional[int] = -1):
    """
    Call the function in .so with original *args, return -1 means error occurred.
    :param name: function name
    :param args: function args
    :param fail_val: the value means error occurred.
    :return: int value
    """
    result = getattr(lib, name)(*args)
    if fail_val is not None and result == fail_val:
        raise ElaDIDException(ElaError.get(name))
    return result


def _float_call(name, *args):
    """ can not check float value for error """
    return getattr(lib, name)(*args)


def _str_call(name, *args, release_name=None):
    result = getattr(lib, name)(*args)
    if not result:
        raise ElaDIDException(ElaError.get(name))
    return ffi.string(_get_gc_obj(result, release_name=release_name)).decode()


def _bool_call(name, *args, fail_val: t.Optional[bool] = False):
    result = getattr(lib, name)(*args)
    if fail_val is not None and not result:
        # result may be 0 or False.
        raise ElaDIDException(ElaError.get(name))
    return result


def _void_call(name, *args):
    getattr(lib, name)(*args)


def _obj_call(name, *args, release_name=None):
    result = getattr(lib, name)(*args)
    if not result:
        raise ElaDIDException(ElaError.get(name))
    return _get_gc_obj(result, release_name=release_name)


def _c_array_to_list(array, size):
    # TODO: need keep the objects in the array.
    return [ffi.gc(array[i]) for i in range(size)]


class DID:
    def __init__(self, did):
        self.did = did

    @staticmethod
    def create_from_str(did_str: str) -> 'DID':
        return DID(_obj_call('DID_FromString', did_str.encode(), release_name='DID_Destroy'))

    @staticmethod
    def create_from_method(method: t.Optional[str], method_specific_str: str) -> 'DID':
        if method is not None:
            did = _obj_call('DID_NewWithMethod', method.encode(), method_specific_str.encode(), release_name='DID_Destroy')
        else:
            did = _obj_call('DID_New', method_specific_str.encode(), release_name='DID_Destroy')
        return DID(did)

    def get_method(self) -> str:
        """ Get third part of the did string. """
        return _str_call('DID_GetMethod', self.did)

    def get_method_specific_id(self) -> str:
        """ Get third part of the did string. """
        return _str_call('DID_GetMethodSpecificId', self.did)

    def is_deactivated(self):
        return _int_call('DID_IsDeactivated', self.did) == 1

    def resolve(self, force=True) -> 'DIDDocument':
        """
        :param force: only get from chain if True, else get from cache first.
        """
        status = ffi.new("DIDStatus *")
        try:
            return DIDDocument(_obj_call('DID_Resolve', self.did, status, force, release_name='DIDDocument_Destroy'))
        except ElaDIDException as e:
            if status == lib.DIDStatus_Deactivated:
                raise ElaDIDDIDDeactivatedException(e.msg)
            elif status == lib.DIDStatus_NotFound:
                raise ElaDIDDIDNotFoundException(e.msg)
            else:
                raise e

    def resolve_biography(self) -> 'DIDBiography':
        return DIDBiography(_obj_call('DID_ResolveBiography', self.did, release_name='DIDBiography_Destroy'))

    def get_metadata(self) -> 'DIDMetadata':
        return DIDMetadata(_obj_call('DID_GetMetadata', self.did))

    def __str__(self):
        did_str = ffi.new(f'char[{lib.ELA_MAX_DID_LEN}]')
        return _str_call('DID_ToString', self.did, did_str, lib.ELA_MAX_DID_LEN)

    def __eq__(self, other: 'DID'):
        return _int_call('DID_Equals', self.did, other.did) == 1

    def __gt__(self, other: 'DID') -> bool:
        return _int_call('DID_Compare', self.did, other.did) > 0

    def __lt__(self, other: 'DID'):
        return _int_call('DID_Compare', self.did, other.did) < 0

    def __ge__(self, other: 'DID'):
        return _int_call('DID_Compare', self.did, other.did) >= 0

    def __le__(self, other: 'DID'):
        return _int_call('DID_Compare', self.did, other.did) <= 0


class DIDMetadata:
    def __init__(self, metadata):
        self.metadata = metadata

    def get_alias(self):
        return _str_call('DIDMetadata_GetAlias', self.metadata)

    def get_deactivated(self) -> bool:
        return _int_call('DIDMetadata_GetDeactivated', self.metadata) == 1

    def get_published(self) -> int:
        return _int_call('DIDMetadata_GetPublished', self.metadata, fail_val=0)

    def set_alias(self, alias: str):
        _int_call('DIDMetadata_SetAlias', self.metadata, alias.encode())

    def set_extra(self, key: str, value: t.Any):
        if isinstance(value, str):
            _int_call('DIDMetadata_SetExtra', self.metadata, key.encode(), value.encode())
        elif isinstance(value, bool):
            _int_call('DIDMetadata_SetExtraWithBoolean', self.metadata, key.encode(), value)
        elif type(value) in (int, float):
            _int_call('DIDMetadata_SetExtraWithDouble', self.metadata, key.encode(), float(value))
        else:
            raise ElaDIDException(f'DIDMetadata.set_extra: Unsupported value type: {type(value)}')

    def get_extra(self, key: str) -> str:
        return _str_call('DIDMetadata_GetExtra', self.metadata, key.encode())

    def get_extra_bool(self, key: str, def_value: bool) -> bool:
        return _bool_call('DIDMetadata_GetExtraAsBoolean', key.encode(), def_value, fail_val=None)

    def get_extra_float(self, key: str, def_value: float) -> float:
        return _float_call('DIDMetadata_GetExtraAsDouble', self.metadata, key.encode(), def_value)

    def get_extra_int(self, key: str, def_value: int) -> int:
        return _int_call('DIDMetadata_GetExtraAsInteger', self.metadata, key.encode(), def_value, fail_val=None)


class DIDURL:
    def __init__(self, url):
        self.url = url

    @staticmethod
    def create_from_str(id_str: str, context: 'DID') -> 'DIDURL':
        return DIDURL(_obj_call('DIDURL_FromString', id_str.encode(), context.did, release_name='DIDURL_Destroy'))

    @staticmethod
    def create(method_specific: str, fragment: str) -> 'DIDURL':
        return DIDURL(_obj_call('DIDURL_New', method_specific.encode(), fragment.encode(), release_name='DIDURL_Destroy'))

    @staticmethod
    def create_from_did(did: 'DID', fragment: str) -> 'DIDURL':
        return DIDURL(_obj_call('DIDURL_NewFromDid', did.did, fragment.encode(), release_name='DIDURL_Destroy'))

    def get_did(self) -> 'DID':
        return DID(_obj_call('DIDURL_GetDid', self.url))

    def get_fragment(self) -> str:
        return _str_call('DIDURL_GetFragment', self.url)

    def get_path(self) -> str:
        return _str_call('DIDURL_GetPath', self.url)

    def get_query_string(self) -> str:
        return _str_call('DIDURL_GetQueryString', self.url)

    def get_query_size(self) -> int:
        return _int_call('DIDURL_GetQuerySize', self.url)

    def get_query_parameter(self, key: str) -> str:
        return _str_call('DIDURL_GetQueryParameter', self.url, key.encode(), release_name=_DEFAULT_MEMORY_FREE_NAME)

    def has_query_parameter(self, key: str) -> bool:
        return _int_call('DIDURL_HasQueryParameter', self.url, key.encode()) == 1

    def get_metadata(self) -> 'CredentialMetadata':
        return CredentialMetadata(_obj_call('DIDURL_GetMetadata', self.url))

    def __str__(self):
        out_str = ffi.new('char[200]')
        return _str_call('DIDURL_ToString', self.url, out_str, 200)

    def __eq__(self, other: 'DIDURL'):
        return _int_call('DIDURL_Equals', self.url, other.url) == 1

    def __gt__(self, other: 'DIDURL'):
        return _int_call('DIDURL_Compare', self.url, other.url) > 0

    def __ge__(self, other: 'DIDURL'):
        return _int_call('DIDURL_Compare', self.url, other.url) >= 0

    def __lt__(self, other: 'DIDURL'):
        return _int_call('DIDURL_Compare', self.url, other.url) < 0

    def __le__(self, other: 'DIDURL'):
        return _int_call('DIDURL_Compare', self.url, other.url) <= 0


class CredentialMetadata:
    def __init__(self, metadata):
        self.metadata = metadata

    def set_alias(self, alias: str):
        _int_call('CredentialMetadata_SetAlias', self.metadata, alias.encode())

    def get_alias(self) -> str:
        return _str_call('CredentialMetadata_GetAlias', self.metadata)

    def set_extra(self, key: str, value: t.Any):
        if isinstance(value, str):
            _int_call('CredentialMetadata_SetExtra', self.metadata, key.encode(), value.encode())
        elif isinstance(value, bool):
            _int_call('CredentialMetadata_SetExtraWithBoolean', self.metadata, key.encode(), value)
        elif isinstance(value, float):
            _int_call('CredentialMetadata_SetExtraWithDouble', self.metadata, key.encode(), value)
        else:
            raise ElaDIDException(f'CredentialMetadata.set_extra: Unsupported value type: {type(value)}')

    def get_published(self) -> int:
        return _int_call('CredentialMetadata_GetPublished', self.metadata, fail_val=0)

    def get_revoke(self) -> bool:
        return _int_call('CredentialMetadata_GetRevoke', self.metadata) == 1

    def get_transaction_id(self) -> str:
        return _str_call('CredentialMetadata_GetTxid', self.metadata)

    def get_extra(self, key: str) -> str:
        return _str_call('CredentialMetadata_GetExtra', self.metadata, key.encode())

    def get_extra_bool(self, key: str, def_value: bool):
        return _bool_call('CredentialMetadata_GetExtraAsBoolean', self.metadata, key.encode(), def_value, fail_val=None)

    def get_extra_float(self, key: str, def_value: float):
        return _float_call('CredentialMetadata_GetExtraAsDouble', key.encode(), def_value)

    def get_extra_int(self, key: str, def_value: int):
        return _int_call('CredentialMetadata_GetExtraAsInteger', self.metadata, key.encode(), def_value, fail_val=None)


class DIDStatus(Enum):
    Valid = 0  # DID is valid on chain.
    Deactivated = 2  # DID is deactivated on the chain.
    NotFound = 3  # DID is not on the chain.
    Error = -1  # Other status.

    @staticmethod
    def get_status(value: int) -> 'DIDStatus':
        return {0: DIDStatus.Valid,
                2: DIDStatus.Deactivated,
                3: DIDStatus.NotFound,
                -1: DIDStatus.Error}.get(value, DIDStatus.Error)


class DIDBiography:
    def __init__(self, biography):
        self.biography = biography

    def get_owner(self) -> 'DID':
        return DID(_obj_call('DIDBiography_GetOwner', self.biography, release_name='DID_Destroy'))

    def get_status(self) -> DIDStatus:
        return DIDStatus.get_status(_int_call('DIDBiography_GetStatus', self.biography))

    def get_transaction_count(self) -> int:
        return _int_call('DIDBiography_GetTransactionCount', self.biography)

    def get_document_by_index(self, index: int) -> 'DIDDocument':
        return DIDDocument(_obj_call('DIDBiography_GetDocumentByIndex', self.biography, index, release_name='DIDDocument_Destroy'))

    def get_transaction_id_by_index(self, index: int) -> str:
        return _str_call('DIDBiography_GetTransactionIdByIndex', self.biography, index)

    def get_published_by_index(self, index: int) -> int:
        return _int_call('DIDBiography_GetPublishedByIndex', self.biography, index, fail_val=0)

    def get_operation_by_index(self, index: int):
        return _str_call('DIDBiography_GetOperationByIndex', self.biography, index)


class CredentialStatus(Enum):
    Valid = 0  # Credential is valid on chain.
    Revoked = 2  # Credential is revoked on the chain.
    NotFound = 3  # Credential is not on the chain.
    Error = -1  # Other status.

    @staticmethod
    def get_status(value: int) -> 'CredentialStatus':
        return {0: CredentialStatus.Valid,
                2: CredentialStatus.Revoked,
                3: CredentialStatus.NotFound,
                -1: CredentialStatus.Error}.get(value, CredentialStatus.Error)


class CredentialBiography:
    def __init__(self, biography):
        self.biography = biography

    def get_id(self) -> 'DIDURL':
        return DIDURL(_obj_call('CredentialBiography_GetId', self.biography, release_name='DIDURL_Destroy'))

    def get_owner(self) -> 'DID':
        return DID(_obj_call('CredentialBiography_GetOwner', self.biography, release_name='DID_Destroy'))

    def get_status(self) -> CredentialStatus:
        return CredentialStatus.get_status(_int_call('CredentialBiography_GetStatus', self.biography))

    def get_transaction_count(self) -> int:
        return _int_call('CredentialBiography_GetTransactionCount', self.biography)

    def get_credential_by_index(self, index: int) -> 'Credential':
        return Credential(_obj_call('CredentialBiography_GetCredentialByIndex', self.biography, index, release_name='Credential_Destroy'))

    def get_transaction_id_by_index(self, index: int) -> str:
        return _str_call('CredentialBiography_GetTransactionIdByIndex', self.biography, index)

    def get_published_by_index(self, index: int) -> int:
        return _int_call('CredentialBiography_GetPublishedByIndex', index, fail_val=0)

    def get_operation_by_index(self, index: int) -> str:
        return _str_call('CredentialBiography_GetOperationByIndex', self.biography, index)

    def get_transaction_sign_key_by_index(self, index: int) -> 'DIDURL':
        return DIDURL(_obj_call('CredentialBiography_GetTransactionSignkeyByIndex', self.biography, index))


class RootIdentity:
    def __init__(self, store: 'DIDStore', identity):
        self.store = store
        self.identity = identity

    @staticmethod
    def create(store: 'DIDStore', mnemonic: str, passphrase: str, overwrite: bool) -> 'RootIdentity':
        return RootIdentity(store, _obj_call('RootIdentity_Create', mnemonic.encode(), passphrase.encode(), overwrite, store.store, store.storepass,
                                             release_name='RootIdentity_Destroy'))

    @staticmethod
    def create_from_root_key(store: 'DIDStore', extended_prv_key: str, overwrite: bool) -> 'RootIdentity':
        return RootIdentity(store, _obj_call(('RootIdentity_CreateFromRootKey', extended_prv_key.encode(), overwrite, store.store, store.storepass)))

    @staticmethod
    def create_id(mnemonic: str, passphrase: str) -> str:
        return _str_call('RootIdentity_CreateId', mnemonic.encode(), passphrase.encode(), release_name=_DEFAULT_MEMORY_FREE_NAME)

    @staticmethod
    def create_id_from_root_key(extended_prv_key: str) -> str:
        return _str_call('RootIdentity_CreateIdFromRootKey', extended_prv_key.encode(), release_name=_DEFAULT_MEMORY_FREE_NAME)

    def set_as_default(self):
        _int_call('RootIdentity_SetAsDefault', self.identity)

    def get_id(self) -> str:
        return _str_call('RootIdentity_GetId', self.identity)

    def set_alias(self, alias: str):
        _int_call('RootIdentity_SetAlias', self.identity, alias.encode())

    def get_alias(self) -> str:
        return _str_call('RootIdentity_GetAlias', self.identity)

    def set_default_did(self, did: DID):
        _int_call('RootIdentity_SetDefaultDID', did.did)

    def get_default_did(self):
        return DID(_obj_call('RootIdentity_GetDefaultDID', self.identity, release_name='DID_Destroy'))

    def get_did_by_index(self, index: int) -> DID:
        return DID(_obj_call('RootIdentity_GetDIDByIndex', self.identity, index, release_name='DID_Destroy'))

    def new_did(self, store: 'DIDStore', alias: str, overwrite: bool):
        return DIDDocument(_obj_call('RootIdentity_NewDID', self.identity, store.storepass, alias.encode(), overwrite, release_name='DIDDocument_Destroy'))

    def get_did_0(self) -> DID:
        return self.get_did_by_index(0)

    def sync_by_index(self, index) -> None:
        return _bool_call('RootIdentity_SynchronizeByIndex', self.identity, index, ffi.NULL)

    def sync_0(self) -> None:
        self.sync_by_index(0)

    def new_did_by_index(self, index, overwrite=True) -> 'DIDDocument':
        return DIDDocument(_obj_call('RootIdentity_NewDIDByIndex', self.identity, index, self.store.storepass, ffi.NULL, overwrite,
                                     release_name='DIDDocument_Destroy'))

    def new_did_0(self) -> 'DIDDocument':
        return self.new_did_by_index(0)

    def new_did_by_identifier(self, store: 'DIDStore', identifier: str, security_code: int, alias: str, overwrite: bool) -> 'DIDDocument':
        return DIDDocument(_obj_call('RootIdentity_NewDIDByIdentifier',
                                     self.identity, identifier.encode(), security_code, store.storepass, alias.encode(), overwrite,
                                     release_name='DIDDocument_Destroy'))

    def get_did_by_identifier(self, identifier: str, security_code: int):
        return DID(_obj_call('RootIdentity_GetDIDByIdentifier', self.identity, identifier.encode(), security_code, release_name='DID_Destroy'))

    def synchronize(self, conflict_handle: t.Callable[['DIDDocument', 'DIDDocument'], 'DIDDocument']):
        @ffi.callback("DIDDocument* (DIDDocument *, DIDDocument *)")
        def ffi_handle(chain_doc, local_doc):
            return conflict_handle(DIDDocument(chain_doc), DIDDocument(local_doc)).doc
        _bool_call('RootIdentity_Synchronize', self.identity, ffi_handle)

    def synchronize_by_index(self, index: int, conflict_handle: t.Callable[['DIDDocument', 'DIDDocument'], 'DIDDocument']):
        @ffi.callback("DIDDocument* (DIDDocument *, DIDDocument *)")
        def ffi_handle(chain_doc, local_doc):
            return conflict_handle(DIDDocument(chain_doc), DIDDocument(local_doc)).doc
        _bool_call('RootIdentity_SynchronizeByIndex', self.identity, index, ffi_handle)


class Cipher:
    def __init__(self, cipher):
        self.cipher = cipher

    def set_other_side_public_key(self, key: bytes):
        _bool_call('Cipher_SetOtherSidePublicKey', self.cipher, ffi.from_buffer(key))

    def encrypt(self, data: bytes, nonce: bytes) -> bytes:
        length = ffi.new("unsigned int *")
        cipher_data = _obj_call('Cipher_Encrypt', self.cipher, ffi.from_buffer(data), len(data), ffi.from_buffer(nonce), length)
        return bytes(ffi.buffer(_get_gc_obj(cipher_data, _DEFAULT_MEMORY_FREE_NAME), length[0]))

    def decrypt(self, data: bytes, nonce: bytes) -> bytes:
        length = ffi.new("unsigned int *")
        clear_data = _obj_call('Cipher_Decrypt', self.cipher, ffi.from_buffer(data), len(data), ffi.from_buffer(nonce), length)
        return bytes(ffi.buffer(_get_gc_obj(clear_data, _DEFAULT_MEMORY_FREE_NAME), length[0]))

    def create_encryption_stream(self):
        return CipherEncryptionStream(_obj_call('Cipher_EncryptionStream_Create', self.cipher,
                                                release_name=_DEFAULT_MEMORY_FREE_NAME))

    def create_decryption_stream(self, header):
        return CipherDecryptionStream(_obj_call('Cipher_DecryptionStream_Create', self.cipher, ffi.from_buffer(header),
                                                release_name=_DEFAULT_MEMORY_FREE_NAME))

    def get_ed25519_public_key(self) -> bytes:
        length = ffi.new("unsigned int *")
        key = _obj_call('Cipher_GetEd25519PublicKey', self.cipher, length)
        return bytes(ffi.buffer(key, length[0]))

    def get_curve25519_public_key(self) -> bytes:
        length = ffi.new("unsigned int *")
        key = _obj_call('Cipher_GetCurve25519PublicKey', self.cipher, length)
        return bytes(ffi.buffer(key, length[0]))


class CipherEncryptionStream:
    def __init__(self, stream):
        self.stream = stream

    def header(self) -> bytes:
        length = ffi.new("unsigned int *")
        header = _obj_call('Cipher_EncryptionStream_Header', self.stream, length)
        return bytes(ffi.buffer(header, length[0]))

    def push(self, data: bytes, is_final) -> bytes:
        length = ffi.new("unsigned int *")
        cipher_data = _obj_call('Cipher_EncryptionStream_Push', self.stream, ffi.from_buffer(data), len(data), is_final, length)
        return bytes(ffi.buffer(_get_gc_obj(cipher_data, _DEFAULT_MEMORY_FREE_NAME), length[0]))


class CipherDecryptionStream:
    def __init__(self, stream):
        self.stream = stream

    @staticmethod
    def header_len():
        return _int_call('Cipher_DecryptionStream_GetHeaderLen', fail_val=None)

    @staticmethod
    def extra_encryption_size():
        return _int_call('Cipher_DecryptionStream_GetExtraEncryptSize', fail_val=None)

    def pull(self, data: bytes) -> bytes:
        length = ffi.new("unsigned int *")
        clear_data = _obj_call('Cipher_DecryptionStream_Pull', self.stream, ffi.from_buffer(data), len(data), length)
        return bytes(ffi.buffer(_get_gc_obj(clear_data, _DEFAULT_MEMORY_FREE_NAME), length[0]))

    def is_complete(self):
        return _bool_call('Cipher_DecryptionStream_IsComplete', self.stream)


class DIDDocument:
    def __init__(self, doc):
        self.doc = doc

    @staticmethod
    def from_json(doc_str: str) -> 'DIDDocument':
        # BUGBUG
        # return DIDDocument(_obj_call('DIDDocument_FromJson', doc_str.encode(), release_name='DIDDocument_Destroy'))
        return DIDDocument(_obj_call('DIDDocument_FromJson', doc_str.encode()))

    def to_json(self, normalized: bool = True) -> str:
        return _str_call('DIDDocument_ToJson', self.doc, normalized, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def is_customized_did(self):
        return _int_call('DIDDocument_IsCustomizedDID', self.doc) == 1

    def is_deactivated(self):
        return _int_call('DIDDocument_IsDeactivated', self.doc) == 1

    def is_genuine(self):
        return _int_call('DIDDocument_IsGenuine', self.doc) == 1

    def is_expired(self):
        return _int_call('DIDDocument_IsExpired', self.doc) == 1

    def is_valid(self) -> bool:
        return _int_call('DIDDocument_IsValid', self.doc) == 1

    def is_qualified(self) -> bool:
        return _int_call('DIDDocument_IsQualified', self.doc) == 1

    def get_subject(self) -> DID:
        return DID(_obj_call('DIDDocument_GetSubject', self.doc))

    def edit(self, controller_doc: 'DIDDocument') -> 'DIDDocumentBuilder':
        return DIDDocumentBuilder(_obj_call('DIDDocument_Edit', self.doc, controller_doc, release_name='DIDDocumentBuilder_Destroy'))

    def get_multisig(self):
        return _int_call('DIDDocument_GetMultisig', self.doc)

    def get_controller_count(self):
        return _int_call('DIDDocument_GetControllerCount', self.doc)

    def get_controllers(self, size):
        controllers = ffi.new('struct DID[]', size)
        real_size = _int_call('DIDDocument_GetControllers', self.doc, controllers, size)
        return _c_array_to_list(controllers, min(real_size, size))

    def contains_controller(self, controller: DID) -> bool:
        return _int_call('DIDDocument_ContainsController', self.doc, controller.did) == 1

    def get_public_key_count(self):
        return _int_call('DIDDocument_GetPublicKeyCount', self.doc)

    def get_public_keys(self, size):
        keys = ffi.new('struct PublicKey[]', size)
        real_size = _int_call('DIDDocument_GetPublicKeys', self.doc, keys, size)
        return _c_array_to_list(keys, min(real_size, size))

    def get_public_key(self, keyid: DIDURL) -> 'PublicKey':
        return PublicKey(_obj_call('DIDDocument_GetPublicKey', self.doc, keyid.url))

    def select_public_keys(self, type_, keyid: DIDURL, size):
        keys = ffi.new('struct PublicKey[]', size)
        real_size = _int_call('DIDDocument_SelectPublicKeys', self.doc, type_.encode(), keyid.url, keys, size)
        return _c_array_to_list(keys, min(real_size, size))

    def get_default_public_key(self) -> DIDURL:
        return DIDURL(_obj_call('DIDDocument_GetDefaultPublicKey', self.doc))

    def get_authentication_count(self):
        return _int_call('DIDDocument_GetAuthenticationCount', self.doc)

    def get_authentication_keys(self, size):
        keys = ffi.new('struct PublicKey[]', size)
        real_size = _int_call('DIDDocument_GetAuthenticationKeys', self.doc, keys, size)
        return _c_array_to_list(keys, min(real_size, size))

    def get_authentication_key(self, keyid: DIDURL) -> 'PublicKey':
        return PublicKey(_obj_call('DIDDocument_GetAuthenticationKey', self.doc, keyid.url))

    def select_authentication_keys(self, type_, keyid: DIDURL, size):
        keys = ffi.new('struct PublicKey[]', size)
        real_size = _int_call('DIDDocument_SelectAuthenticationKeys', self.doc, type_.encode(), keyid.url, keys, size)
        return _c_array_to_list(keys, min(real_size, size))

    def is_authentication_key(self, keyid: DIDURL) -> bool:
        return _int_call('DIDDocument_IsAuthenticationKey', self.doc, keyid.url) == 1

    def is_authorization_key(self, keyid: DIDURL) -> bool:
        return _int_call('DIDDocument_IsAuthorizationKey', self.doc, keyid.url) == 1

    def get_authorization_count(self) -> int:
        return _int_call('DIDDocument_GetAuthorizationCount', self.doc)

    def get_authorization_keys(self, size):
        keys = ffi.new('struct PublicKey[]', size)
        real_size = _int_call('DIDDocument_GetAuthorizationKeys', self.doc, keys, size)
        return _c_array_to_list(keys, min(real_size, size))

    def get_authorization_key(self, keyid: DIDURL) -> 'PublicKey':
        return PublicKey(_obj_call('DIDDocument_GetAuthorizationKey', self.doc, keyid.url))

    def select_authorization_keys(self, type_, keyid: DIDURL, size):
        keys = ffi.new('struct PublicKey[]', size)
        real_size = _int_call('DIDDocument_SelectAuthorizationKeys', self.doc, type_.encode(), keyid.url, keys, size)
        return _c_array_to_list(keys, min(real_size, size))

    def get_credential_count(self) -> int:
        return _int_call('DIDDocument_GetCredentialCount', self.doc)

    def get_credentials(self, size):
        credentials = ffi.new('struct Credential[]', size)
        real_size = _int_call('DIDDocument_GetCredentials', self.doc, credentials, size)
        return _c_array_to_list(credentials, min(real_size, size))

    def get_credential(self, credid: DIDURL) -> 'Credential':
        return Credential(_obj_call('DIDDocument_GetCredential', self.doc, credid.url))

    def select_credentials(self, type_, credid: DIDURL, size):
        credentials = ffi.new('struct Credential[]', size)
        real_size = _int_call('DIDDocument_SelectCredentials', self.doc, type_.encode(), credid.url, credentials, size)
        return _c_array_to_list(credentials, min(real_size, size))

    def get_service_count(self) -> int:
        return _int_call('DIDDocument_GetServiceCount', self.doc)

    def get_services(self, size):
        services = ffi.new('struct Service[]', size)
        real_size = _int_call('DIDDocument_GetServices', self.doc, services, size)
        return _c_array_to_list(services, min(real_size, size))

    def get_service(self, serviceid: DIDURL) -> 'Service':
        return Service(_obj_call('DIDDocument_GetService', self.doc, serviceid.url))

    def select_services(self, type_, service_id: DIDURL, size):
        services = ffi.new('struct Service[]', size)
        real_size = _int_call('DIDDocument_SelectServices', self.doc, type_.encode(), service_id.url, services, size)
        return _c_array_to_list(services, min(real_size, size))

    def get_expires(self) -> int:
        return _int_call('DIDDocument_GetExpires', self.doc, fail_val=0)

    # /* DID_API */ DIDDocument *DIDDocument_NewCustomizedDID(DIDDocument *document,
    #         const char *customizeddid, DID **controllers, size_t size, int multisig,

    def sign(self, key_id: DIDURL, store: 'DIDStore', sig: str, count: int, *args):
        _int_call('DIDDocument_Sign', self.doc, key_id.url, store.storepass, sig.encode(), count, *args)

    def sign_digest(self, key_id: DIDURL, store: 'DIDStore', sig: str, digest: str, size):
        _int_call('DIDDocument_SignDigest', self.doc, key_id.url, store.storepass, sig.encode(), digest.encode(), size)

    def verify(self, key_id: DIDURL, sig: str, count: int, *args):
        _int_call('DIDDocument_Verify', self.doc, key_id.url, sig.encode(), count, *args)

    def verify_digest(self, key_id: DIDURL, store: 'DIDStore', sig: str, digest: str, size):
        _int_call('DIDDocument_VerifyDigest', self.doc, key_id.url, store.storepass, sig.encode(), digest.encode(), size)

    def create_cipher(self, identifier, security_code, storepass) -> 'Cipher':
        return Cipher(_obj_call('DIDDocument_CreateCipher', self.doc, identifier.encode(), security_code, storepass.encode(),
                                release_name='DIDDocument_Cipher_Destroy'))

    def create_curve25519_cipher(self, identifier, security_code, storepass, is_server) -> 'Cipher':
        return Cipher(_obj_call('DIDDocument_CreateCurve25519Cipher', self.doc, identifier.encode(), security_code, storepass.encode(), is_server,
                                release_name='DIDDocument_Cipher_Destroy'))

    def get_metadata(self):
        return DIDMetadata(_obj_call('DIDDocument_GetMetadata', self.doc))

    def get_proof_count(self):
        return _int_call('DIDDocument_GetProofCount', self.doc)

    def get_proof_type(self, index: int):
        return _str_call('DIDDocument_GetProofType', self.doc, index)

    def get_proof_creator(self, index):
        return DIDURL(_obj_call('DIDDocument_GetProofCreater', self.doc, index))

    def get_proof_create_time(self, index):
        return _int_call('DIDDocument_GetProofCreatedTime', self.doc, index, fail_val=0)

    def get_proof_signature(self, index: int):
        return _str_call('DIDDocument_GetProofSignature', self.doc, index)

    def get_jwt_builder(self) -> 'JWTBuilder':
        return JWTBuilder(_obj_call('DIDDocument_GetJwtBuilder', self.doc, release_name='JWTBuilder_Destroy'))

    # /*DID_API*/ JWSParser *DIDDocument_GetJwsParser(DIDDocument *document);

    def derive_by_identifier(self, identifier: str, security_code: str, store: 'DIDStore'):
        return _str_call('DIDDocument_DeriveByIdentifier', self.doc, identifier.encode(), security_code, store.storepass, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def derive_by_index(self, index: int, store: 'DIDStore'):
        return _str_call('DIDDocument_DeriveByIndex', self.doc, index, store.storepass, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def sign_document(self, document: str, store: 'DIDStore'):
        return DIDDocument(_obj_call('DIDDocument_SignDIDDocument', self.doc, document.encode(), store.storepass, release_name='DIDDocument_Destroy'))

    @staticmethod
    def merge_documents(count: int, *args):
        return _str_call('DIDDocument_MergeDIDDocuments', count, *args, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def create_transfer_ticket(self, owner: DID, to: DID, store: 'DIDStore'):
        return TransferTicket(_obj_call('DIDDocument_CreateTransferTicket', self.doc, owner.did, to.did, store.storepass, release_name='TransferTicket_Destroy'))

    def sign_transfer_ticket(self, ticket: 'TransferTicket', store: 'DIDStore'):
        _int_call('DIDDocument_SignTransferTicket', self.doc, ticket.ticket, store.storepass)

    def publish_did(self, sign_key: DIDURL, force: bool, store: 'DIDStore') -> bool:
        return _int_call('DIDDocument_PublishDID', self.doc, sign_key.url, force, store.storepass) == 1

    def transfer_did(self, ticket: 'TransferTicket', sign_key: DIDURL, store: 'DIDStore') -> bool:
        return _int_call('DIDDocument_TransferDID', self.doc, ticket.ticket, sign_key.url, store.storepass) == 1

    def deactivate_did(self, sign_key: DIDURL, store: 'DIDStore') -> bool:
        return _int_call('DIDDocument_DeactivateDID', self.doc, sign_key.url, store.storepass) == 1

    def deactivate_did_by_authorizer(self, target: DID, sign_key: DIDURL, store: 'DIDStore') -> bool:
        return _int_call('DIDDocument_DeactivateDIDByAuthorizor', self.doc, target.did, sign_key.url, store.storepass) == 1

    def __str__(self, normalized=True):
        return _str_call('DIDDocument_ToString', self.doc, normalized, release_name=_DEFAULT_MEMORY_FREE_NAME)


class PublicKey:
    def __init__(self, key):
        self.key = key

    def get_id(self) -> DIDURL:
        return DIDURL(_obj_call('PublicKey_GetId', self.key))

    def get_controller(self) -> DID:
        return DID(_obj_call('PublicKey_GetController', self.key))

    def get_public_key_base58(self) -> str:
        return _str_call('PublicKey_GetPublicKeyBase58', self.key)

    def get_type(self) -> str:
        return _str_call('PublicKey_GetType', self.key)

    def is_authentication_key(self) -> bool:
        return _int_call('PublicKey_IsAuthenticationKey', self.key) == 1

    def is_authorization_key(self) -> bool:
        return _int_call('PublicKey_IsAuthorizationKey', self.key) == 1


class Service:
    def __init__(self, service):
        self.service = service

    def get_id(self) -> DIDURL:
        return DIDURL(_obj_call('Service_GetId', self.service))

    def get_endpoint(self) -> str:
        return _str_call('Service_GetEndpoint', self.service)

    def get_type(self) -> str:
        return _str_call('Service_GetType', self.service)

    def get_property_count(self) -> int:
        return _int_call('Service_GetPropertyCount', self.service)

    def get_properties(self) -> str:
        return _str_call('Service_GetProperties', self.service, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def get_property(self, name: str) -> str:
        return _str_call('Service_GetProperty', self.service, name.encode(), release_name=_DEFAULT_MEMORY_FREE_NAME)


class TransferTicket:
    def __init__(self, ticket):
        self.ticket = ticket

    def to_json(self) -> str:
        return _str_call('TransferTicket_ToJson', self.ticket, release_name=_DEFAULT_MEMORY_FREE_NAME)

    @staticmethod
    def from_json(json: str) -> 'TransferTicket':
        return TransferTicket(_obj_call('TransferTicket_FromJson', json.encode(), release_name='TransferTicket_Destroy'))

    def is_valid(self) -> bool:
        return _int_call('TransferTicket_IsValid', self.ticket) == 1

    def is_qualified(self) -> bool:
        return _int_call('TransferTicket_IsQualified', self.ticket) == 1

    def is_genuine(self) -> bool:
        return _int_call('TransferTicket_IsGenuine', self.ticket) == 1

    def get_owner(self) -> DID:
        return DID(_obj_call('TransferTicket_GetOwner', self.ticket))

    def get_recipient(self) -> DID:
        return DID(_obj_call('TransferTicket_GetRecipient', self.ticket))

    def get_transaction_id(self) -> str:
        return _str_call('TransferTicket_GetTransactionId', self.ticket)

    def get_proof_count(self) -> int:
        return _int_call('TransferTicket_GetProofCount', self.ticket)

    def get_proof_type(self, index: int) -> str:
        return _str_call('TransferTicket_GetProofType', self.ticket, index)

    def get_sign_key(self, index: int) -> DIDURL:
        return DIDURL(_obj_call('TransferTicket_GetSignKey', self.ticket, index))

    def get_proof_create_time(self, index: int) -> int:
        return _int_call('TransferTicket_GetProofCreatedTime', self.ticket, index, fail_val=0)

    def get_proof_signature(self, index: int) -> str:
        return _str_call('TransferTicket_GetProofSignature', self.ticket, index)


class DIDDocumentBuilder:
    def __init__(self, builder):
        self.builder = builder

    def seal(self, store: 'DIDStore'):
        return DIDDocument(_obj_call('DIDDocumentBuilder_Seal', self.builder, store.storepass, release_name='DIDDocument_Destroy'))

    def get_subject(self, store: 'DIDStore') -> DID:
        return DID(_obj_call('DIDDocumentBuilder_GetSubject', self.builder, store.storepass))

    def add_context(self, context: str):
        _int_call('DIDDocumentBuilder_AddContext', self.builder, context.encode())

    def add_default_context(self):
        _int_call('DIDDocumentBuilder_AddDefaultContext', self.builder)

    def add_controller(self, controller: 'DID'):
        _int_call('DIDDocumentBuilder_AddController', self.builder, controller.did)

    def remove_controller(self, controller: 'DID'):
        _int_call('DIDDocumentBuilder_RemoveController', self.builder, controller.did)

    def add_public_key(self, keyid: DIDURL, controller: 'DID', key: str):
        _int_call('DIDDocumentBuilder_AddPublicKey', self.builder, keyid.url, controller.did, key.encode())

    def remove_public_key(self, keyid: DIDURL, force: bool = True):
        """
        :param keyid An identifier of public key.
        :param force True, must remove key; false, if key is authentication or authorization key, not to remove.
        """
        _int_call('DIDDocumentBuilder_RemovePublicKey', self.builder, keyid.url, force)

    def add_authentication_key(self, keyid: DIDURL, key: str):
        _int_call('DIDDocumentBuilder_AddAuthenticationKey', self.builder, keyid.url, key.encode())

    def remove_authentication_key(self, keyid: DIDURL):
        _int_call('DIDDocumentBuilder_RemoveAuthenticationKey', self.builder, keyid.url)

    def add_authorization_key(self, keyid: DIDURL, key: str, controller: 'DID'):
        _int_call('DIDDocumentBuilder_AddAuthorizationKey', self.builder, keyid.url, controller.did, key.encode())

    def remove_authorization_key(self, keyid: DIDURL):
        _int_call('DIDDocumentBuilder_RemoveAuthorizationKey', self.builder, keyid.url)

    def authorize_did(self, keyid: DIDURL, controller: 'DID', key: str):
        _int_call('DIDDocumentBuilder_AuthorizeDid', self.builder, keyid.url, controller.did, key.encode())

    def add_credential(self, credential: 'Credential'):
        _int_call('DIDDocumentBuilder_AddCredential', self.builder, credential.vc)

    def remove_credential(self, credential_id: 'DIDURL'):
        _int_call('DIDDocumentBuilder_RemoveCredential', self.builder, credential_id.url)

    def add_self_proclaimed_credential(self, credid: DIDURL, types):
        # TODO:
        ...

    # /* DID_API */ int DIDDocumentBuilder_AddSelfProclaimedCredential(DIDDocumentBuilder *builder,
    #         DIDURL *credid, const char **types, size_t typesize,
    #         Property *properties, int propsize, time_t expires, DIDURL *signkey, const char *storepass);

    def renew_self_proclaimed_credential(self, controller: DID, sign_key: DIDURL, store: 'DIDStore'):
        _int_call('DIDDocumentBuilder_RenewSelfProclaimedCredential', self.builder, controller.did, sign_key.url, store.storepass)

    def remove_self_proclaimed_credential(self, controller: DID):
        _int_call('DIDDocumentBuilder_RemoveSelfProclaimedCredential', self.builder, controller.did)

    def add_service(self, service_id: DID, type_: str, endpoint: str):
        _int_call('DIDDocumentBuilder_AddService', self.builder, service_id.did, type_.encode(), endpoint.encode())

    def remove_service(self, service_id: DID):
        _int_call('DIDDocumentBuilder_RemoveService', self.builder, service_id.did)

    def remove_proof(self, controller: DID):
        _int_call('DIDDocumentBuilder_RemoveProof', self.builder, controller.did)

    def set_expires(self, expires: int):
        _int_call('DIDDocumentBuilder_SetExpires', self.builder, expires)

    def set_multi_sig(self, multi_sig: int):
        _int_call('DIDDocumentBuilder_SetMultisig', self.builder, multi_sig)


class CredentialProperty:
    def __init__(self, key, value):
        self.key = key
        self.value = value


class Credential:
    def __init__(self, vc):
        self.vc = vc

    def to_json(self, normalized=True) -> str:
        return _str_call('Credential_ToJson', self.vc, normalized, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def __str__(self):
        return _str_call('Credential_ToString', self.vc, True)

    @staticmethod
    def from_json(vc_json: str, owner: 'DID' = None) -> 'Credential':
        return Credential(_obj_call('Credential_FromJson', vc_json.encode(), owner.did if owner else ffi.NULL, release_name='Credential_Destroy'))

    def is_self_proclaimed(self) -> bool:
        return _int_call('Credential_IsSelfProclaimed', self.vc) == 1

    def get_id(self) -> DIDURL:
        return DIDURL(_obj_call('Credential_GetId', self.vc))

    def get_owner(self) -> DID:
        return DID(_obj_call('Credential_GetOwner', self.vc))

    def get_type_count(self) -> int:
        return _int_call('Credential_IsSelfProclaimed', self.vc)

    # def get_types(self, size):
    #     services = ffi.new('char *[]', size)
    #     real_size = _int_call('DIDDocument_GetServices', self.doc, services, size)
    #     return _c_array_to_list(services, min(real_size, size))
    # /* DID_API */ ssize_t Credential_GetTypes(Credential *credential, const char **types, size_t size);

    def get_issuer(self) -> DID:
        return DID(_obj_call('Credential_GetIssuer', self.vc))

    def get_issuance_date(self):
        return _int_call('Credential_GetIssuanceDate', self.vc, fail_val=0)

    def get_expiration_date(self) -> int:
        return _int_call('Credential_GetExpirationDate', self.vc, fail_val=0)

    def get_property_count(self) -> int:
        return _int_call('Credential_GetExpirationDate', self.vc)

    def get_properties(self) -> str:
        return _str_call('Credential_GetProperties', self.vc, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def get_property(self, name: str) -> str:
        return _str_call('Credential_GetProperty', self.vc, name.encode(), release_name=_DEFAULT_MEMORY_FREE_NAME)

    def get_proof_create_time(self) -> int:
        return _int_call('Credential_GetProofCreatedTime', self.vc, fail_val=0)

    def get_proof_method(self) -> str:
        return _str_call('Credential_GetProperty', self.vc)

    def get_proof_type(self) -> str:
        return _str_call('Credential_GetProofType', self.vc)

    def get_proof_signature(self) -> str:
        return _str_call('Credential_GetProofSignture', self.vc)

    def is_expired(self) -> bool:
        return _int_call('Credential_IsExpired', self.vc) == 1

    def is_genuine(self) -> bool:
        return _int_call('Credential_IsGenuine', self.vc) == 1

    def is_valid(self) -> bool:
        return _int_call('Credential_IsValid', self.vc) == 1

    def declare(self, sign_key: DIDURL, store: 'DIDStore'):
        _int_call('Credential_Declare', self.vc, sign_key.url, store.storepass)

    def revoke(self, sign_key: DIDURL, store: 'DIDStore'):
        _int_call('Credential_Revoke', self.vc, sign_key.url, store.storepass)

    @staticmethod
    def revoke_by_id(id_: DIDURL, document: DIDDocument, sign_key: DIDURL, store: 'DIDStore') -> bool:
        return _int_call('Credential_RevokeById', id_.url, document.doc, sign_key.url, store.storepass) == 1

    # @staticmethod
    # def resolve(self, ):
    # /* DID_API */ Credential *Credential_Resolve(DIDURL *id, int *status, bool force);

    @staticmethod
    def resolve_revocation(id_: DIDURL, issuer: DID) -> bool:
        return _int_call('Credential_ResolveRevocation', id_.url, issuer.did)

    @staticmethod
    def resolve_biography(id_: DIDURL, issuer: DID) -> CredentialBiography:
        return CredentialBiography(_obj_call('Credential_ResolveBiography', id_.url, issuer.did))

    @staticmethod
    def was_declared(id_: DIDURL) -> bool:
        return _int_call('Credential_WasDeclared', id_) == 1

    def is_revoked(self) -> bool:
        return _int_call('Credential_IsRevoked', self.vc) == 1

    # /* DID_API */ ssize_t Credential_List(DID *did, DIDURL **buffer, size_t size, int skip, int limit);

    def get_metadata(self):
        return CredentialMetadata(_obj_call('Credential_GetMetadata', self.vc))


class Issuer:
    def __init__(self, issuer):
        self.issuer = issuer

    @staticmethod
    def create(did: DID, sign_key: typing.Optional[DIDURL], store: 'DIDStore') -> 'Issuer':
        return Issuer(_obj_call('Issuer_Create', did.did, sign_key.url if sign_key is not None else ffi.NULL,
                                store.store, release_name='Issuer_Destroy'))

    def create_credential(self, owner: DID, credid: DIDURL, type_: str, props: list[CredentialProperty]) -> Credential:
        # BUGBUG: can not simplify to one line.
        type0 = ffi.new("char[]", type_.encode())
        types = ffi.new("char **", type0)
        props_c = ffi.new("struct Property[]", len(props))
        for i in range(len(props)):
            props_c[i].key, props_c[i].value = props[i].key, props[i].value
        return Credential(_obj_call('Issuer_CreateCredential', self.issuer, owner.did, credid.url, types, 1,
                                    props_c, len(props), release_name='Credential_Destroy'))

    def create_credential_by_string(self, store: 'DIDStore', owner: 'DID', fragment: str, type_: str,
                                    props: dict, expire: int) -> Credential:
        # BUGBUG: can not simplify to one line.
        type0 = ffi.new("char[]", type_.encode())
        types = ffi.new("char **", type0)
        return Credential(_obj_call('Issuer_CreateCredentialByString', self.issuer, owner.did, DIDURL.create_from_did(owner, fragment).url,
                                    types, 1, json.dumps(props).encode(), expire, store.storepass,
                                    release_name='Credential_Destroy'))

    def get_signer(self):
        return DID(_obj_call('Issuer_GetSigner', self.issuer))

    def get_sign_key(self):
        return DIDURL(_obj_call('Issuer_GetSigner', self.issuer))


class DIDStore:
    def __init__(self, dir_path: str, storepass: str):
        self.storepass = storepass.encode()
        self.store = DIDStore.__open(dir_path)

    def get_root_identity(self, mnemonic: str, passphrase: str) -> RootIdentity:
        id_ = RootIdentity.create_id(mnemonic, passphrase)

        if self.contains_root_identity(id_):
            return self.load_root_identity(id_)

        return RootIdentity.create(self, mnemonic, passphrase, True)

    @staticmethod
    def __open(dir_path: str):
        return _obj_call('DIDStore_Open', dir_path.encode(), release_name='DIDStore_Close')

    def contains_root_identity(self, id_: str) -> bool:
        return _int_call('DIDStore_ContainsRootIdentity', self.store, id_.encode()) == 1

    def contains_root_identities(self) -> bool:
        return _int_call('DIDStore_ContainsRootIdentities', self.store) == 1

    def load_root_identity(self, id_: str) -> RootIdentity:
        return RootIdentity(self, _obj_call('DIDStore_LoadRootIdentity', self.store, id_.encode()))

    def delete_root_identity(self, id_: str) -> bool:
        return _bool_call('DIDStore_DeleteRootIdentity', self.store, id_.encode())

    def contains_root_identity_mnemonic(self, id_: str) -> bool:
        return _int_call('DIDStore_ContainsRootIdentityMnemonic', self.store, id_.encode()) == 1

    # /* DID_API */ ssize_t DIDStore_ListRootIdentities(DIDStore *store,
    #         DIDStore_RootIdentitiesCallback *callback, void *context);

    def get_default_root_identity(self):
        return _str_call('DIDStore_GetDefaultRootIdentity', self.store, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def export_identity_mnemonic(self, id_: str, mnemonic: str, size: int):
        _int_call('DIDStore_ExportRootIdentityMnemonic', self.store, self.storepass, id_.encode(), mnemonic.encode(), size)

    def store_did(self, doc: DIDDocument):
        _int_call('DIDStore_StoreDID', self.store, doc.doc)

    def load_did(self, did: DID) -> DIDDocument:
        return DIDDocument(_obj_call('DIDStore_LoadDID', self.store, did.did, release_name='DIDDocument_Destroy'))

    def contains_did(self, did: DID) -> bool:
        return _int_call('DIDStore_ContainsDID', self.store, did.did) == 1

    def contains_dids(self) -> bool:
        return _int_call('DIDStore_ContainsDIDs', self.store) == 1

    def delete_did(self, did: DID):
        return _bool_call('DIDStore_DeleteDID', did.did)

    def list_dids(self) -> []:
        """
        :return: list[DID]
        """
        dids = []

        @ffi.def_extern()
        def ListDIDsCallback(did, context):
            # INFO: contains a terminating signal by a did with None.
            if did:
                did_str = ffi.new(f'char[{lib.ELA_MAX_DID_LEN}]')
                did_str = lib.DID_ToString(did, did_str, lib.ELA_MAX_DID_LEN)
                d = lib.DID_FromString(did_str)
                dids.append(DID(_get_gc_obj(d, 'DID_Destroy')))
            # 0 means no error.
            return 0

        filter_has_private_keys = 1
        _int_call('DIDStore_ListDIDs', self.store, filter_has_private_keys, lib.ListDIDsCallback, ffi.NULL)
        return dids

    def store_credential(self, credential: Credential):
        _int_call('DIDStore_StoreCredential', self.store, credential.vc)

    def load_credential(self, did: DID, credid: DIDURL) -> Credential:
        return Credential(_obj_call('DIDStore_LoadCredential', did.did, credid.url, release_name='Credential_Destroy'))

    def contains_credentials(self, did: DID) -> bool:
        return _int_call('DIDStore_ContainsCredentials', self.store, did) == 1

    def contains_credential(self, did: DID, credid: DIDURL) -> bool:
        return _int_call('DIDStore_ContainsCredential', self.store, did.did, credid.url) == 1

    def delete_credential(self, did: DID, id_: DIDURL):
        _bool_call('DIDStore_DeleteCredential', self.store, did.did, id_.url)

    # /* DID_API */ int DIDStore_ListCredentials(DIDStore *store, DID *did,
    #         DIDStore_CredentialsCallback *callback, void *context);

    # /* DID_API */ int DIDStore_SelectCredentials(DIDStore *store, DID *did, DIDURL *credid,
    #         const char *type, DIDStore_CredentialsCallback *callback, void *context);

    def contains_private_keys(self, did: DID) -> bool:
        return _int_call('DIDStore_ContainsPrivateKeys', self.store, did.did) == 1

    def contains_private_key(self, did: DID, key_id: DIDURL) -> bool:
        return _int_call('DIDStore_ContainsPrivateKey', self.store, did.did, key_id.url) == 1

    # /* DID_API */ int DIDStore_StorePrivateKey(DIDStore *store, const char *storepass,
    #         DIDURL *id, const uint8_t *privatekey, size_t size);

    def delete_private_key(self, key_id: DIDURL):
        _void_call('DIDStore_DeletePrivateKey', self.store, key_id.url)

    def synchronize(self, conflict_handler: t.Callable[[DIDDocument, DIDDocument], DIDDocument]):
        @ffi.def_extern()
        def DocumentMergeCallback(chain_copy, local_copy):
            res_doc = conflict_handler(DIDDocument(chain_copy), DIDDocument(local_copy))
            return res_doc.doc if res_doc else ffi.NULL

        _void_call('DIDStore_Synchronize', self.store, DocumentMergeCallback)

    def change_password(self, new_pw: str, old_pw: str):
        _int_call('DIDStore_ChangePassword', self.store, new_pw.encode(), old_pw.encode())

    def export_did(self, did: DID, file: str, password: str):
        _int_call('DIDStore_ExportDID', self.store, self.storepass, did.did, file.encode(), password.encode())

    def import_did(self, file_path: str, passphrase: str):
        _int_call('DIDStore_ImportDID', self.store, self.storepass, file_path.encode(), passphrase.encode())

    def export_root_identity(self, id_: str, file: str, password: str):
        _int_call('DIDStore_ExportRootIdentity', self.store, self.storepass, id_.encode(), file.encode(), password.encode())

    def import_root_identity(self, id_: str, file: str, password: str):
        _int_call('DIDStore_ImportRootIdentity', self.store, self.storepass, id_.encode(), file.encode(), password.encode())

    def export_store(self, zip_file: str, password: str):
        _int_call('DIDStore_ExportStore', self.store, self.storepass, zip_file.encode(), password.encode())

    def import_store(self, zip_file: str, password: str):
        _int_call('DIDStore_ImportStore', self.store, self.storepass, zip_file.encode(), password.encode())


class Mnemonic:
    def __init__(self, value):
        self.value = value.encode()

    @staticmethod
    def generate(language: str) -> str:
        return _str_call('Mnemonic_Generate', language.encode(), release_name='Mnemonic_free')

    def is_valid(self, language: str) -> bool:
        return _bool_call('Mnemonic_IsValid', self.value, language.encode(), fail_val=None)

    def get_language(self):
        return _str_call('Mnemonic_GetLanguage', self.value, release_name=_DEFAULT_MEMORY_FREE_NAME)


class Presentation:
    def __init__(self, vp):
        self.vp = vp

    @staticmethod
    def create(store: DIDStore, did: DID, fragment: str, nonce: str, realm: str, vc: Credential) -> 'Presentation':
        # INFO: It is not supported to combine to a single line.
        type0 = ffi.new("char[]", "VerifiablePresentation".encode())
        types = ffi.new("char **", type0)
        did_url, sign_key = DIDURL.create_from_did(did, fragment), ffi.NULL
        return Presentation(_obj_call('Presentation_Create', did_url.url, did.did, types, 1, nonce.encode(), realm.encode(), sign_key,
                                      store.store, store.storepass, 1, vc.vc, release_name='Presentation_Destroy'))

    # /*DID_API*/ Presentation *Presentation_CreateByCredentials(DIDURL *id, DID *holder,
    #         const char **types, size_t size, const char *nonce, const char *realm,
    #         Credential **creds, size_t count, DIDURL *signkey, DIDStore *store,
    #         const char *storepass);

    @staticmethod
    def from_json(json_str: str) -> 'Presentation':
        return Presentation(_obj_call('Presentation_FromJson', json_str.encode(), release_name='Presentation_Destroy'))

    def to_json(self, normalized: bool = True) -> str:
        return _str_call('Presentation_ToJson', self.vp, normalized, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def is_valid(self) -> bool:
        return _int_call('Presentation_IsValid', self.vp) == 1

    def get_id(self) -> DIDURL:
        return DIDURL(_obj_call('Presentation_GetId', self.vp))

    def get_holder(self) -> DID:
        return DID(_obj_call('Presentation_GetHolder', self.vp))

    def get_credential_count(self) -> int:
        return _int_call('Presentation_GetCredentialCount', self.vp)

    # /* DID_API */ ssize_t Presentation_GetCredentials(Presentation *presentation, Credential **creds, size_t size);

    def get_credential(self, url: DIDURL):
        return Credential(_obj_call('Presentation_GetCredential', self.vp, url.url))

    def get_type_count(self) -> int:
        return _int_call('Presentation_GetTypeCount', self.vp)

    # /* DID_API */ ssize_t Presentation_GetTypes(Presentation *presentation, const char **types, size_t size);

    def get_created_time(self) -> int:
        return _int_call('Presentation_GetCreatedTime', self.vp, fail_val=0)

    def get_verification_method(self):
        return DIDURL(_obj_call('Presentation_GetVerificationMethod', self.vp))

    def get_realm(self) -> str:
        return _str_call('Presentation_GetRealm', self.vp)

    def get_nonce(self) -> str:
        return _str_call('Presentation_GetNonce', self.vp)

    def is_genuine(self):
        return _int_call('Presentation_IsGenuine', self.vp) == 1


# TODO: TransferTicket


class JWTBuilder:
    def __init__(self, builder):
        self.builder = builder

    @staticmethod
    def set_allowed_clock_skew(seconds: int):
        """ Set the amount of clock skew in seconds to tolerate when verifying the
        local time against the 'exp' and 'nbf' claims.
        """
        _void_call('JWTParser_SetAllowedClockSkewSeconds', seconds)

    def set_header(self, attr: str, value: str) -> 'JWTBuilder':
        _bool_call('JWTBuilder_SetHeader', self.builder, attr.encode(), value.encode())
        return self

    def set_subject(self, subject: str) -> 'JWTBuilder':
        _bool_call('JWTBuilder_SetSubject', self.builder, subject.encode())
        return self

    def set_audience(self, audience: str) -> 'JWTBuilder':
        _bool_call('JWTBuilder_SetAudience', self.builder, audience.encode())
        return self

    def set_issue_at(self, iat: int) -> 'JWTBuilder':
        _bool_call('JWTBuilder_SetIssuedAt', self.builder, iat)
        return self

    def set_expiration(self, expiration: int) -> 'JWTBuilder':
        _bool_call('JWTBuilder_SetExpiration', self.builder, expiration)
        return self

    def set_not_before(self, nbf: int) -> 'JWTBuilder':
        _bool_call('JWTBuilder_SetNotBefore', self.builder, nbf)
        return self

    def set_claim_with_json(self, key: str, json: str) -> 'JWTBuilder':
        _bool_call('JWTBuilder_SetClaimWithJson', self.builder, key.encode(), json.encode())
        return self

    def set_claim(self, key: str, value: str) -> 'JWTBuilder':
        _bool_call('JWTBuilder_SetClaim', self.builder, key.encode(), value.encode())
        return self

    def sign(self, key_id: typing.Optional[DIDURL], store: DIDStore) -> 'JWTBuilder':
        _int_call('JWTBuilder_Sign', self.builder, key_id.url if key_id is not None else ffi.NULL, store.storepass)
        return self

    def compact(self) -> str:
        return _str_call('JWTBuilder_Compact', self.builder, release_name=_DEFAULT_MEMORY_FREE_NAME)

    def create_token(self, subject: str, audience_did_str: str, expire: typing.Optional[int], claim_key: str, claim_value: any,
                     store: DIDStore = None, claim_json: bool = True) -> str:
        ticks, sign_key = int(datetime.now().timestamp()), None
        self.set_header('type', 'JWT')\
            .set_header('version', '1.0')\
            .set_subject(subject)\
            .set_audience(audience_did_str)\
            .set_issue_at(ticks)\
            .set_not_before(ticks)
        if expire is not None:
            self.set_expiration(expire)
        if claim_json:
            self.set_claim_with_json(claim_key, claim_value)
        else:
            self.set_claim(claim_key, claim_value)
        self.sign(sign_key, store)
        return self.compact()

    # TODO:


class DIDBackend:
    def __init__(self):
        pass

    @staticmethod
    def initialize_default(resolver_url: str, cache_dir: str):
        _int_call('DIDBackend_InitializeDefault', ffi.NULL, resolver_url.encode(), cache_dir.encode())

    @staticmethod
    def is_initialized() -> bool:
        return _bool_call('DIDBackend_IsInitialized', fail_val=None)

    # /* DID_API */ int DIDBackend_Initialize(CreateIdTransaction_Callback *createtransaction, Resolve_Callback *resolve, const char *cachedir);

    @staticmethod
    def set_ttl(ttl: int):
        _void_call('DIDBackend_SetTTL', ttl)

    @staticmethod
    def set_resolve_handle(handle: t.Callable[[DID], DIDDocument]):
        @ffi.def_extern()
        def MyDIDLocalResovleHandle(did):
            doc = handle(DID(did))
            if not doc:
                return ffi.NULL
            return doc.doc

        _void_call('DIDBackend_SetLocalResolveHandle', lib.MyDIDLocalResovleHandle)


# TODO: Feature

class JWT:
    """
    TODO: add more APIs from ela_jwt.ffi.h file from did native sdk.
    """

    def __init__(self, jwt):
        self.jwt = jwt

    @staticmethod
    def parse(jwt_str: str) -> 'JWT':
        # TODO: rename to default_parse
        # INFO：DefaultJWSParser_Parse will validate the sign information.
        return JWT(_obj_call('DefaultJWSParser_Parse', jwt_str.encode()))

    def get_subject(self):
        return _str_call('JWT_GetSubject', self.jwt)

    def get_claim_as_json(self, claim_key) -> str:
        return _str_call('JWT_GetClaimAsJson', self.jwt, claim_key.encode(), release_name=_DEFAULT_MEMORY_FREE_NAME)

    def get_audience(self):
        return _str_call('JWT_GetAudience', self.jwt)

    def get_claim(self, k: str):
        return _str_call('JWT_GetClaim', self.jwt, k.encode())

    def get_issuer(self):
        return _str_call('JWT_GetIssuer', self.jwt)

    def get_expiration(self):
        return _int_call('JWT_GetExpiration', self.jwt, fail_val=0)

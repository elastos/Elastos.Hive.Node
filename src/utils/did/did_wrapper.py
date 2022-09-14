# -*- coding: utf-8 -*-
import inspect
import json
import typing
from datetime import datetime

from src.utils.did.eladid import ffi, lib

from src.utils.http_exception import ElaDIDException

"""
The wrapper for eladid.so

1. Replace lib.Mnemonic_Free() with lib.DID_FreeMemory.
"""


class ElaError:
    @staticmethod
    def get(prompt=None) -> str:
        """ helper method to get error message from did.so """
        error_msg, c_msg = 'UNKNOWN ERROR', lib.DIDError_GetLastErrorMessage()
        if c_msg:
            error_msg = ffi.string(c_msg).decode()
        return error_msg if not prompt else f'{prompt}: {error_msg}'

    @staticmethod
    def get_from_method(prompt=None, error_print=False):
        """
        Only used for class normal method, not static method.
        """
        ppt = ': ' + prompt if prompt else ''
        frame = inspect.stack()[1]
        self = frame.frame.f_locals['self']
        cls_name = self.__class__.__name__
        mtd_name = frame[3]
        msg = ElaError.get(f'{cls_name}.{mtd_name}{ppt}')
        if error_print:
            with open('output.txt', 'w') as f:
                c_f = ffi.cast("FILE *", f)
                lib.DIDError_Print(c_f)
        return msg


class JWT:
    def __init__(self, jwt):
        self.jwt = jwt

    @staticmethod
    def parse(jwt_str: str) -> 'JWT':
        # INFO：DefaultJWSParser_Parse will validate the sign information.
        jwt = lib.DefaultJWSParser_Parse(jwt_str.encode())
        if not jwt:
            raise ElaDIDException(ElaError.get('JWT.parse'))
        return JWT(jwt)

    def get_subject(self):
        subject = lib.JWT_GetSubject(self.jwt)
        if not subject:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(subject).decode()

    def get_claim_as_json(self, claim_key) -> str:
        claim_value = lib.JWT_GetClaimAsJson(self.jwt, claim_key.encode())
        if not claim_value:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(ffi.gc(claim_value, lib.Mnemonic_Free)).decode()

    def get_audience(self):
        aud = lib.JWT_GetAudience(self.jwt)
        if not aud:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(aud).decode()

    def get_claim(self, k):
        v = lib.JWT_GetClaim(self.jwt, k.encode())
        if not v:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(v).decode()

    def get_issuer(self):
        issuer = lib.JWT_GetIssuer(self.jwt)
        if not issuer:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(issuer).decode()

    def get_expiration(self):
        expire = lib.JWT_GetExpiration(self.jwt)
        if expire <= 0:
            raise ElaDIDException(ElaError.get_from_method())
        return expire


class JWTBuilder:
    def __init__(self, store, builder):
        self.store, self.builder = store, builder

    @staticmethod
    def set_allowed_clock_skew(seconds: int):
        """ Set the amount of clock skew in seconds to tolerate when verifying the
        local time against the 'exp' and 'nbf' claims.
        """
        lib.JWTParser_SetAllowedClockSkewSeconds(seconds)

    def create_token(self, subject: str, audience_did_str: str, expire: typing.Optional[int], claim_key: str, claim_value: any, claim_json: bool = True) -> str:
        ticks, sign_key = int(datetime.now().timestamp()), ffi.NULL
        lib.JWTBuilder_SetHeader(self.builder, "type".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(self.builder, "version".encode(), "1.0".encode())
        lib.JWTBuilder_SetSubject(self.builder, subject.encode())
        lib.JWTBuilder_SetAudience(self.builder, audience_did_str.encode())
        lib.JWTBuilder_SetIssuedAt(self.builder, ticks)
        if expire is not None:
            lib.JWTBuilder_SetExpiration(self.builder, expire)
        lib.JWTBuilder_SetNotBefore(self.builder, ticks)
        if claim_json:
            lib.JWTBuilder_SetClaimWithJson(self.builder, claim_key.encode(), claim_value.encode())
        else:
            lib.JWTBuilder_SetClaim(self.builder, claim_key.encode(), claim_value.encode())
        ret_val = lib.JWTBuilder_Sign(self.builder, sign_key, self.store.storepass)
        if ret_val != 0:
            raise ElaDIDException(ElaError.get_from_method('sign'))
        c_token = lib.JWTBuilder_Compact(self.builder)
        if not c_token:
            raise ElaDIDException(ElaError.get_from_method('compact'))
        return ffi.string(ffi.gc(c_token, lib.Mnemonic_Free)).decode()


class Credential:
    def __init__(self, vc):
        self.vc = vc

    @staticmethod
    def from_json(vc_json: str) -> 'Credential':
        # INFO: second NULL means owner is NULL
        vc = lib.Credential_FromJson(vc_json.encode(), ffi.NULL)
        if not vc:
            raise ElaDIDException(ElaError.get('Credential.from_json'))
        return Credential(ffi.gc(vc, lib.Credential_Destroy))

    def is_valid(self) -> bool:
        ret_val = lib.Credential_IsValid(self.vc)
        if ret_val == -1:
            raise ElaDIDException(ElaError.get_from_method())
        return ret_val == 1

    def get_issuer(self) -> 'DID':
        issuer = lib.Credential_GetIssuer(self.vc)
        if not issuer:
            raise ElaDIDException(ElaError.get_from_method())
        return DID(issuer)

    def get_expiration_date(self) -> int:
        expire_date = lib.Credential_GetExpirationDate(self.vc)
        if expire_date <= 0:
            raise ElaDIDException(ElaError.get_from_method())
        return expire_date

    def to_json(self) -> str:
        # INFO: param 2: normalized
        vc_json = lib.Credential_ToJson(self.vc, True)
        if not vc_json:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(vc_json).decode()

    def __str__(self):
        vc_str = lib.Credential_ToString(self.vc, True)
        if not vc_str:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(vc_str).decode()


class Issuer:
    def __init__(self, store: 'DIDStore', issuer):
        self.store, self.issuer = store, issuer

    def create_credential_by_string(self, owner: 'DID', fragment: str, type_: str, props: dict, expire: int):
        # BUGBUG: can not simplify to one line.
        type0 = ffi.new("char[]", type_.encode())
        types = ffi.new("char **", type0)
        vc = lib.Issuer_CreateCredentialByString(self.issuer, owner.did, owner.create_did_url(fragment),
                                                 types, 1, json.dumps(props).encode(), expire, self.store.storepass)
        if not vc:
            raise ElaDIDException(ElaError.get_from_method())
        return Credential(ffi.gc(vc, lib.Credential_Destroy))


class Presentation:
    def __init__(self, vp):
        self.vp = vp

    @staticmethod
    def from_json(json_str: str) -> 'Presentation':
        vp = lib.Presentation_FromJson(json_str.encode())
        if not vp:
            raise ElaDIDException(ElaError.get('Presentation.from_json'))
        return Presentation(ffi.gc(vp, lib.Presentation_Destroy))

    def to_json(self) -> str:
        normalized = True
        vp_json = lib.Presentation_ToJson(self.vp, normalized)
        if not vp_json:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(ffi.gc(vp_json, lib.Mnemonic_Free)).decode()

    def is_valid(self) -> bool:
        result = lib.Presentation_IsValid(self.vp)
        if result == -1:
            raise ElaDIDException(ElaError.get_from_method())
        return result == 1

    def get_holder(self) -> 'DID':
        holder = lib.Presentation_GetHolder(self.vp)
        if not holder:
            raise ElaDIDException(ElaError.get_from_method())
        return DID(holder)

    def get_credential_count(self):
        count = lib.Presentation_GetCredentialCount(self.vp)
        if count < 0:
            raise ElaDIDException(ElaError.get_from_method())
        return count

    def get_realm(self):
        realm = lib.Presentation_GetRealm(self.vp)
        if not realm:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(realm).decode()

    def get_nonce(self):
        nonce = lib.Presentation_GetNonce(self.vp)
        if not nonce:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(nonce).decode()


class DID:
    def __init__(self, did):
        self.did = did

    def create_did_url(self, fragment: str):
        did_url = lib.DIDURL_NewFromDid(self.did, fragment.encode())
        if not did_url:
            raise ElaDIDException(ElaError.get_from_method('Can not create did url'))
        return ffi.gc(did_url, lib.DIDURL_Destroy)

    @staticmethod
    def from_string(did_str: str) -> 'DID':
        d = lib.DID_FromString(did_str.encode())
        if not d:
            raise ElaDIDException(ElaError.get('DID.from_string'))
        return DID(ffi.gc(d, lib.DID_Destroy))

    def get_method(self) -> str:
        """ Get third part of the did string. """
        return ffi.string(lib.DID_GetMethod(self.did)).decode()

    def get_method_specific_id(self) -> str:
        """ Get third part of the did string. """
        return ffi.string(lib.DID_GetMethodSpecificId(self.did)).decode()

    def resolve(self, force=True) -> 'DIDDocument':
        """
        :param force: only get from chain if True, else get from cache first.
        """
        status = ffi.new("DIDStatus *")
        doc = lib.DID_Resolve(self.did, status, force)
        if not doc:
            raise ElaDIDException(ElaError.get_from_method())
        return DIDDocument(ffi.gc(doc, lib.DIDDocument_Destroy))

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
            raise ElaDIDException(ElaError.get('DIDDocument.from_json'))
        # BUGBUG: for test cases
        # return DIDDocument(ffi.gc(doc, lib.DIDDocument_Destroy))
        return DIDDocument(doc)

    def to_json(self) -> str:
        normalized = True
        doc_str = lib.DIDDocument_ToJson(self.doc, normalized)
        if not doc_str:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.string(ffi.gc(doc_str, lib.Mnemonic_Free)).decode()

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
        vc = lib.DIDDocument_GetCredential(self.doc, did.create_did_url(fragment))
        if not vc:
            raise ElaDIDException(ElaError.get_from_method('Can not get credential'))

        return Credential(vc)

    def get_expires(self) -> int:
        expire = lib.DIDDocument_GetExpires(self.doc)
        if expire == 0:
            raise ElaDIDException(ElaError.get_from_method())
        return expire

    def create_cipher(self, identifier, security_code, storepass) -> 'Cipher':
        cipher = lib.DIDDocument_CreateCipher(self.doc, identifier.encode(), security_code, storepass.encode())
        if not cipher:
            raise ElaDIDException(ElaError.get_from_method('Can not get the cipher'))

        return Cipher(ffi.gc(cipher, lib.DIDDocument_Cipher_Destroy))

    def create_curve25519_cipher(self, identifier, security_code, storepass, is_server) -> 'Cipher':
        cipher = lib.DIDDocument_CreateCurve25519Cipher(self.doc, identifier.encode(), security_code, storepass.encode(), is_server)
        if not cipher:
            raise ElaDIDException(ElaError.get_from_method('Can not get the curve25519 cipher'))

        return Cipher(ffi.gc(cipher, lib.DIDDocument_Cipher_Destroy))


class Cipher:
    def __init__(self, cipher):
        self.cipher = cipher

    def set_other_side_public_key(self, key):
        success = lib.Cipher_SetOtherSidePublicKey(self.cipher, ffi.from_buffer(key))
        if not success:
            raise ElaDIDException(ElaError.get_from_method('Can not set other side public key'))

    def encrypt(self, data, nonce):
        length = ffi.new("unsigned int *")
        cipher_data = lib.Cipher_Encrypt(self.cipher, ffi.from_buffer(data), len(data), ffi.from_buffer(nonce), length)
        if not cipher_data:
            raise ElaDIDException(ElaError.get_from_method('Can not encrypt the data.'))

        return ffi.buffer(ffi.gc(cipher_data, lib.DID_FreeMemory), length[0])

    def decrypt(self, data, nonce):
        length = ffi.new("unsigned int *")
        clear_data = lib.Cipher_Decrypt(self.cipher, ffi.from_buffer(data), len(data), ffi.from_buffer(nonce), length)
        if not clear_data:
            raise ElaDIDException(ElaError.get_from_method('Can not decrypt the data.'))

        return ffi.buffer(ffi.gc(clear_data, lib.DID_FreeMemory), length[0])

    def create_encryption_stream(self):
        stream = lib.Cipher_EncryptionStream_Create(self.cipher)
        if not stream:
            raise ElaDIDException(ElaError.get_from_method('Can not create the encryption stream.'))

        return CipherEncryptionStream(ffi.gc(stream, lib.DID_FreeMemory))

    def create_decryption_stream(self, header):
        stream = lib.Cipher_DecryptionStream_Create(self.cipher, ffi.from_buffer(header))
        if not stream:
            raise ElaDIDException(ElaError.get_from_method('Can not create the decryption stream.'))

        return CipherDecryptionStream(ffi.gc(stream, lib.DID_FreeMemory))

    def get_ed25519_public_key(self):
        length = ffi.new("unsigned int *")
        key = lib.Cipher_GetEd25519PublicKey(self.cipher, length)
        if not key:
            raise ElaDIDException(ElaError.get_from_method('Can not get the ed25519 public key.'))

        return ffi.buffer(key, length[0])

    def get_curve25519_public_key(self):
        length = ffi.new("unsigned int *")
        key = lib.Cipher_GetCurve25519PublicKey(self.cipher, length)
        if not key:
            raise ElaDIDException(ElaError.get_from_method('Can not get the curve25519 public key.'))

        return ffi.buffer(key, length[0])


class CipherEncryptionStream:
    def __init__(self, stream):
        self.stream = stream

    def header(self):
        length = ffi.new("unsigned int *")
        header = lib.Cipher_EncryptionStream_Header(self.stream, length)
        if not header:
            raise ElaDIDException(ElaError.get_from_method('Can not decrypt the data.'))

        return ffi.buffer(header, length[0])

    def push(self, data, is_final):
        length = ffi.new("unsigned int *")
        cipher_data = lib.Cipher_EncryptionStream_Push(self.stream, ffi.from_buffer(data), len(data), is_final, length)
        if not cipher_data:
            raise ElaDIDException(ElaError.get_from_method('Can not push the data.'))

        return ffi.buffer(ffi.gc(cipher_data, lib.DID_FreeMemory), length[0])


class CipherDecryptionStream:
    def __init__(self, stream):
        self.stream = stream

    @staticmethod
    def header_len():
        return lib.Cipher_DecryptionStream_GetHeaderLen()

    @staticmethod
    def extra_encryption_size():
        return lib.Cipher_DecryptionStream_GetExtraEncryptSize()

    def pull(self, data):
        length = ffi.new("unsigned int *")
        clear_data = lib.Cipher_DecryptionStream_Pull(self.stream, ffi.from_buffer(data), len(data), length)
        if not clear_data:
            raise ElaDIDException(ElaError.get_from_method('Can not decrypt the data.'))

        return ffi.buffer(ffi.gc(clear_data, lib.DID_FreeMemory), length[0])

    def is_complete(self):
        return lib.Cipher_DecryptionStream_IsComplete(self.stream)


class RootIdentity:
    def __init__(self, store, identity):
        self.store = store
        self.identity = identity

    def get_did_by_index(self, index: int) -> DID:
        did = lib.RootIdentity_GetDIDByIndex(self.identity, index)
        if not did:
            raise ElaDIDException(ElaError.get_from_method())
        return DID(ffi.gc(did, lib.DID_Destroy))

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
        return DIDDocument(ffi.gc(doc, lib.DIDDocument_Destroy))

    def new_did_0(self) -> DIDDocument:
        return self.new_did_by_index(0)


class DIDStore:
    def __init__(self, dir_path: str, storepass: str):
        self.store = self._init(dir_path)
        self.storepass = storepass.encode()

    def _init(self, dir_path: str):
        store = lib.DIDStore_Open(dir_path.encode())
        if not store:
            raise ElaDIDException(ElaError.get_from_method())
        return ffi.gc(store, lib.DIDStore_Close)

    def load_did(self, did: DID) -> DIDDocument:
        doc = lib.DIDStore_LoadDID(self.store, did.did)
        if not doc:
            raise ElaDIDException(ElaError.get_from_method())
        return DIDDocument(ffi.gc(doc, lib.DIDDocument_Destroy))

    def import_did(self, file_path: str, passphrase: str) -> None:
        ret_val = lib.DIDStore_ImportDID(self.store, self.storepass, file_path.encode(), passphrase.encode())
        if ret_val != 0:
            raise ElaDIDException(ElaError.get_from_method())

    def list_dids(self):
        """
        :return: list[DID]
        """
        dids = []

        @ffi.def_extern()
        def ListDIDsCallback(did, context):
            # INFO: contains a terminating signal by a did with None.
            if did:
                did_str = ffi.new('char[64]')
                did_str = lib.DID_ToString(did, did_str, 64)
                d = lib.DID_FromString(did_str)
                dids.append(DID(ffi.gc(d, lib.DID_Destroy)))
            # 0 means no error.
            return 0

        filter_has_private_keys = 1
        ret_value = lib.DIDStore_ListDIDs(self.store, filter_has_private_keys, lib.ListDIDsCallback, ffi.NULL)
        if ret_value != 0:
            raise ElaDIDException(ElaError.get_from_method())

        return dids

    def get_root_identity(self, mnemonic: str, passphrase: str) -> RootIdentity:
        c_id = lib.RootIdentity_CreateId(mnemonic.encode(), passphrase.encode())
        if not c_id:
            raise ElaDIDException(ElaError.get_from_method('Can not create the id of root identity'))
        c_id = ffi.gc(c_id, lib.Mnemonic_Free)

        if lib.DIDStore_ContainsRootIdentity(self.store, c_id) == 1:
            root_identity = lib.DIDStore_LoadRootIdentity(self.store, c_id)
            if not root_identity:
                raise ElaDIDException(ElaError.get_from_method('Can not load root identity'))
            return RootIdentity(self, root_identity)

        root_identity = lib.RootIdentity_Create(mnemonic.encode(), passphrase.encode(), True, self.store, self.storepass)
        if not root_identity:
            raise ElaDIDException(ElaError.get_from_method('Can not create root identity'))
        return RootIdentity(self, root_identity)

    def contains_did(self, did: DID) -> bool:
        return lib.DIDStore_ContainsDID(self.store, did.did)

    def contains_private_key(self, did: DID) -> bool:
        return lib.DIDStore_ContainsPrivateKey(self.store, did.did) == 1

    def create_issuer(self, did: DID) -> Issuer:
        sign_key = ffi.NULL
        issuer = lib.Issuer_Create(did.did, sign_key, self.store)
        if not issuer:
            raise ElaDIDException(ElaError.get_from_method())
        return Issuer(self, ffi.gc(issuer, lib.Issuer_Destroy))

    def create_presentation(self, did: DID, fragment: str, nonce: str, realm: str, vc: Credential) -> Presentation:
        # BUGBUG: can not combine to single line.
        type0 = ffi.new("char[]", "VerifiablePresentation".encode())
        types = ffi.new("char **", type0)
        did_url, sign_key = did.create_did_url(fragment), ffi.NULL
        vp = lib.Presentation_Create(did_url, did.did, types, 1,
                                     nonce.encode(), realm.encode(), sign_key,
                                     self.store, self.storepass, 1, vc.vc)
        if not vp:
            raise ElaDIDException(ElaError.get_from_method())
        return Presentation(ffi.gc(vp, lib.Presentation_Destroy))

    def get_jwt_builder(self, doc: DIDDocument) -> JWTBuilder:
        builder = lib.DIDDocument_GetJwtBuilder(doc.doc)
        if not builder:
            raise ElaDIDException(ElaError.get_from_method())
        return JWTBuilder(self, ffi.gc(builder, lib.JWTBuilder_Destroy))

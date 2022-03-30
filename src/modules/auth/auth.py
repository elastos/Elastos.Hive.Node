# -*- coding: utf-8 -*-

"""
Entrance of the subscription module.
"""
import json
import logging
import os
from datetime import datetime

from src.utils_v1.did.eladid import ffi, lib

from src import hive_setting
from src.utils_v1.constants import APP_INSTANCE_DID, DID_INFO_NONCE_EXPIRED
from src.utils_v1.did.entity import Entity
from src.utils_v1.did_info import create_nonce, get_did_info_by_app_instance_did, add_did_nonce_to_db, \
    update_did_info_by_app_instance_did, get_did_info_by_nonce, update_token_of_did_info
from src.utils.http_client import HttpClient
from src.utils.http_exception import InvalidParameterException, BadRequestException

from src.utils.http_response import hive_restful_response
from src.utils.consts import URL_DID_SIGN_IN, URL_DID_BACKUP_AUTH
from src.utils.singleton import Singleton


class Auth(Entity, metaclass=Singleton):
    def __init__(self):
        self.storepass = hive_setting.PASSWRD
        Entity.__init__(self, "hive.auth", mnemonic=hive_setting.DID_MNEMONIC, passphrase=hive_setting.DID_PASSPHRASE)
        self.http = HttpClient()

    @hive_restful_response
    def sign_in(self, doc):
        app_instance_did = self.__get_app_instance_did(doc)
        return {
            "challenge": self.__create_challenge(app_instance_did, *self.__save_nonce_to_db(app_instance_did))
        }

    def __get_app_instance_did(self, app_instance_doc):
        doc_str = json.dumps(app_instance_doc)
        app_instance_doc = lib.DIDDocument_FromJson(doc_str.encode())
        if not app_instance_doc or lib.DIDDocument_IsValid(app_instance_doc) != 1:
            raise BadRequestException(msg='The did document is invalid in getting app instance did.')

        app_instance_did = lib.DIDDocument_GetSubject(app_instance_doc)
        if not app_instance_did:
            raise BadRequestException(msg='Can not get did from document in getting app instance did.')

        spec_did_str = ffi.string(lib.DID_GetMethodSpecificId(app_instance_did)).decode()
        try:
            with open(hive_setting.DID_DATA_LOCAL_DIDS + os.sep + spec_did_str, "w") as f:
                f.write(doc_str)
        except Exception as e:
            logging.getLogger("HiveAuth").error(f"Exception in sign_in:{str(e)} in getting app instance did")

        return "did:" + ffi.string(lib.DID_GetMethod(app_instance_did)).decode() + ":" + spec_did_str

    def __save_nonce_to_db(self, app_instance_did):
        nonce, expire_time = create_nonce(), int(datetime.now().timestamp()) + hive_setting.AUTH_CHALLENGE_EXPIRED
        try:
            if not get_did_info_by_app_instance_did(app_instance_did):
                add_did_nonce_to_db(app_instance_did, nonce, expire_time)
            else:
                update_did_info_by_app_instance_did(app_instance_did, nonce, expire_time)
        except Exception as e:
            logging.getLogger("HiveAuth").error(f"Exception in __save_nonce_to_db: {e}")
            raise BadRequestException(msg='Failed to generate nonce.')
        return nonce, expire_time

    def __create_challenge(self, app_instance_did, nonce, expire_time):
        """
        Create challenge for sign in response.
        """
        builder = lib.DIDDocument_GetJwtBuilder(self.doc)  # service instance doc
        if not builder:
            raise BadRequestException(msg=f'Can not get challenge builder: {self.get_error_message()}.')
        lib.JWTBuilder_SetHeader(builder, "type".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())
        lib.JWTBuilder_SetSubject(builder, "DIDAuthChallenge".encode())
        lib.JWTBuilder_SetAudience(builder, app_instance_did.encode())
        lib.JWTBuilder_SetClaim(builder, "nonce".encode(), nonce.encode())
        lib.JWTBuilder_SetExpiration(builder, expire_time)
        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        token = lib.JWTBuilder_Compact(builder)
        msg = '' if token else self.get_error_message()
        lib.JWTBuilder_Destroy(builder)
        if not token:
            raise BadRequestException(msg=f'Failed to create challenge token: {msg}')
        return ffi.string(token).decode()

    @hive_restful_response
    def auth(self, challenge_response):
        credential_info = self.__get_auth_info_from_challenge_response(challenge_response, ['appDid', ])
        access_token = self.__create_access_token(credential_info, "AccessToken")

        try:
            update_token_of_did_info(credential_info["userDid"],
                                     credential_info["appDid"],
                                     credential_info["id"],
                                     credential_info["nonce"],
                                     access_token,
                                     credential_info["expTime"])
        except Exception as e:
            logging.error(f"Exception in __save_auth_info_to_db:: {e}")
            raise e

        return {
            "token": access_token,
        }

    def __get_auth_info_from_challenge_response(self, challenge_response, props=None):
        presentation_json, nonce, nonce_info = self.__get_values_from_challenge_response(challenge_response)
        if nonce_info[DID_INFO_NONCE_EXPIRED] < int(datetime.now().timestamp()):
            raise BadRequestException(msg='The nonce expired.')
        credential_info = self.__get_presentation_credential_info(presentation_json, props)
        if credential_info["id"] != nonce_info[APP_INSTANCE_DID]:
            raise BadRequestException(msg='The app instance did of the credential does not match.')
        credential_info["nonce"] = nonce
        return credential_info

    def __get_values_from_challenge_response(self, challenge_response):
        challenge_response_cstr = lib.DefaultJWSParser_Parse(challenge_response.encode())
        if not challenge_response_cstr:
            raise BadRequestException(msg=f'Invalid challenge response: {self.get_error_message()}')

        presentation_cstr = lib.JWT_GetClaimAsJson(challenge_response_cstr, "presentation".encode())
        lib.JWT_Destroy(challenge_response_cstr)
        if not presentation_cstr:
            raise BadRequestException(msg=f'Can not get presentation cstr: {self.get_error_message()}')
        presentation = lib.Presentation_FromJson(presentation_cstr)
        if not presentation or lib.Presentation_IsValid(presentation) != 1:
            raise BadRequestException(msg=f'The presentation is invalid: {self.get_error_message()}')
        if lib.Presentation_GetCredentialCount(presentation) < 1:
            raise BadRequestException(msg=f'No presentation credential exists: {self.get_error_message()}')

        self.__validate_presentation_realm(presentation)
        nonce, nonce_info = self.__get_presentation_nonce(presentation)
        return json.loads(ffi.string(presentation_cstr).decode()), nonce, nonce_info

    def __get_presentation_nonce(self, presentation):
        nonce = lib.Presentation_GetNonce(presentation)
        if not nonce:
            raise BadRequestException(msg=f'Failed to get presentation nonce: {self.get_error_message()}')
        nonce_str = ffi.string(nonce).decode()
        if not nonce_str:
            raise BadRequestException(msg='Invalid presentation nonce.')
        nonce_info = get_did_info_by_nonce(nonce_str)
        if not nonce_info:
            raise BadRequestException(msg='Can not get presentation nonce information from database.')
        return nonce_str, nonce_info

    def __validate_presentation_realm(self, presentation):
        realm = lib.Presentation_GetRealm(presentation)
        if not realm:
            raise BadRequestException(msg=f'Can not get presentation realm: {self.get_error_message()}')
        realm = ffi.string(realm).decode()
        if not realm or realm != self.get_did_string():
            raise BadRequestException(msg=f'Invalid presentation realm or not match.')

    def __get_presentation_credential_info(self, presentation_json, props=None):
        if "verifiableCredential" not in presentation_json:
            raise BadRequestException(msg='Verifiable credentials do not exist.')

        vcs_json = presentation_json["verifiableCredential"]
        if not isinstance(vcs_json, list):
            raise BadRequestException(msg="Verifiable credentials are not the list.")

        vc_json = vcs_json[0]
        if not vc_json:
            raise BadRequestException(msg='The credential is invalid.')
        if "credentialSubject" not in vc_json or type(vc_json["credentialSubject"]) != dict\
                or "issuer" not in vc_json:
            raise BadRequestException(msg='The credential subject is invalid or the issuer does not exist.')
        credential_info = vc_json["credentialSubject"]

        required_props = ['id', ]
        if props:
            required_props.extend(props)
        not_exist_props = list(filter(lambda p: p not in credential_info, required_props))
        if not_exist_props:
            raise BadRequestException(msg=f"The credentialSubject's prop ({not_exist_props}) does not exists.")

        credential_info["expTime"] = self.__get_presentation_credential_expire_time(vcs_json)
        credential_info["userDid"] = vc_json["issuer"]
        return credential_info

    def __get_presentation_credential_expire_time(self, vcs_json):
        vc_str = json.dumps(vcs_json[0])
        if not vc_str:
            raise BadRequestException(msg='The presentation credential does not exist.')
        vc = lib.Credential_FromJson(vc_str.encode(), ffi.NULL)
        if not vc or lib.Credential_IsValid(vc) != 1:
            raise BadRequestException(msg='The presentation credential is invalid.')
        exp_time = lib.Credential_GetExpirationDate(vc)
        if exp_time <= 0:
            raise BadRequestException(msg="The credential's expiration date does not exist.")
        return min(int(datetime.now().timestamp()) + hive_setting.ACCESS_TOKEN_EXPIRED, exp_time)

    def __create_access_token(self, credential_info, subject):
        doc = lib.DIDStore_LoadDID(self.store, self.did)
        if not doc:
            raise BadRequestException(msg=f'Can not load node did in creating access token: {self.get_error_message()}')

        builder = lib.DIDDocument_GetJwtBuilder(doc)
        if not builder:
            raise BadRequestException(msg=f'Can not get builder for creating access token: {self.get_error_message()}')

        lib.JWTBuilder_SetHeader(builder, "typ".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())
        lib.JWTBuilder_SetSubject(builder, subject.encode())
        lib.JWTBuilder_SetAudience(builder, credential_info["id"].encode())
        lib.JWTBuilder_SetExpiration(builder, credential_info["expTime"])

        props = {k: credential_info[k] for k in credential_info if k not in ['id', 'expTime']}
        if not lib.JWTBuilder_SetClaim(builder, "props".encode(), json.dumps(props).encode()):
            msg = self.get_error_message()
            lib.JWTBuilder_Destroy(builder)
            raise BadRequestException(msg=f'Can not set claim in creating access token: {msg}')

        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        token = lib.JWTBuilder_Compact(builder)
        msg = '' if token else self.get_error_message()
        lib.JWTBuilder_Destroy(builder)
        if not token:
            raise BadRequestException(msg=f'Can not build token in creating access token: {msg}')

        return ffi.string(token).decode()

    @hive_restful_response
    def backup_auth(self, challenge_response):
        """ for the vault service node """
        credential_info = self.__get_auth_info_from_challenge_response(challenge_response, ["targetHost", "targetDID"])
        access_token = self.__create_access_token(credential_info, "BackupToken")
        return {'token': access_token}

    def get_error_message(self, prompt=None):
        """ helper method to get error message from did.so """
        error_msg = lib.DIDError_GetLastErrorMessage()
        msg = ffi.string(error_msg).decode() if error_msg else 'Unknown DID error.'
        return msg if not prompt else f'[{prompt}] {msg}'

    def get_backup_credential_info(self, credential):
        """ for vault /backup """
        from src.utils_v1.auth import get_credential_info
        credential_info, err = get_credential_info(credential, ["targetHost", "targetDID"])
        if credential_info is None:
            raise InvalidParameterException(msg=f'Failed to get credential info: {err}')
        return credential_info

    def backup_client_sign_in(self, host_url, credential, subject):
        """
        for vault /backup & /restore
        :return challenge_response, backup_service_instance_did
        """
        vc = lib.Credential_FromJson(credential.encode(), ffi.NULL)
        if not vc:
            raise InvalidParameterException(msg='backup_sign_in: invalid credential.')

        doc_str = ffi.string(lib.DIDDocument_ToJson(lib.DIDStore_LoadDID(self.store, self.did), True)).decode()
        doc = json.loads(doc_str)
        body = self.http.post(host_url + URL_DID_SIGN_IN, None, {"id": doc})
        if 'challenge' not in body or not body["challenge"]:
            raise InvalidParameterException(msg='backup_sign_in: failed to sign in to backup node.')

        jws = lib.DefaultJWSParser_Parse(body["challenge"].encode())
        if not jws:
            raise InvalidParameterException(
                msg=f'backup_sign_in: failed to parse challenge with error {self.get_error_message()}.')

        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        if aud != self.get_did_string():
            lib.JWT_Destroy(jws)
            raise InvalidParameterException(msg=f'backup_sign_in: failed to get the audience of the challenge.')

        nonce = ffi.string(lib.JWT_GetClaim(jws, "nonce".encode())).decode()
        if nonce is None:
            lib.JWT_Destroy(jws)
            raise InvalidParameterException(
                msg=f'backup_sign_in: failed to get the nonce of the challenge.')

        issuer = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)
        if issuer is None:
            raise InvalidParameterException(
                msg=f'backup_sign_in: failed to get the issuer of the challenge.')

        vp_json = self.create_presentation(vc, nonce, issuer)
        if vp_json is None:
            raise InvalidParameterException(
                msg=f'backup_sign_in: failed to create presentation.')
        challenge_response = self.create_vp_token(vp_json, subject, issuer, hive_setting.AUTH_CHALLENGE_EXPIRED)
        if challenge_response is None:
            raise InvalidParameterException(
                msg=f'backup_sign_in: failed to create the challenge response.')
        return challenge_response, issuer

    def backup_client_auth(self, host_url, challenge_response, backup_service_instance_did):
        """
        for vault /backup & /restore
        :return backup access token
        """
        body = self.http.post(host_url + URL_DID_BACKUP_AUTH, None, {"challenge_response": challenge_response})
        if 'token' not in body or not body["token"]:
            raise InvalidParameterException(msg='backup_auth: failed to backup auth to backup node.')

        jws = lib.DefaultJWSParser_Parse(body["token"].encode())
        if not jws:
            raise InvalidParameterException(
                msg=f'backup_auth: failed to parse token with error {self.get_error_message()}.')

        audience = ffi.string(lib.JWT_GetAudience(jws)).decode()
        if audience != self.get_did_string():
            lib.JWT_Destroy(jws)
            raise InvalidParameterException(msg=f'backup_auth: failed to get the audience of the challenge.')

        issuer = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)
        if issuer != backup_service_instance_did:
            raise InvalidParameterException(msg=f'backup_auth: failed to get the issuer of the challenge.')

        return body["token"]

    def create_order_proof(self, user_did, doc_id, amount=0, is_receipt=False):
        doc = lib.DIDStore_LoadDID(self.store, self.did)
        if not doc:
            raise BadRequestException(msg='Can not load service instance document in creating order proof.')

        builder = lib.DIDDocument_GetJwtBuilder(doc)
        if not builder:
            raise BadRequestException(msg='Can not get builder from doc in creating order proof.')

        lib.JWTBuilder_SetHeader(builder, "typ".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())
        lib.JWTBuilder_SetSubject(builder, 'ORDER_PROOF'.encode())
        lib.JWTBuilder_SetAudience(builder, user_did.encode())
        exp = int(datetime.utcnow().timestamp()) + 7 * 24 * 3600 if not is_receipt else -1
        lib.JWTBuilder_SetExpiration(builder, exp)
        props = {'order_id': doc_id}
        if is_receipt:
            props = {'receipt_id': doc_id, 'amount': amount}
        lib.JWTBuilder_SetClaim(builder, "props".encode(), json.dumps(props).encode())

        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        proof = lib.JWTBuilder_Compact(builder)
        lib.JWTBuilder_Destroy(builder)
        if not proof:
            raise BadRequestException(msg='Can not build token in creating order proof.')

        return ffi.string(proof).decode()

    def verify_order_proof(self, proof, user_did, order_id):
        # INFO：DefaultJWSParser_Parse will validate the sign information.
        jws = lib.DefaultJWSParser_Parse(proof.encode())
        if not jws:
            raise BadRequestException(msg=self.get_error_message('parse the proof error'))

        issuer = lib.JWT_GetIssuer(jws)
        if not issuer:
            lib.JWT_Destroy(jws)
            raise BadRequestException(msg=self.get_error_message('the issue of the proof error'))
        if self.did_str != ffi.string(issuer).decode():
            lib.JWT_Destroy(jws)
            raise BadRequestException(msg=f'the issue of the proof not match: {ffi.string(issuer).decode()}')

        audience = lib.JWT_GetAudience(jws)
        if not audience:
            lib.JWT_Destroy(jws)
            raise BadRequestException(msg=self.get_error_message('the audience of the proof error'))
        if user_did != ffi.string(audience).decode():
            lib.JWT_Destroy(jws)
            raise BadRequestException(msg=f'the audience of the proof not match: {ffi.string(audience).decode()}')

        props = lib.JWT_GetClaim(jws, "props".encode())
        if not props:
            lib.JWT_Destroy(jws)
            raise BadRequestException(msg=self.get_error_message('the claim of the proof error'))
        props_json = json.loads(ffi.string(props).decode())
        if props_json.get('order_id') != order_id:
            lib.JWT_Destroy(jws)
            raise BadRequestException(msg=f'the order_id of the proof not match: {props_json.get("order_id")}')

        expired = lib.JWT_GetExpiration(jws)
        now = int(datetime.now().timestamp())
        if now > expired:
            lib.JWT_Destroy(jws)
            raise BadRequestException(msg=f'the proof is expired (valid for 7 days)')

        lib.JWT_Destroy(jws)

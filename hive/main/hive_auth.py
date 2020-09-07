import json
import logging

from flask import request
from datetime import datetime
import time
import os

from hive.util.did.eladid import ffi, lib

from hive.util.did_info import add_did_nonce_to_db, create_nonce, get_did_info_by_nonce, update_nonce_of_did_info, \
    get_did_info_by_did_appid, update_token_of_did_info
from hive.util.server_response import response_err, response_ok
from hive.settings import AUTH_CHALLENGE_EXPIRED, ACCESS_TOKEN_EXPIRED
from hive.util.constants import DID_INFO_DB_NAME, DID_INFO_REGISTER_COL, DID, APP_ID, DID_INFO_NONCE, DID_INFO_TOKEN, \
    DID_INFO_NONCE_EXPIRED, DID_INFO_TOKEN_EXPIRED, APP_INSTANCE_DID

from hive.settings import DID_MNEMONIC, DID_PASSPHRASE, DID_STOREPASS, HIVE_DATA_PATH

from hive.util.did.entity import Entity, localdids

ACCESS_AUTH_COL = "did_auth"
APP_DID = "appdid"
ACCESS_TOKEN = "access_token"


class HiveAuth(Entity):
    access_token = None

    def __init__(self):
        self.mnemonic = DID_MNEMONIC
        self.passphrase = DID_PASSPHRASE.encode()
        self.storepass = DID_STOREPASS.encode()
        Entity.__init__(self, "hive.auth")

    def init_app(self, app):
        self.app = app

    def __is_did(self, did_str):
        did = lib.DID_FromString(did_str.encode())
        if did is None:
            return False
        doc = lib.DID_Resolve(did, True)
        if doc is None:
            return False
        else:
            return True

    def __get_token_from_db(self, iss, appdid):
        return vp_token

    def sign_in(self):
        body = request.get_json(force=True, silent=True)
        if body is None:
            return response_err(401, "parameter is not application/json")
        document = body.get('document', None)
        if document is None:
            return response_err(400, "Thd did document is null")

        doc_str = json.dumps(body.get('document', None))
        doc = lib.DIDDocument_FromJson(doc_str.encode())
        if (doc is None) or (not lib.DIDDocument_IsValid(doc)):
            return response_err(400, "Thd did document is vaild")

        did = lib.DIDDocument_GetSubject(doc)

        spec_did_str = ffi.string(lib.DID_GetMethodSpecificId(did)).decode()
        f = open(localdids + os.sep + spec_did_str, "w")
        try:
            f.write(doc_str)
        finally:
            f.close()
        did_str = "did:" + ffi.string(lib.DID_GetMethod(did)).decode() +":" + spec_did_str

        # save to db
        nonce = create_nonce()
        exp = int(datetime.now().timestamp()) + AUTH_CHALLENGE_EXPIRED
        if not self.__save_nonce_to_db(nonce, did_str, exp):
            return response_err(500, "save to db fail!")

        # response token
        builder = lib.DIDDocument_GetJwtBuilder(self.doc)
        lib.JWTBuilder_SetHeader(builder, "type".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())

        lib.JWTBuilder_SetSubject(builder, "DIDAuthChallenge".encode())
        lib.JWTBuilder_SetAudience(builder, did_str.encode())
        lib.JWTBuilder_SetClaim(builder, "nonce".encode(), nonce.encode())
        lib.JWTBuilder_SetExpiration(builder, exp)

        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        token = ffi.string(lib.JWTBuilder_Compact(builder)).decode()
        # print(token)
        lib.JWTBuilder_Destroy(builder)
        data = {
            "challenge": token,
        }
        return response_ok(data)

    def request_did_auth(self):
        # get jwt
        body = request.get_json(force=True, silent=True)
        if body is None:
            return response_err(400, "The parameter is not application/json")
        jwt = body.get('jwt', None)

        # check auth token
        credentialSubject, err = self.__check_auth_token(jwt)
        if credentialSubject is None:
            return response_err(400, err)

        # create access token
        expTime = credentialSubject["expTime"]
        exp = int(datetime.now().timestamp()) + ACCESS_TOKEN_EXPIRED
        if exp > expTime:
            exp = expTime

        access_token = self.__create_access_token(credentialSubject, exp)
        if not access_token:
            return response_err(400, "create access token fail!")

        # save to db
        if not self.__save_token_to_db(credentialSubject, access_token, exp):
            return response_err(400, "save to db fail!")

        # response token
        data = {
            "access_token": access_token,
        }
        return response_ok(data)

    def __check_auth_token(self, jwt):
        if jwt is None:
            return None, "The jwt is none."

        #check jwt token
        jws = lib.JWTParser_Parse(jwt.encode())
        vp_str = lib.JWS_GetClaimAsJson(jws, "presentation".encode())
        if vp_str is None:
            return None, "The jwt's presentation is none."

        vp = lib.Presentation_FromJson(vp_str)
        if vp is None:
            return None, "The presentation string is error, unable to rebuild to a presentation object."

        vp_json = json.loads(ffi.string(vp_str).decode())
        lib.JWS_Destroy(jws)

        #check vp
        ret = lib.Presentation_IsValid(vp)
        if not ret:
            return None, "The presentation isn't valid"
        # print(ffi.string(vp_str).decode())

        #check nonce
        nonce = vp_json["proof"]["nonce"]
        if nonce is None:
            return None, "The nonce is none."

        #check did:nonce from db
        info = get_did_info_by_nonce(nonce)
        if info is None:
            return None, "The nonce is error."

        #check realm
        realm = vp_json["proof"]["realm"]
        if realm is None:
            return None, "The realm is none."

        if realm != self.get_did_string():
            return None, "The realm is error."

        #check vc
        vc_json = vp_json["verifiableCredential"][0]
        vc_str = json.dumps(vc_json)
        vc = lib.Credential_FromJson(vc_str.encode(), ffi.NULL)
        if vc is None:
            return None, "The credential string is error, unable to rebuild to a credential object."

        ret = lib.Credential_IsValid(vc)
        if not ret:
            return None, "The verifiableCredential isn't valid"

        credentialSubject = vc_json["credentialSubject"]
        instance_did = credentialSubject["id"]
        if info[APP_INSTANCE_DID] != instance_did:
            return None, "The app instance did is error."

        if info[DID_INFO_NONCE_EXPIRED] < int(datetime.now().timestamp()):
            #TODO::delete it
            return None, "The nonce is expired"

        credentialSubject["userDid"] = vc_json["issuer"]
        credentialSubject["nonce"] = nonce
        expirationDate = vc_json["expirationDate"]
        timeArray = time.strptime(expirationDate, "%Y-%m-%dT%H:%M:%SZ")
        credentialSubject["expTime"] = int(time.mktime(timeArray))

        return credentialSubject, None

    def __create_access_token(self, credentialSubject, exp):
        user_did = credentialSubject["userDid"]
        app_id = credentialSubject["appDid"]
        app_instance_did = credentialSubject["id"]

        did_str = self.get_did_string()
        doc = lib.DIDStore_LoadDID(self.store, self.did)
        builder = lib.DIDDocument_GetJwtBuilder(doc)
        lib.JWTBuilder_SetHeader(builder, "typ".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())

        lib.JWTBuilder_SetSubject(builder, "AccessToken".encode())
        lib.JWTBuilder_SetAudience(builder, app_instance_did.encode())
        lib.JWTBuilder_SetExpiration(builder, exp)
        lib.JWTBuilder_SetClaim(builder, "userDid".encode(), user_did.encode())
        lib.JWTBuilder_SetClaim(builder, "appId".encode(), app_id.encode())
        lib.JWTBuilder_SetClaim(builder, "appInstanceDid".encode(), app_instance_did.encode())
        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        token = ffi.string(lib.JWTBuilder_Compact(builder)).decode()
        lib.JWTBuilder_Destroy(builder)
        return token

    def __save_nonce_to_db(self, nonce, app_instance_did, exp):
        info = get_did_info_by_nonce(nonce)

        try:
            if info is None:
                add_did_nonce_to_db(app_instance_did, nonce, exp)
            else:
                update_nonce_of_did_info(app_instance_did, nonce, exp)
        except Exception as e:
            logging.debug(f"Exception in __save_nonce_to_db:: {e}")
            return False

        return True

    def __save_token_to_db(self, credentialSubject, token, exp):
        user_did = credentialSubject["userDid"]
        app_id = credentialSubject["appDid"]
        nonce = credentialSubject["nonce"]
        app_instance_did = credentialSubject["id"]

        try:
            update_token_of_did_info(user_did, app_id, app_instance_did, nonce, token, exp)
        except Exception as e:
            logging.debug(f"Exception in __save_token_to_db:: {e}")
            return False

        return True

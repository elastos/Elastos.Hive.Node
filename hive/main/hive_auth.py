import json
import logging

from flask import request
from datetime import datetime
import time
import os

from hive.util.did.eladid import ffi, lib

from hive.util.did_info import add_did_nonce_to_db, create_nonce, get_did_info_by_nonce, update_nonce_of_did_info, \
        update_token_of_did_info
from hive.util.server_response import ServerResponse
from hive.settings import AUTH_CHALLENGE_EXPIRED, ACCESS_TOKEN_EXPIRED
from hive.util.constants import DID_INFO_DB_NAME, DID_INFO_REGISTER_COL, DID, APP_ID, DID_INFO_NONCE, DID_INFO_TOKEN, \
    DID_INFO_NONCE_EXPIRED, DID_INFO_TOKEN_EXPIRED, APP_INSTANCE_DID

from hive.settings import DID_MNEMONIC, DID_PASSPHRASE, DID_STOREPASS, HIVE_DATA

from hive.util.did.entity import Entity
from hive.util.did.did_init import localdids
from hive.util.auth import did_auth

ACCESS_AUTH_COL = "did_auth"
APP_DID = "appdid"
ACCESS_TOKEN = "access_token"

class HiveAuth(Entity):
    access_token = None

    def __init__(self):
        self.mnemonic = DID_MNEMONIC
        self.passphrase = DID_PASSPHRASE
        self.storepass = DID_STOREPASS
        Entity.__init__(self, "hive.auth")
        self.response = ServerResponse("HiveSync")

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
            return self.response.response_err(401, "parameter is not application/json")
        document = body.get('document', None)
        if document is None:
            return self.response.response_err(400, "Thd did document is null")

        doc_str = json.dumps(body.get('document', None))
        doc = lib.DIDDocument_FromJson(doc_str.encode())
        if (not doc) or (not lib.DIDDocument_IsValid(doc)):
            return self.response.response_err(400, "Thd did document is vaild")

        did = lib.DIDDocument_GetSubject(doc)
        if not did:
            return self.response.response_err(400, "Thd did document is vaild, can't get did.")

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
            return self.response.response_err(500, "save to db fail!")

        # response token
        builder = lib.DIDDocument_GetJwtBuilder(self.doc)
        if not builder:
            return self.response.response_err(500, "Can't get jwt builder.")

        lib.JWTBuilder_SetHeader(builder, "type".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())

        lib.JWTBuilder_SetSubject(builder, "DIDAuthChallenge".encode())
        lib.JWTBuilder_SetAudience(builder, did_str.encode())
        lib.JWTBuilder_SetClaim(builder, "nonce".encode(), nonce.encode())
        lib.JWTBuilder_SetExpiration(builder, exp)

        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        token = lib.JWTBuilder_Compact(builder)
        if not token:
            return self.response.response_err(500, "Compact builder to a token is fail.")

        token = ffi.string(token).decode()
        # print(token)
        lib.JWTBuilder_Destroy(builder)
        data = {
            "challenge": token,
        }
        return self.response.response_ok(data)

    def request_did_auth(self):
        # get jwt
        body = request.get_json(force=True, silent=True)
        if body is None:
            return self.response.response_err(400, "The parameter is not application/json")
        jwt = body.get('jwt', None)

        # check auth token
        credentialSubject, err = self.__check_auth_token(jwt)
        if credentialSubject is None:
            return self.response.response_err(400, err)

        # create access token
        expTime = credentialSubject["expTime"]
        exp = int(datetime.now().timestamp()) + ACCESS_TOKEN_EXPIRED
        if exp > expTime:
            exp = expTime

        access_token, err = self.__create_access_token(credentialSubject, exp)
        if not err is None:
            return self.response.response_err(500, err)

        # save to db
        if not self.__save_token_to_db(credentialSubject, access_token, exp):
            return self.response.response_err(400, "save to db fail!")

        # response token
        data = {
            "access_token": access_token,
        }
        return self.response.response_ok(data)

    def __check_auth_token(self, jwt):
        if jwt is None:
            return None, "The jwt is none."

        #check jwt token
        jws = lib.JWTParser_Parse(jwt.encode())
        if not jwt:
            return None, "The jwt is error."

        vp_str = lib.JWS_GetClaimAsJson(jws, "presentation".encode())
        if not vp_str:
            return None, "The jwt's presentation is none."

        vp = lib.Presentation_FromJson(vp_str)
        if not vp:
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
        if not vc:
            return None, "The credential string is error, unable to rebuild to a credential object."

        ret = lib.Credential_IsValid(vc)
        if not ret:
            return None, "The verifiableCredential isn't valid"

        credentialSubject = vc_json["credentialSubject"]
        instance_did = credentialSubject["id"]
        if info[APP_INSTANCE_DID] != instance_did:
            return None, "The app instance did is error."

        expired = info[DID_INFO_NONCE_EXPIRED] < int(datetime.now().timestamp())
        if expired:
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

        doc = lib.DIDStore_LoadDID(self.store, self.did)
        if not doc:
            return None, "The doc can't load from did."

        builder = lib.DIDDocument_GetJwtBuilder(doc)
        if not builder:
            return None, "Can't get jwt builder."

        lib.JWTBuilder_SetHeader(builder, "typ".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())

        lib.JWTBuilder_SetSubject(builder, "AccessToken".encode())
        lib.JWTBuilder_SetAudience(builder, app_instance_did.encode())
        lib.JWTBuilder_SetExpiration(builder, exp)
        lib.JWTBuilder_SetClaim(builder, "userDid".encode(), user_did.encode())
        lib.JWTBuilder_SetClaim(builder, "appId".encode(), app_id.encode())
        lib.JWTBuilder_SetClaim(builder, "appInstanceDid".encode(), app_instance_did.encode())
        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        token = lib.JWTBuilder_Compact(builder)
        if not token:
            return None, "Compact builder to a token is fail."

        token = ffi.string(token).decode()
        lib.JWTBuilder_Destroy(builder)
        return token, None

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


    def check_token(self):
        info, err = self.check_access_token()
        if info is None:
            return self.response.response_err(400, err)
        else:
            return self.response.response_ok()

    def check_access_token(self):
        auth = request.headers.get("Authorization")
        if auth is None:
            return None, "Can't find the Authorization!"

        if not auth.strip().lower().startswith(("token", "bearer")):
            return None, "Can't find the token!"

        auth_splits = auth.split(" ")
        if len(auth_splits) < 2:
            return None, "Can't find the token!"

        access_token = auth_splits[1]
        if access_token == "":
            return None, "The token is None!"

        return self.get_info_from_token(access_token)

    def get_info_from_token(self, access_token):
        if access_token is None:
            return None, "Then access token is none!"

        token_splits = access_token.split(".")
        if token_splits is None:
            return None, "Then access token is invalid!"

        if (len(token_splits) != 3) or token_splits[2] == "":
            return None, "Then access token is invalid!"

        jws = lib.JWTParser_Parse(access_token.encode())
        if not jws:
            return None, "Then access token is invalid!"

        issuer = lib.JWS_GetIssuer(jws)
        if not issuer:
            return None, "Then issuer is null!"

        issuer = ffi.string(issuer).decode()
        if issuer != self.get_did_string():
            return None, "Then issuer is invalid!"

        expired =  lib.JWS_GetExpiration(jws)
        now = (int)(datetime.now().timestamp())
        if now > expired:
            return None, "Then token is expired!"

        did = lib.JWS_GetClaim(jws, "userDid".encode())
        if not did:
            return None, "Then user did is none!"


        appid = lib.JWS_GetClaim(jws, "appId".encode())
        if not appid:
            return None, "Then app id is none!"

        info = {}
        info[DID] = ffi.string(did).decode()
        info[APP_ID] = ffi.string(appid).decode()

        return info, None



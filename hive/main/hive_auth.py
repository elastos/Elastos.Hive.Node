import json
import logging

from flask import request
from datetime import datetime
import time
import os
import requests

from hive.util.did.eladid import ffi, lib

from hive.util.did_info import add_did_nonce_to_db, create_nonce, get_did_info_by_nonce, get_did_info_by_app_instance_did, update_did_info_by_app_instance_did, \
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
        # check auth token
        auth_info, err = self.__get_auth_token_info(["appDid"])
        if auth_info is None:
            return self.response.response_err(401, err)

        # create access token
        access_token, err = self.__create_token(auth_info, "AccessToken")
        if not err is None:
            return self.response.response_err(401, err)

        # save to db
        if not self.__save_auth_info_to_db(auth_info, access_token):
            return self.response.response_err(401, "save to db fail!")

        # response token
        data = {
            "access_token": access_token,
        }
        return self.response.response_ok(data)

    def __get_auth_token_info(self, props):
        # get jwt
        body = request.get_json(force=True, silent=True)
        if body is None:
            return None, "The parameter is not application/json"
        jwt = body.get('jwt', None)

        if jwt is None:
            return None, "The jwt is none."

        #check jwt token
        jws = lib.DefaultJWSParser_Parse(jwt.encode())
        if not jws:
            return None, self.get_error_message("JWS parser")

        vp_str = lib.JWT_GetClaimAsJson(jws, "presentation".encode())
        if not vp_str:
            return None, "The jwt's presentation is none."

        vp = lib.Presentation_FromJson(vp_str)
        if not vp:
            return None, "The presentation string is error, unable to rebuild to a presentation object."

        vp_json = json.loads(ffi.string(vp_str).decode())
        lib.JWT_Destroy(jws)

        #check vp
        ret = lib.Presentation_IsValid(vp)
        if not ret:
            return None, self.get_error_message("Presentation isValid")
        # print(ffi.string(vp_str).decode())

        #check nonce
        nonce = lib.Presentation_GetNonce(vp)
        if not nonce:
            return None, "The nonce is none."
        nonce = ffi.string(nonce).decode()
        if nonce is None:
            return None, "The nonce is isn't valid."

        #check did:nonce from db
        info = get_did_info_by_nonce(nonce)
        if info is None:
            return None, "The nonce is error."

        #check realm
        realm = lib.Presentation_GetRealm(vp)
        if not realm:
            return None, "The realm is none."
        realm = ffi.string(realm).decode()
        if realm is None:
            return None, "The realm is isn't valid."

        if realm != self.get_did_string():
            return None, "The realm is error."

        #check vc
        count = lib.Presentation_GetCredentialCount(vp)
        if count < 1:
            return None, "The credential count is error."

        if not "verifiableCredential" in vp_json:
            return None, "The credential isn't exist."

        vcs_json = vp_json["verifiableCredential"]
        if not isinstance(vcs_json, list):
            return None, "The verifiableCredential isn't valid"

        vc_json = vcs_json[0]
        if vc_json is None:
            return None, "The credential isn't exist"

        vc_str = json.dumps(vc_json)

        credential_info, err = self.get_credential_info(vc_str, props)
        if not credential_info is None:
            if credential_info["id"] != info[APP_INSTANCE_DID]:
                return None, "The app instance did is error."
            credential_info["nonce"] = nonce
            if info[DID_INFO_NONCE_EXPIRED] < int(datetime.now().timestamp()):
                return None, "The nonce is expired"

        return credential_info, err

    def __create_token(self, auth_info, subject):
        if not isinstance(auth_info, dict):
            return None, "auth info isn't dict type"

        doc = lib.DIDStore_LoadDID(self.store, self.did)
        if not doc:
            return None, self.get_error_message("The doc load from did")

        builder = lib.DIDDocument_GetJwtBuilder(doc)
        if not builder:
            return None, "Can't get jwt builder."

        lib.JWTBuilder_SetHeader(builder, "typ".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())

        lib.JWTBuilder_SetSubject(builder, subject.encode())
        lib.JWTBuilder_SetAudience(builder, auth_info["id"].encode())
        lib.JWTBuilder_SetExpiration(builder, auth_info["expTime"])
        for key in auth_info:
            if key != "expTime" and key != "id":
                lib.JWTBuilder_SetClaim(builder, key.encode(), auth_info[key].encode())

        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        token = lib.JWTBuilder_Compact(builder)
        if not token:
            return None, self.get_error_message("Compact builder to a token")

        token = ffi.string(token).decode()
        lib.JWTBuilder_Destroy(builder)
        return token, None

    def __save_nonce_to_db(self, nonce, app_instance_did, exp):
        info = get_did_info_by_app_instance_did(app_instance_did)

        try:
            if info is None:
                add_did_nonce_to_db(app_instance_did, nonce, exp)
            else:
                update_did_info_by_app_instance_did(app_instance_did, nonce, exp)
        except Exception as e:
            logging.error(f"Exception in __save_nonce_to_db:: {e}")
            return False

        return True

    def __save_auth_info_to_db(self, auth_info, token):
        user_did = auth_info["userDid"]
        app_id = auth_info["appDid"]
        nonce = auth_info["nonce"]
        app_instance_did = auth_info["id"]
        exp = auth_info["expTime"]

        try:
            update_token_of_did_info(user_did, app_id, app_instance_did, nonce, token, exp)
        except Exception as e:
            logging.error(f"Exception in __save_auth_info_to_db:: {e}")
            return False

        return True


    def check_token(self):
        info, err = self.get_access_token_info()
        if info is None:
            return self.response.response_err(401, err)
        else:
            return self.response.response_ok()

    def get_access_token_info(self):
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

        jws = lib.DefaultJWSParser_Parse(access_token.encode())
        if not jws:
            return None, self.get_error_message("JWS parser")

        issuer = lib.JWT_GetIssuer(jws)
        if not issuer:
            return None, self.get_error_message("JWT getIssuer")

        issuer = ffi.string(issuer).decode()
        if issuer != self.get_did_string():
            return None, "Then issuer is invalid!"

        expired =  lib.JWT_GetExpiration(jws)
        now = (int)(datetime.now().timestamp())
        if now > expired:
            return None, "Then token is expired!"

        did = lib.JWT_GetClaim(jws, "userDid".encode())
        if not did:
            return None, "Then user did is none!"

        appid = lib.JWT_GetClaim(jws, "appDid".encode())
        if not appid:
            appid = lib.JWT_GetClaim(jws, "appId".encode())
        if not appid:
            return None, "Then app id is none!"

        app_instance_did = ffi.string(lib.JWT_GetAudience(jws)).decode()
        if not app_instance_did:
            return None, "Then app instance id is none!"

        info = {}
        info[DID] = ffi.string(did).decode()
        info[APP_ID] = ffi.string(appid).decode()
        info[APP_INSTANCE_DID] = app_instance_did

        return info, None

    def backup_request(self):
        info, err = self.get_access_token_info()

        # get credential
        body = request.get_json(force=True, silent=True)
        if body is None:
            return self.response.response_err(400, "The parameter is not application/json")
        vc_str = body.get('credential', None)

        # check backup request vc
        credential_info, err = self.get_credential_info(vc_str, ["targetHost", "targetDID", "sourceHost"])
        if credential_info is None:
            return self.response.response_err(401, err)

        doc = lib.DIDStore_LoadDID(self.store, self.did)
        doc_str = ffi.string(lib.DIDDocument_ToJson(doc, True)).decode()
        doc = json.loads(doc_str)

        rt, s = self.parse_response(
            self.post(credential_info["targetHost"] + '/api/v1/did/sign_in', {"document": doc}))

        jwt = rt["challenge"]
        # print(jwt)
        jws = lib.DefaultJWSParser_Parse(jwt.encode())
        if not jws:
            print(ffi.string(lib.DIDError_GetMessage()).decode())
        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        if aud != self.get_did_string():
            return self.response.response_err(401, "Backup sign_in is error.")

        nonce = ffi.string(lib.JWT_GetClaim(jws, "nonce".encode())).decode()
        hive2_did = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)

        #backup auth
        vc = lib.Credential_FromJson(vc_str.encode(), ffi.NULL)
        if not vc:
            return None, "The credential string is error, unable to rebuild to a credential object."
        vp_json = self.create_presentation(vc, nonce, hive2_did)
        auth_token = self.create_vp_token(vp_json, "DIDBackupAuthResponse", hive2_did, AUTH_CHALLENGE_EXPIRED)
        # # print(auth_token)
        rt, s = self.parse_response(
            self.post(credential_info["targetHost"] + '/api/v1/did/backup_auth', {"jwt": auth_token}))


        token = rt["backup_token"]
        jws = lib.DefaultJWSParser_Parse(token.encode())
        aud = ffi.string(lib.JWT_GetAudience(jws)).decode()
        if aud != self.get_did_string():
            return self.response.response_err(401, "Backup auth is error.")

        # issuer = ffi.string(lib.JWT_GetIssuer(jws)).decode()
        lib.JWT_Destroy(jws)

        return self.response.response_ok()

    def create_backup_vc_token(self, vc_json, hive_did):
        doc = lib.DIDStore_LoadDID(self.store, self.did)
        builder = lib.DIDDocument_GetJwtBuilder(doc)
        ticks = int(datetime.now().timestamp())
        iat = ticks
        nbf = ticks
        exp = ticks + 60

        lib.JWTBuilder_SetHeader(builder, "type".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())

        lib.JWTBuilder_SetSubject(builder, "DIDBackupAuthResponse".encode())
        lib.JWTBuilder_SetAudience(builder, hive_did.encode())
        lib.JWTBuilder_SetIssuedAt(builder, iat)
        lib.JWTBuilder_SetExpiration(builder, exp)
        lib.JWTBuilder_SetNotBefore(builder, nbf)
        lib.JWTBuilder_SetClaimWithJson(builder, "credential".encode(), vc_json.encode())

        lib.JWTBuilder_Sign(builder, ffi.NULL, self.storepass)
        token = ffi.string(lib.JWTBuilder_Compact(builder)).decode()
        lib.JWTBuilder_Destroy(builder)
        # print(token)
        return token

    def post(self, url, param):
        try:
            r = requests.post(url, json=param, headers={"Content-Type": "application/json"})
        except Exception as e:
            logging.error(f"Exception in post:: {e}")
            return None
        return r

    def parse_response(self, r):
        try:
            v = r.json()
        except json.JSONDecodeError:
            v = None
        return v, r.status_code

    def get_credential_info(self, vc_str, props):
        if vc_str is None:
            return None, "The credential is none."

        vc = lib.Credential_FromJson(vc_str.encode(), ffi.NULL)
        if not vc:
            return None, "The credential string is error, unable to rebuild to a credential object."

        ret = lib.Credential_IsValid(vc)
        if not ret:
            return None, self.get_error_message("Credential isValid")

        vc_json = json.loads(vc_str)
        if not "credentialSubject" in vc_json:
            return None, "The credentialSubject isn't exist."
        credentialSubject = vc_json["credentialSubject"]

        if not "id" in credentialSubject:
            return None, "The credentialSubject's id isn't exist."

        for prop in props:
            if not prop in credentialSubject:
                return None, "The credentialSubject's '" + prop + "' isn't exist."

        if not "issuer" in vc_json:
            return None, "The credential issuer isn't exist."
        credentialSubject["userDid"] = vc_json["issuer"]

        expTime = lib.Credential_GetExpirationDate(vc)
        if expTime == 0:
            return None, self.get_error_message("Credential getExpirationDate")

        exp = int(datetime.now().timestamp()) + ACCESS_TOKEN_EXPIRED
        if expTime > exp:
            expTime = exp

        credentialSubject["expTime"] = expTime

        return credentialSubject, None

    def backup_auth(self):
        # check backup auth token
        auth_info, err = self.__get_auth_token_info(["targetHost", "targetDID", "sourceHost"])
        if auth_info is None:
            return self.response.response_err(401, err)

        # create backup token
        backup_token, err = self.__create_token(auth_info, "BackupToken")
        if not err is None:
            return self.response.response_err(401, err)

        # response token
        data = {
            "backup_token": backup_token,
        }
        return self.response.response_ok(data)
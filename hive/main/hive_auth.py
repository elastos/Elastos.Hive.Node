import json
import os
import pathlib

from pymongo import MongoClient
from hive.util.constants import DID_INFO_DB_NAME

from flask import request
from datetime import datetime
from hive.util.did.eladid import ffi, lib

from hive.util.did_info import add_did_info_to_db, create_nonce, update_nonce_of_did_info, get_did_info_by_did_appid
from hive.util.server_response import response_err, response_ok
from hive.settings import DID_CHALLENGE_EXPIRE, DID_TOKEN_EXPIRE

# import sys
# sys.path.append(os.getcwd() + "/hive/util/did")
from hive.util.did.entity import Entity

ACCESS_AUTH_COL = "did_auth"
APP_DID = "appdid"
ACCESS_TOKEN = "access_token"
TOKEN_EXPIRE = "token_expire"

class HiveAuth(Entity):
    access_token = None

    def __init__(self):
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

    def request_did_auth(self):
        #get jwt
        body = request.get_json(force=True, silent=True)
        if body is None:
            return response_err(400, "parameter is not application/json")
        jwt = body.get('jwt', None)

        #check auth token
        credentialSubject = self.__check_auth_token(jwt)
        if credentialSubject is None:
            return

        #create access token
        exp = int(datetime.now().timestamp()) + DID_CHALLENGE_EXPIRE
        access_token = self.__create_access_token(credentialSubject, exp)
        if not access_token:
            return response_err(400, "create access token fail!")

        #save to db
        if not self.__save_to_db(credentialSubject, access_token, exp):
            return response_err(400, "save to db fail!")

        #response token
        data = {
            "subject": "didauth",
            "issuer": "elastos_hive_node",
            "token": access_token,
        }
        return response_ok(data)

    def __check_auth_token(self, jwt):
        if jwt is None:
            response_err(400, "jwt is null")
            return None

        jws = lib.JWTParser_Parse(jwt.encode())
        ver = lib.JWS_GetHeader(jws, "version".encode())
        # iss = JWS_GetClaim(jws, "iss")
        vp_str = lib.JWS_GetClaimAsJson(jws, "vp".encode())

        vp = lib.Presentation_FromJson(vp_str)
        vp_json = json.loads(ffi.string(vp_str).decode())
        lib.JWS_Destroy(jws)

        ret = lib.Presentation_IsGenuine(vp)
        if not ret:
            response_err(400, "vp isn't genuine")
            return None

        ret = lib.Presentation_IsValid(vp)
        if not ret:
            response_err(400, "vp isn't valid")
            return None

        # print(ffi.string(vp_str).decode())

        vc_json = vp_json.get("verifiableCredential")[0]
        credentialSubject = vc_json.get("credentialSubject")
        vp_issuer = vc_json.get("issuer")
        userDid = credentialSubject.get("userDid")
        if (vp_issuer != userDid):
            response_err(400, "vp issuer isn't userDid")
            return None

        return credentialSubject

    def __create_access_token(self, credentialSubject, exp):
        did_str = self.get_did_string()
        doc = lib.DIDStore_LoadDID(self.store, self.did)
        builder = lib.DIDDocument_GetJwtBuilder(doc)
        lib.JWTBuilder_SetHeader(builder, "typ".encode(), "JWT".encode())
        lib.JWTBuilder_SetHeader(builder, "version".encode(), "1.0".encode())

        lib.JWTBuilder_SetSubject(builder, "AccessAuthority".encode())
        lib.JWTBuilder_SetIssuer(builder, did_str.encode())
        lib.JWTBuilder_SetExpiration(builder, exp)
        lib.JWTBuilder_SetClaimWithJson(builder, "accessSubject".encode(), json.dumps(credentialSubject).encode())
        token = ffi.string(lib.JWTBuilder_Compact(builder)).decode()
        lib.JWTBuilder_Destroy(builder)
        return token


    def __save_to_db(self, credentialSubject, token, exp):
        did = credentialSubject.get("userDid")
        app_id = credentialSubject.get("appDid")
        nonce = create_nonce()
        info = get_did_info_by_did_appid(did, app_id)

        try:
            if info is None:
                add_did_info_to_db(did, app_id, nonce, token, exp)
            else:
                update_nonce_of_did_info(did, app_id, nonce, token, exp)
        except Exception as e:
            print("Exception in did_auth_challenge::", e)
            response_err(500, "Exception in did_auth_challenge:" + e)
            return False

        return True




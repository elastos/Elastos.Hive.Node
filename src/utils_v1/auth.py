import json
from datetime import datetime

from flask import request

from src import hive_setting
from src.utils.resolver import DIDResolver
from src.utils_v1.constants import USER_DID, APP_ID, APP_INSTANCE_DID
from src.utils_v1.did.eladid import ffi, lib
from src.modules.auth.auth import Auth

###############################################################################
# TODO: try to move the following methods to authorization module.


_auth = None


def get_auth():
    global _auth
    if _auth is None:
        _auth = Auth()
    return _auth


def get_credential_info(vc_str, props: list):
    if vc_str is None:
        return None, "The credential is none."

    vc = lib.Credential_FromJson(vc_str.encode(), ffi.NULL)
    if not vc:
        return None, "The credential string is error, unable to rebuild to a credential object."

    if lib.Credential_IsValid(vc) != 1:
        return None, DIDResolver.get_errmsg(f"Credential isValid")

    vc_json = json.loads(vc_str)
    if not "credentialSubject" in vc_json:
        return None, "The credentialSubject isn't exist."
    credentialSubject = vc_json["credentialSubject"]

    if not "id" in credentialSubject:
        return None, "The credentialSubject's id isn't exist."

    if 'sourceDID' not in props:
        props.append('sourceDID')

    for prop in props:
        if not prop in credentialSubject:
            return None, "The credentialSubject's '" + prop + "' isn't exist."

    if credentialSubject['sourceDID'] != get_current_node_did_string():
        return None, f'The sourceDID({credentialSubject["sourceDID"]}) is not the hive node did.'

    if not "issuer" in vc_json:
        return None, "The credential issuer isn't exist."
    credentialSubject["userDid"] = vc_json["issuer"]

    expTime = lib.Credential_GetExpirationDate(vc)
    if expTime == 0:
        return None, DIDResolver.get_errmsg('Credential getExpirationDate')

    exp = int(datetime.now().timestamp()) + hive_setting.ACCESS_TOKEN_EXPIRED
    if expTime > exp:
        expTime = exp

    credentialSubject["expTime"] = expTime

    return credentialSubject, None


def get_verifiable_credential_info(vc_str: str):
    """
    Common version of the credential parsing logic.
    @return all possible fields of the credential.
    """
    if not vc_str:
        return None, "The credential is empty."
    vc = lib.Credential_FromJson(vc_str.encode(), ffi.NULL)
    if not vc:
        return None, "The credential is not a valid JSON format."
    if lib.Credential_IsValid(vc) != 1:
        return None, DIDResolver.get_errmsg('The credential is invalid')

    vc_json = json.loads(vc_str)
    if "credentialSubject" not in vc_json:
        return None, "The credentialSubject doesn't exist in credential."
    credential_subject = vc_json["credentialSubject"]
    if "id" not in credential_subject:
        return None, "The credentialSubject's id doesn't exist in credential."
    if "issuer" not in vc_json:
        return None, "The issuer doesn't exist in credential."

    credential_subject["__issuer"] = vc_json["issuer"]
    credential_subject["__expirationDate"] = lib.Credential_GetExpirationDate(vc)
    if credential_subject["__expirationDate"] == 0:
        return None, DIDResolver.get_errmsg('The expirationDate is invalid in credential')
    if int(datetime.now().timestamp()) > credential_subject["__expirationDate"]:
        return None, DIDResolver.get_errmsg('The expirationDate is expired in credential.')
    return credential_subject, None


def get_current_node_did_string():
    return get_did_string_from_did(get_auth().did)


def get_did_string_from_did(did):
    return get_auth().get_did_string()


def get_info_from_token(token):
    if token is None:
        return None, "Then token is none!"

    token_splits = token.split(".")
    if token_splits is None:
        return None, "Then token is invalid because of not containing dot!"

    if (len(token_splits) != 3) or token_splits[2] == "":
        return None, "Then token is invalid because of containing invalid parts!"

    jws = lib.DefaultJWSParser_Parse(token.encode())
    if not jws:
        return None, DIDResolver.get_errmsg("JWS parser error!")

    issuer = lib.JWT_GetIssuer(jws)
    if not issuer:
        msg = DIDResolver.get_errmsg("JWT getIssuer error!")
        lib.JWT_Destroy(jws)
        return None, msg

    issuer = ffi.string(issuer).decode()
    if issuer != get_current_node_did_string():
        lib.JWT_Destroy(jws)
        return None, "The issuer is invalid!"

    expired = lib.JWT_GetExpiration(jws)
    now = (int)(datetime.now().timestamp())
    if now > expired:
        lib.JWT_Destroy(jws)
        return None, "Then token is expired!"

    props = lib.JWT_GetClaim(jws, "props".encode())
    if not props:
        lib.JWT_Destroy(jws)
        return None, "Then props is none!"

    props_str = ffi.string(props).decode()
    props_json = json.loads(props_str)

    app_instance_did = ffi.string(lib.JWT_GetAudience(jws)).decode()
    if not app_instance_did:
        lib.JWT_Destroy(jws)
        return None, "Then app instance id is none!"

    props_json[APP_INSTANCE_DID] = app_instance_did

    lib.JWT_Destroy(jws)
    # print(props_json)

    return props_json, None


def get_token_info():
    author = request.headers.get("Authorization")
    if author is None:
        return None, "Can't find the Authorization!"

    if not author.strip().lower().startswith(("token", "bearer")):
        return None, "Can't find the token with prefix token or bearer!"

    auth_splits = author.split(" ")
    if len(auth_splits) < 2:
        return None, "Can't find the token value!"

    access_token = auth_splits[1]
    if access_token == "":
        return None, "The token is empty!"

    return get_info_from_token(access_token)


# end of the get_token_info() method
###############################################################################


def did_auth():
    info, err = get_token_info()
    if info:
        if APP_ID in info:
            return info[USER_DID], info[APP_ID]
        else:
            return info[USER_DID], None
    else:
        return None, None


def did_auth2():
    """ Only for src part. """
    info, err = get_token_info()
    did = info[USER_DID] if info else None
    app_did = info[APP_ID] if info and APP_ID in info else None
    return did, app_did, err

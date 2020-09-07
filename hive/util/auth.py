from flask import request

from hive.util.constants import DID, APP_ID
from hive.util.did_info import get_did_info_by_token

from hive.util.did.eladid import ffi, lib

def get_info_from_token(access_token):
    jws = lib.JWTParser_Parse(access_token.encode())
    if not jws:
        return None, None
    userDid = lib.JWS_GetClaim(jws, "userDid".encode())
    if not userDid is None:
        userDid = ffi.string(userDid).decode()
    appId = lib.JWS_GetClaim(jws, "appId".encode())
    if not appId is None:
        appId = ffi.string(appId).decode()

    return userDid, appId

def did_auth():
    auth = request.headers.get("Authorization")
    if auth is None:
        return None, None

    if auth.strip().lower().startswith(("token", "bearer")):
        token = auth.split(" ")[1]
        info = get_did_info_by_token(token)
        if info is not None:
            # expired = info[DID_INFO_TOKEN_EXPIRED]
            # now = datetime.now().timestamp()
            # if now > expired:
            #     return None, None
            return info[DID], info[APP_ID]
        else:
            return get_info_from_token(token)
    else:
        return None, None


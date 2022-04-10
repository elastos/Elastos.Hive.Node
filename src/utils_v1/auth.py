import json
from datetime import datetime

from flask import request

from src.utils.http_exception import ElaDIDException
from src.utils_v1.constants import USER_DID, APP_ID, APP_INSTANCE_DID
from src.modules.auth.auth import Auth
from src.utils_v1.did.did_wrapper import JWT


def _get_info_from_token(token):
    token_splits = token.split(".")
    if token_splits is None:
        return None, "Then token is invalid because of not containing dot!"

    if (len(token_splits) != 3) or token_splits[2] == "":
        return None, "Then token is invalid because of containing invalid parts!"

    jwt = JWT.parse(token)
    issuer = jwt.get_issuer()
    if issuer != Auth().get_did_string():
        return None, "The issuer is invalid!"

    if int(datetime.now().timestamp()) > jwt.get_expiration():
        return None, "Then token is expired!"

    props_json = json.loads(jwt.get_claim('props'))
    props_json[APP_INSTANCE_DID] = jwt.get_audience()
    return props_json, None


def _get_token_info():
    author = request.headers.get("Authorization")
    if author is None:
        return None, "Can't find the Authorization!"

    if not author.strip().lower().startswith(("token", "bearer")):
        return None, "Can't find the token with prefix token or bearer!"

    auth_splits = author.split(" ")
    if len(auth_splits) < 2:
        return None, "Can't find the token value!"

    access_token = auth_splits[1]
    if not access_token:
        return None, "The token is empty!"

    try:
        return _get_info_from_token(access_token)
    except ElaDIDException as ex:
        return None, ex.msg


def did_auth():
    info, err = _get_token_info()
    if info:
        if APP_ID in info:
            return info[USER_DID], info[APP_ID]
        else:
            return info[USER_DID], None
    else:
        return None, None


def did_auth2():
    """ Only for src part. """
    info, err = _get_token_info()
    did = info[USER_DID] if info else None
    app_did = info[APP_ID] if info and APP_ID in info else None
    return did, app_did, err

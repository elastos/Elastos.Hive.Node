import datetime

from eve.auth import TokenAuth
from flask import request

from hive.util.constants import DID_PREFIX, DID_INFO_TOKEN_EXPIRE, DID, APP_ID
from hive.util.did_info import get_did_info_by_token


class HiveTokenAuth(TokenAuth):
    def check_auth(self, token, allowed_roles, resource, method):
        info = get_did_info_by_token(token)
        if info is not None:
            # expire = info[DID_INFO_TOKEN_EXPIRE]
            # now = datetime.now().timestamp()
            # if now > expire:
            #     return False
            did = info[DID]
            self.set_mongo_prefix(did + DID_PREFIX)
            return True
        else:
            return False


def did_auth():
    auth = request.headers.get("Authorization")
    if auth is None:
        return None

    if auth.strip().lower().startswith(("token", "bearer")):
        token = auth.split(" ")[1]
        info = get_did_info_by_token(token)
        if info is not None:
            return info[DID], info[APP_ID]
        else:
            return None
    else:
        return None

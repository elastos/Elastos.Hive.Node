from flask import request

from hive.util.constants import DID, APP_ID
from hive.util.did_info import get_did_info_by_token


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
            return None, None
    else:
        return None, None


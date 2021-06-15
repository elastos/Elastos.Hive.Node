from hive.util.constants import DID, APP_ID
from hive.main import view


def did_auth():
    info, err = view.h_auth.get_token_info()
    if info:
        if APP_ID in info:
            return info[DID], info[APP_ID]
        else:
            return info[DID], None
    else:
        return None, None


def did_auth2():
    """ Only for src part. """
    info, err = view.h_auth.get_token_info()
    did = info[DID] if info else None
    app_did = info[APP_ID] if info and APP_ID in info else None
    return did, app_did, err

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

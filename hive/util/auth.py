from flask import request

from hive.util.constants import DID, APP_ID
from hive.util.did_info import get_did_info_by_token

from hive.util.did.eladid import ffi, lib
from hive.main import view


def did_auth():
    info, err = view.h_auth.check_access_token()
    if not info is None:
        return info[DID], info[APP_ID]
    else:
        return None, None

